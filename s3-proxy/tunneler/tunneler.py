#!/usr/bin/env python3
"""
SSH Tunnel Manager for SkyStore S3 Proxy

This script sets up SSH tunnels to forward S3 services through the SkyStore server,
enabling access to S3 services without public IP addresses (e.g., local Minio deployments).
"""

import argparse
import json
import sys
import subprocess
import signal
import time
import ipaddress
import shutil
import os
from urllib.parse import urlparse, urlunparse
from pathlib import Path


class TunnelManager:
    """Manages SSH tunnels for S3 service forwarding"""
    
    def __init__(self, server_ip, ssh_port, ssh_username, config_path, mapping_file, dry_run=False):
        self.server_ip = server_ip
        self.ssh_port = ssh_port
        self.ssh_username = ssh_username
        self.config_path = config_path
        self.mapping_file = mapping_file
        self.pid_file = Path(config_path).parent / 'tunnel.pid'
        self.ssh_process = None
        self.config = None
        self.client_region = None
        self.dry_run = dry_run
        
    def load_config(self):
        """Load and parse the s3-proxy configuration JSON file"""
        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
            
            self.client_region = self.config.get('client_from_region')
            if not self.client_region:
                raise ValueError("Configuration missing 'client_from_region' field")
                
            print(f"Loaded configuration for client region: {self.client_region}")
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}", file=sys.stderr)
            return False
    
    def backup_config(self):
        """Create a backup copy of the configuration file"""
        try:
            backup_path = self.config_path + '.backup'
            shutil.copy2(self.config_path, backup_path)
            print(f"Created backup of configuration: {backup_path}")
            return True
        except Exception as e:
            print(f"Error creating backup: {e}", file=sys.stderr)
            return False
    
    def save_config(self):
        """Save the modified configuration back to the file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Updated configuration file: {self.config_path}")
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}", file=sys.stderr)
            return False
    
    
    def extract_hostname(self, endpoint_url):
        """Extract hostname from endpoint URL"""
        parsed = urlparse(endpoint_url)
        return parsed.hostname or parsed.netloc.split(':')[0]
    
    def is_ip_address(self, hostname):
        """Check if hostname is an IP address (IPv4 or IPv6)"""
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False
    
    def update_endpoint_url(self, endpoint_url, new_host, port):
        """Update endpoint URL with new host and port"""
        parsed = urlparse(endpoint_url)
        
        # Build new netloc with host and port
        new_netloc = f"{new_host}:{port}"
        
        # Reconstruct URL with new netloc
        new_url = urlunparse((
            parsed.scheme,
            new_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        return new_url
    
    def get_endpoint_details(self, region_name):
        """Get endpoint details for a custom region"""
        custom_endpoints = self.config.get('custom_endpoints', {})
        endpoint_config = custom_endpoints.get(region_name)
        
        if not endpoint_config:
            return None
            
        # Handle both simple string format and detailed object format
        if isinstance(endpoint_config, str):
            return {
                'endpoint_url': endpoint_config,
                'local_port_fwd': None
            }
        elif isinstance(endpoint_config, dict):
            return {
                'endpoint_url': endpoint_config.get('endpoint_url'),
                'local_port_fwd': endpoint_config.get('local_port_fwd')
            }
        
        return None
    
    def build_ssh_commands(self):
        """Build separate SSH commands for each forwarding group"""
        # Get custom endpoints
        custom_endpoints = self.config.get('custom_endpoints', {})
        mapping_entries = []
        
        # Group 1: SkyStore service (port 3000)
        skystore_cmd = [
            'ssh',
            '-f',  # Go to background after authentication and forwards are established
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=60',
            '-o', 'ServerAliveCountMax=3',
            '-o', 'ExitOnForwardFailure=yes',  # Exit if forward fails
            '-N',  # Don't execute remote command
            '-L', '3000:localhost:3000',  # Forward SkyStore server port
        ]
        if self.ssh_port != 22:
            skystore_cmd.extend(['-p', str(self.ssh_port)])
        skystore_cmd.append(f'{self.ssh_username}@{self.server_ip}')
        
        # Group 2: Local S3 service (if client region is custom with local_port_fwd)
        local_s3_cmd = None
        local_s3_info = None
        if self.client_region.startswith('custom:'):
            client_details = self.get_endpoint_details(self.client_region)
            if client_details and client_details['local_port_fwd']:
                port = client_details['local_port_fwd']
                endpoint_url = client_details['endpoint_url']
                hostname = self.extract_hostname(endpoint_url)
                local_port = urlparse(endpoint_url).port or (443 if endpoint_url.startswith("https") else 80)
                
                local_s3_cmd = [
                    'ssh',
                    '-f',  # Go to background after authentication and forwards are established
                    '-o', 'StrictHostKeyChecking=no',
                    '-o', 'ServerAliveInterval=60',
                    '-o', 'ServerAliveCountMax=3',
                    '-o', 'ExitOnForwardFailure=yes',  # Exit if forward fails
                    '-N',
                    '-R', f'{port}:{hostname}:{local_port}',
                ]
                if self.ssh_port != 22:
                    local_s3_cmd.extend(['-p', str(self.ssh_port)])
                local_s3_cmd.append(f'{self.ssh_username}@{self.server_ip}')
                local_s3_info = f"{self.client_region} ({hostname}:{local_port} -> server:{port})"
        
        # Group 3: Remote S3 services (other custom regions)
        remote_s3_cmd = None
        remote_s3_forwards = []
        remote_s3_cmd_base = [
            'ssh',
            '-f',  # Go to background after authentication and forwards are established
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=60',
            '-o', 'ServerAliveCountMax=3',
            '-o', 'ExitOnForwardFailure=yes',  # Exit if forward fails
            '-N',
        ]
        
        for region_name, endpoint_config in custom_endpoints.items():
            # Skip the client's own region
            if region_name == self.client_region:
                continue
            
            details = self.get_endpoint_details(region_name)
            if details and details['local_port_fwd']:
                port = details['local_port_fwd']
                endpoint_url = details['endpoint_url']
                hostname = self.extract_hostname(endpoint_url)
                
                # Add forward to command
                remote_s3_cmd_base.extend(['-L', f'{port}:localhost:{port}'])
                remote_s3_forwards.append((region_name, hostname, port))
                
                # Update endpoint URL in config
                if self.is_ip_address(hostname):
                    # Replace IP with 127.0.0.1
                    new_url = self.update_endpoint_url(endpoint_url, '127.0.0.1', port)
                else:
                    # DNS name - add to mapping file and update URL with port
                    new_url = self.update_endpoint_url(endpoint_url, hostname, port)
                    mapping_entries.append(hostname)
                
                # Update the endpoint URL in config
                if isinstance(custom_endpoints[region_name], str):
                    custom_endpoints[region_name] = new_url
                elif isinstance(custom_endpoints[region_name], dict):
                    custom_endpoints[region_name]['endpoint_url'] = new_url
        
        if remote_s3_forwards:
            if self.ssh_port != 22:
                remote_s3_cmd_base.extend(['-p', str(self.ssh_port)])
            remote_s3_cmd_base.append(f'{self.ssh_username}@{self.server_ip}')
            remote_s3_cmd = remote_s3_cmd_base
        
        # Write mapping file
        self.write_mapping_file(mapping_entries)
        
        return {
            'skystore': skystore_cmd,
            'local_s3': (local_s3_cmd, local_s3_info),
            'remote_s3': (remote_s3_cmd, remote_s3_forwards)
        }
    
    def remove_local_port_fwd_fields(self):
        """Remove all local_port_fwd fields from custom_endpoints"""
        custom_endpoints = self.config.get('custom_endpoints', {})
        
        for region_name, endpoint_config in custom_endpoints.items():
            if isinstance(endpoint_config, dict) and 'local_port_fwd' in endpoint_config:
                del endpoint_config['local_port_fwd']
                print(f"Removed local_port_fwd from {region_name}")
    
    def find_ssh_pids(self, port_spec):
        """Find SSH process PIDs that match a specific port forward specification"""
        try:
            # Use pgrep to find SSH processes, then filter by command line
            result = subprocess.run(
                ['pgrep', '-f', f'ssh.*{port_spec}'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return [int(pid) for pid in result.stdout.strip().split('\n') if pid]
            return []
        except Exception:
            return []
    
    def cleanup_ssh_tunnels(self, pids):
        """Kill SSH tunnel processes by PID"""
        if not pids:
            return
        
        print(f"Cleaning up {len(pids)} SSH tunnel(s)...", file=sys.stderr)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to PID {pid}", file=sys.stderr)
            except ProcessLookupError:
                pass  # Already stopped
            except Exception as e:
                print(f"Error stopping PID {pid}: {e}", file=sys.stderr)
        
        # Wait and force kill if needed
        time.sleep(2)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass  # Already stopped
            except Exception:
                pass
        print("Cleanup complete", file=sys.stderr)
    
    def write_mapping_file(self, hostnames):
        """Write the hostname mapping file"""
        try:
            mapping_path = Path(self.mapping_file)
            mapping_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.mapping_file, 'w') as f:
                for hostname in hostnames:
                    f.write(f"{hostname}\n")
            
            print(f"Wrote {len(hostnames)} hostname(s) to mapping file: {self.mapping_file}")
        except Exception as e:
            print(f"Error writing mapping file: {e}", file=sys.stderr)
            raise
    
    def start_tunnel(self):
        """Start the SSH tunnels in 3 separate groups"""
        if not self.load_config():
            return False
        
        # Create backup of config
        if not self.backup_config():
            return False
        
        # Build SSH commands (this also modifies the config)
        ssh_commands = self.build_ssh_commands()
        
        # Remove local_port_fwd fields from config
        self.remove_local_port_fwd_fields()
        
        # Save modified config
        if not self.save_config():
            return False
        
        print(f"Starting SSH tunnels to {self.ssh_username}@{self.server_ip}:{self.ssh_port}")
        
        # Track SSH PIDs for cleanup on failure
        ssh_pids = []
        
        try:
            # Dry-run mode: print commands and exit without executing
            if self.dry_run:
                print("\n=== DRY-RUN MODE ===")
                print("Configuration has been backed up and modified.")
                print("The following SSH tunnel commands would be executed:\n")
                
                print("Forward SkyStore service:")
                print(f"  Command: {' '.join(ssh_commands['skystore'])}")
                
                local_s3_cmd, local_s3_info = ssh_commands['local_s3']
                if local_s3_cmd:
                    print("\nForward Local S3 service:")
                    print(f"  Info: {local_s3_info}")
                    print(f"  Command: {' '.join(local_s3_cmd)}")
                else:
                    print("\nForward Local S3 service:")
                    print("  Nothing to forward")
                
                remote_s3_cmd, remote_s3_forwards = ssh_commands['remote_s3']
                if remote_s3_cmd:
                    print("\nForward Remote S3 services:")
                    for region, hostname, port in remote_s3_forwards:
                        print(f"  - {region}: server:{port} -> localhost:{port} ({hostname})")
                    print(f"  Command: {' '.join(remote_s3_cmd)}")
                else:
                    print("\nForward Remote S3 services:")
                    print("  Nothing to forward")
                
                print("\nExiting without executing the tunnels.")
                return True
            
            # Group 1: Forward SkyStore service (MUST succeed)
            print("\nForward SkyStore service:")
            print(f"  Command: {' '.join(ssh_commands['skystore'])}")
            result = subprocess.run(
                ssh_commands['skystore'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"FAILED: {result.stderr}", file=sys.stderr)
                self.cleanup_ssh_tunnels(ssh_pids)
                return False
            # Find and track the SSH PID
            pids = self.find_ssh_pids('3000:localhost:3000')
            ssh_pids.extend(pids)
            print("Done")
            
            # Group 2: Forward Local S3 service (can fail if port already bound)
            local_s3_cmd, local_s3_info = ssh_commands['local_s3']
            if local_s3_cmd:
                print("\nForward Local S3 service:")
                print(f"  Info: {local_s3_info}")
                print(f"  Command: {' '.join(local_s3_cmd)}")
                result = subprocess.run(
                    local_s3_cmd,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    # Forward failed (likely port already bound)
                    print("Local S3 service forward failed - assuming handled by another S3-proxy")
                else:
                    # Find and track the SSH PID
                    # Extract port from local_s3_info for PID search
                    port = local_s3_info.split('server:')[1].split(')')[0] if 'server:' in local_s3_info else ''
                    if port:
                        pids = self.find_ssh_pids(f'{port}:')
                        ssh_pids.extend(pids)
                    print("Done")
            else:
                print("\nForward Local S3 service:")
                print("Nothing to forward")
            
            # Group 3: Forward Remote S3 services (MUST succeed)
            remote_s3_cmd, remote_s3_forwards = ssh_commands['remote_s3']
            if remote_s3_cmd:
                print("\nForward Remote S3 services:")
                for region, hostname, port in remote_s3_forwards:
                    print(f"  - {region}: server:{port} -> localhost:{port} ({hostname})")
                print(f"  Command: {' '.join(remote_s3_cmd)}")
                
                result = subprocess.run(
                    remote_s3_cmd,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    print(f"FAILED: {result.stderr}", file=sys.stderr)
                    self.cleanup_ssh_tunnels(ssh_pids)
                    return False
                # Find and track SSH PIDs for all remote forwards
                for region, hostname, port in remote_s3_forwards:
                    pids = self.find_ssh_pids(f'{port}:localhost:{port}')
                    ssh_pids.extend(pids)
                print("Done")
            else:
                print("\nForward Remote S3 services:")
                print("Nothing to forward")
            
            # All tunnels established successfully
            print(f"\nAll SSH tunnels established successfully")
            
            # Write PID file
            if ssh_pids:
                try:
                    with open(self.pid_file, 'w') as f:
                        for pid in ssh_pids:
                            f.write(f"{pid}\n")
                    print(f"Wrote {len(ssh_pids)} tunnel PID(s) to {self.pid_file}")
                except Exception as e:
                    print(f"Warning: Failed to write PID file: {e}", file=sys.stderr)
            
            print("Tunnels are running in background. Exiting tunneler.")
            return True
            
        except Exception as e:
            print(f"Error starting SSH tunnels: {e}", file=sys.stderr)
            self.cleanup_ssh_tunnels(ssh_pids)
            return False
    
    def stop(self):
        """Stop all SSH tunnels"""
        try:
            if not self.pid_file.exists():
                print("No PID file found, no tunnels to stop")
                return
            
            with open(self.pid_file, 'r') as f:
                pids = [int(line.strip()) for line in f if line.strip()]
            
            if not pids:
                print("No PIDs found in PID file")
                return
            
            print(f"Stopping {len(pids)} SSH tunnel(s)...")
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGTERM)
                    print(f"Sent SIGTERM to PID {pid}")
                except ProcessLookupError:
                    print(f"Process {pid} not found (already stopped)")
                except Exception as e:
                    print(f"Error stopping process {pid}: {e}", file=sys.stderr)
            
            # Wait a bit and force kill if needed
            time.sleep(2)
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                    print(f"Force killed PID {pid}")
                except ProcessLookupError:
                    pass  # Already stopped
                except Exception as e:
                    print(f"Error force killing process {pid}: {e}", file=sys.stderr)
            
            # Remove PID file
            self.pid_file.unlink()
            print("All SSH tunnels stopped")
            
        except Exception as e:
            print(f"Error stopping tunnels: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='SSH Tunnel Manager for SkyStore S3 Proxy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Start tunnels:
    %(prog)s /path/to/config.json 192.168.1.100 22 skystore /tmp/hostname_mapping.txt
  
  Dry-run (show commands without executing):
    %(prog)s -d /path/to/config.json 192.168.1.100 22 skystore /tmp/hostname_mapping.txt
  
  Stop tunnels:
    %(prog)s --stop /path/to/config.json
        """
    )
    
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Dry-run mode: backup and modify config, but only print tunnel commands without executing them')
    parser.add_argument('--stop', action='store_true',
                        help='Stop running SSH tunnels (only requires config_path)')
    parser.add_argument('config_path', help='Path to s3-proxy configuration JSON file')
    parser.add_argument('server_ip', nargs='?', help='SkyStore server IP address (required for start)')
    parser.add_argument('ssh_port', nargs='?', type=int, help='SkyStore server SSH port (required for start)')
    parser.add_argument('ssh_username', nargs='?', help='SSH username for SkyStore server (required for start)')
    parser.add_argument('mapping_file', nargs='?', help='Path to hostname mapping file (required for start)')
    
    args = parser.parse_args()
    
    # Stop mode - only needs config_path
    if args.stop:
        manager = TunnelManager('', 22, '', args.config_path, '', dry_run=False)
        manager.stop()
        sys.exit(0)
    
    # Start mode - validate all required arguments
    if not all([args.server_ip, args.ssh_port, args.ssh_username, args.mapping_file]):
        parser.error("server_ip, ssh_port, ssh_username, and mapping_file are required for starting tunnels")
    
    # Create tunnel manager for start
    manager = TunnelManager(
        args.server_ip,
        args.ssh_port,
        args.ssh_username,
        args.config_path,
        args.mapping_file,
        dry_run=args.dry_run
    )
    
    # Start tunnel (runs in background, or prints command in dry-run mode)
    if not manager.start_tunnel():
        sys.exit(1)
    
    # Exit successfully - tunnel is running in background (or dry-run completed)
    sys.exit(0)


if __name__ == '__main__':
    main()

# Made with Bob
