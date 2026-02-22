# SkyStore S3 Proxy Tunneler

This tool sets up SSH tunnels to forward S3 services through the SkyStore server, enabling access to S3 services without public IP addresses (e.g., local Minio deployments inside clusters).

## Overview

The tunneler enables s3-proxy instances to access S3 services that don't have publicly reachable IP addresses by:

1. Forwarding the local S3 service to the SkyStore server (if the client region uses `local_port_fwd`)
2. Forwarding remote S3 services from the SkyStore server to the local machine
3. Modifying the configuration file to use localhost addresses and ports
4. Creating a hostname mapping file for DNS-based endpoints

## Usage

```bash
./tunneler.py <server_ip> <ssh_port> <ssh_username> <config_path> <mapping_file>
```

### Arguments

- `server_ip`: SkyStore server IP address
- `ssh_port`: SSH port on the SkyStore server
- `ssh_username`: SSH username for authentication
- `config_path`: Path to the s3-proxy configuration JSON file
- `mapping_file`: Path where the hostname mapping file will be created

### Example

```bash
./tunneler.py 192.168.1.100 22 skystore /etc/skystore/config.json /tmp/hostname_mapping.txt
```

## How It Works

### 1. Configuration Backup

The tunneler creates a backup of the configuration file with a `.backup` extension before making any modifications.

### 2. SSH Tunnel Setup

The tunneler establishes an SSH tunnel with the following forwards:

- **SkyStore Server Port**: Always forwards port 3000 for the SkyStore metadata service
- **Local S3 Service**: If the client region has `local_port_fwd` set, forwards that service to the server
- **Remote S3 Services**: For each custom region (except the client's own) with `local_port_fwd`, forwards from server to local

### 3. Configuration Modification

For each remote S3 service with `local_port_fwd`:

- **IP-based endpoints**: Replaces the IP with `127.0.0.1` and adds the forwarded port
- **DNS-based endpoints**: Keeps the hostname, adds the forwarded port, and adds the hostname to the mapping file

All `local_port_fwd` fields are removed from the configuration after processing.

### 4. Background Operation

The tunneler:
- Writes the SSH process PID to `tunnel.pid` in the same directory as the config file
- Runs the SSH tunnel in the background
- Exits, allowing other processes (like s3-proxy) to start

## Configuration Format

Custom endpoints in the s3-proxy configuration can include a `local_port_fwd` field:

```json
{
  "custom_endpoints": {
    "custom:minio-local": {
      "endpoint_url": "http://minio.cluster.local:9000",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1",
      "local_port_fwd": 9000
    }
  }
}
```

After tunneler runs, this becomes:

```json
{
  "custom_endpoints": {
    "custom:minio-local": {
      "endpoint_url": "http://minio.cluster.local:9000",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1"
    }
  }
}
```

And `minio.cluster.local` is added to the mapping file.

## Files Created

- `<config_path>.backup`: Backup of the original configuration
- `<mapping_file>`: List of DNS hostnames to be mapped to 127.0.0.1
- `tunnel.pid`: PID of the SSH tunnel process (in the same directory as config file)

## Requirements

- Python 3.6+
- SSH client
- SSH access to the SkyStore server
- Network connectivity to local S3 services (for the client region)