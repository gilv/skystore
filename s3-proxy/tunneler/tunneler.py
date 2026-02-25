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
    
    def write_pid_file(self):
        """Write the SSH tunnel PID to a file"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(self.ssh_process.pid))
            print(f"Wrote tunnel PID {self.ssh_process.pid} to {self.pid_file}")
            return True
        except Exception as e:
            print(f"Error writing PID file: {e}", file=sys.stderr)
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
    
    def build_ssh_command(self):
        """Build the SSH command with all necessary port forwards"""
        # Base SSH command with tunnel to SkyStore server port 3000
        ssh_cmd = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ServerAliveInterval=60',
            '-o', 'ServerAliveCountMax=3',
            '-N',  # Don't execute remote command
            '-L', '3000:localhost:3000',  # Forward SkyStore server port
        ]
        
        # Get custom endpoints
        custom_endpoints = self.config.get('custom_endpoints', {})
        mapping_entries = []
        
        # Check if client region needs forwarding (forward local S3 to server)
        if self.client_region.startswith('custom:'):
            client_details = self.get_endpoint_details(self.client_region)
            if client_details and client_details['local_port_fwd']:
                port = client_details['local_port_fwd']
                endpoint_url = client_details['endpoint_url']
                hostname = self.extract_hostname(endpoint_url)
                
                # Forward local S3 service to server
                # -R remote_port:local_host:local_port
                ssh_cmd.extend(['-R', f'{port}:{hostname}:{urlparse(endpoint_url).port or (443 if endpoint_url.startswith("https") else 80)}'])
                print(f"Forwarding local S3 service {self.client_region} to server port {port}")
        
        # Forward other custom regions from server to local
        for region_name, endpoint_config in custom_endpoints.items():
            # Skip the client's own region
            if region_name == self.client_region:
                continue
            
            details = self.get_endpoint_details(region_name)
            if details and details['local_port_fwd']:
                port = details['local_port_fwd']
                endpoint_url = details['endpoint_url']
                hostname = self.extract_hostname(endpoint_url)
                
                # Forward from server to local
                # -L local_port:localhost:remote_port
                ssh_cmd.extend(['-L', f'{port}:localhost:{port}'])
                
                # Update endpoint URL in config
                if self.is_ip_address(hostname):
                    # Replace IP with 127.0.0.1
                    new_url = self.update_endpoint_url(endpoint_url, '127.0.0.1', port)
                    print(f"Forwarding remote S3 service {region_name} from server port {port} to local port {port} (IP: {hostname} -> 127.0.0.1:{port})")
                else:
                    # DNS name - add to mapping file and update URL with port
                    new_url = self.update_endpoint_url(endpoint_url, hostname, port)
                    mapping_entries.append(hostname)
                    print(f"Forwarding remote S3 service {region_name} from server port {port} to local port {port} (DNS: {hostname}:{port})")
                
                # Update the endpoint URL in config
                if isinstance(custom_endpoints[region_name], str):
                    custom_endpoints[region_name] = new_url
                elif isinstance(custom_endpoints[region_name], dict):
                    custom_endpoints[region_name]['endpoint_url'] = new_url
        
        # Add SSH connection details
        ssh_cmd.append(f'{self.ssh_username}@{self.server_ip}')
        if self.ssh_port != 22:
            ssh_cmd.insert(1, '-p')
            ssh_cmd.insert(2, str(self.ssh_port))
        
        # Write mapping file
        self.write_mapping_file(mapping_entries)
        
        return ssh_cmd
    
    def remove_local_port_fwd_fields(self):
        """Remove all local_port_fwd fields from custom_endpoints"""
        custom_endpoints = self.config.get('custom_endpoints', {})
        
        for region_name, endpoint_config in custom_endpoints.items():
            if isinstance(endpoint_config, dict) and 'local_port_fwd' in endpoint_config:
                del endpoint_config['local_port_fwd']
                print(f"Removed local_port_fwd from {region_name}")
    
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
        """Start the SSH tunnel"""
        if not self.load_config():
            return False
        
        # Create backup of config
        if not self.backup_config():
            return False
        
        # Build SSH command (this also modifies the config)
        ssh_cmd = self.build_ssh_command()
        
        # Remove local_port_fwd fields from config
        self.remove_local_port_fwd_fields()
        
        # Save modified config
        if not self.save_config():
            return False
        
        print(f"Starting SSH tunnel to {self.ssh_username}@{self.server_ip}:{self.ssh_port}")
        print(f"Command: {' '.join(ssh_cmd)}")
        
        # Dry-run mode: print command and exit without executing
        if self.dry_run:
            print("\n=== DRY-RUN MODE ===")
            print("Configuration has been backed up and modified.")
            print("The following SSH tunnel command would be executed:")
            print(f"\n{' '.join(ssh_cmd)}\n")
            print("Exiting without executing the tunnel.")
            return True
        
        try:
            self.ssh_process = subprocess.Popen(
                ssh_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent process
            )
            
            # Wait a bit to see if the process starts successfully
            time.sleep(2)
            
            if self.ssh_process.poll() is not None:
                # Process has terminated
                _, stderr = self.ssh_process.communicate()
                print(f"SSH tunnel failed to start: {stderr.decode()}", file=sys.stderr)
                return False
            
            print(f"SSH tunnel established (PID: {self.ssh_process.pid})")
            
            # Write PID file
            if not self.write_pid_file():
                print("Warning: Failed to write PID file, but tunnel is running", file=sys.stderr)
            
            print("Tunnel is running in background. Exiting tunneler.")
            return True
            
        except Exception as e:
            print(f"Error starting SSH tunnel: {e}", file=sys.stderr)
            return False
    
    def stop(self):
        """Stop the SSH tunnel"""
        if self.ssh_process and self.ssh_process.poll() is None:
            print("Stopping SSH tunnel...")
            self.ssh_process.terminate()
            try:
                self.ssh_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Force killing SSH tunnel...")
                self.ssh_process.kill()
            print("SSH tunnel stopped")


def main():
    parser = argparse.ArgumentParser(
        description='SSH Tunnel Manager for SkyStore S3 Proxy',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s 192.168.1.100 22 skystore /path/to/config.json /tmp/hostname_mapping.txt
  %(prog)s -d 192.168.1.100 22 skystore /path/to/config.json /tmp/hostname_mapping.txt
        """
    )
    
    parser.add_argument('-d', '--dry-run', action='store_true',
                        help='Dry-run mode: backup and modify config, but only print tunnel commands without executing them')
    parser.add_argument('server_ip', help='SkyStore server IP address')
    parser.add_argument('ssh_port', type=int, help='SkyStore server SSH port')
    parser.add_argument('ssh_username', help='SSH username for SkyStore server')
    parser.add_argument('config_path', help='Path to s3-proxy configuration JSON file')
    parser.add_argument('mapping_file', help='Path to hostname mapping file (will be created)')
    
    args = parser.parse_args()
    
    # Create tunnel manager
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
