# Local Port Forwarding for S3 Services

This document describes the local port forwarding feature that enables s3-proxy instances to access S3 services without public IP addresses, such as local Minio deployments inside Kubernetes clusters.

## Overview

The feature allows each s3-proxy to access all S3 services, even those that are not directly reachable from the network, by leveraging SSH tunnels through the main SkyStore server.
The implementation is completely transparent to the core code of SkyStore. Extra configuration is removed after being processed. 

### Architecture

```
┌─────────────────┐         SSH Tunnel          ┌─────────────────┐
│   S3-Proxy A    │◄──────────────────────────►│  SkyStore       │
│  (Cluster A)    │                             │  Main Server    │
│                 │                             │                 │
│ Local Minio A   │─────Forward Port 9001──────►│  Port 9001      │
│ (unreachable)   │                             │                 │
└─────────────────┘                             └─────────────────┘
                                                         │
                                                         │ Forward
                                                         │ Port 9002
                                                         ▼
┌─────────────────┐         SSH Tunnel          ┌─────────────────┐
│   S3-Proxy B    │◄──────────────────────────►│  Port 9002      │
│  (Cluster B)    │                             │                 │
│                 │                             │                 │
│ Local Minio B   │─────Forward Port 9002──────►│                 │
│ (unreachable)   │                             │                 │
└─────────────────┘                             └─────────────────┘
```

Each s3-proxy:
1. Forwards its local S3 service to the main server (if it has `local_port_fwd`)
2. Forwards remote S3 services from the main server to its local machine
3. Accesses remote services through localhost with hostname mapping

## Components

### 1. Tunneler Script

**Location**: `skystore/s3-proxy/tunneler/tunneler.py`

**Purpose**: Sets up SSH tunnels and modifies the configuration file

**Workflow**:
1. Reads the s3-proxy configuration JSON file
2. Creates a backup of the configuration (`.backup` extension)
3. Establishes SSH tunnel to the SkyStore server
4. Forwards local S3 service to server (if client region has `local_port_fwd`)
5. Forwards remote S3 services from server to local machine
6. Modifies endpoint URLs in the configuration:
   - IP addresses → `127.0.0.1:port`
   - DNS names → `hostname:port` (adds to mapping file)
7. Removes all `local_port_fwd` fields from the configuration
8. Writes SSH tunnel PID to `tunnel.pid`
9. Runs in background

**Usage**:
```bash
./tunneler.py <server_ip> <ssh_port> <ssh_username> <config_path> <mapping_file>
```

### 2. Wrapper Script

**Location**: `skystore/s3-proxy/wrap_s3p.sh`

**Purpose**: Configures hostname resolution for s3-proxy

**Modes**:
- **Container Mode** (`RUN_IN_CNTR=1`): Modifies `/etc/hosts` directly
- **Namespace Mode** (default): Uses `unshare` for isolated hostname mapping

**Usage**:
```bash
./wrap_s3p.sh <mapping_file> [s3-proxy arguments...]
```

## Configuration Example

### Before Tunneler

```json
{
  "init_regions": [
    "aws:eu-central-1",
    "custom:minio-cluster-a",
    "custom:minio-cluster-b"
  ],
  "client_from_region": "custom:minio-cluster-a",
  "skystore_bucket_prefix": "skystore-test",
  "policy": "write_local",
  "server_addr": "192.168.1.100",
  "custom_endpoints": {
    "custom:minio-cluster-a": {
      "endpoint_url": "http://minio.cluster-a.local:9000",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1",
      "local_port_fwd": 9001
    },
    "custom:minio-cluster-b": {
      "endpoint_url": "http://minio.cluster-b.local:9000",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1",
      "local_port_fwd": 9002
    }
  }
}
```

### After Tunneler

```json
{
  "init_regions": [
    "aws:eu-central-1",
    "custom:minio-cluster-a",
    "custom:minio-cluster-b"
  ],
  "client_from_region": "custom:minio-cluster-a",
  "skystore_bucket_prefix": "skystore-test",
  "policy": "write_local",
  "server_addr": "192.168.1.100",
  "custom_endpoints": {
    "custom:minio-cluster-a": {
      "endpoint_url": "http://minio.cluster-a.local:9000",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1"
    },
    "custom:minio-cluster-b": {
      "endpoint_url": "http://minio.cluster-b.local:9002",
      "aws_access_key_id": "minioadmin",
      "aws_secret_access_key": "minioadmin",
      "region": "us-east-1"
    }
  }
}
```

**Mapping File** (`/tmp/hostname_mapping.txt`):
```
minio.cluster-b.local
```

## Complete Workflow

### Step 1: Prepare Configuration

Create a configuration file with `local_port_fwd` fields for S3 services that need forwarding:

```json
{
  "custom_endpoints": {
    "custom:my-minio": {
      "endpoint_url": "http://minio.internal:9000",
      "local_port_fwd": 9000
    }
  }
}
```

### Step 2: Start Tunneler

```bash
cd skystore/s3-proxy/tunneler
./tunneler.py 192.168.1.100 22 skystore /path/to/config.json /tmp/hostname_mapping.txt
```

The tunneler will:
- Create `config.json.backup`
- Modify `config.json` with updated endpoint URLs
- Create `/tmp/hostname_mapping.txt` with DNS names
- Write `tunnel.pid` with the SSH process ID
- Run in background

### Step 3: Start S3-Proxy with Wrapper

**In Container**:
```bash
export RUN_IN_CNTR=1
./wrap_s3p.sh /tmp/hostname_mapping.txt init --config=/path/to/config.json
```

**On Host**:
```bash
./wrap_s3p.sh /tmp/hostname_mapping.txt init --config=/path/to/config.json
```

### Step 4: S3-Proxy Operation

The s3-proxy now has access to all S3 services:
- Local services through their original endpoints
- Forwarded services through localhost with hostname mapping

## Use Cases

### 1. Multi-Cluster Minio Deployment

Each Kubernetes cluster has its own Minio instance that's not externally accessible. S3-proxies in different clusters can access each other's Minio through the SkyStore server.

### 2. Private Cloud Storage

S3-compatible storage services in private networks can be accessed by s3-proxies in other networks through SSH tunneling.

### 3. Development and Testing

Local Minio instances on developer machines can be integrated into a distributed SkyStore setup for testing.

## Security Considerations

1. **SSH Keys**: Ensure proper SSH key management for tunnel authentication
2. **Port Conflicts**: Choose unique port numbers for each S3 service
3. **Network Isolation**: The tunneler creates isolated network namespaces (in namespace mode)
4. **Configuration Backup**: Always keep the `.backup` file for recovery

## Troubleshooting

### Tunnel Not Established

Check the tunnel PID file and SSH process:
```bash
cat tunnel.pid
ps aux | grep $(cat tunnel.pid)
```

### Hostname Resolution Fails

Verify the mapping file:
```bash
cat /tmp/hostname_mapping.txt
```

Check if hostnames are mapped (container mode):
```bash
grep "SkyStore" /etc/hosts
```

### Port Already in Use

Ensure no other process is using the forwarded ports:
```bash
netstat -tuln | grep <port>
```

### Configuration Issues

Restore from backup if needed:
```bash
cp config.json.backup config.json
```

## Limitations

1. **SSH Dependency**: Requires SSH access to the SkyStore server
2. **Port Management**: Manual port number assignment required
3. **Single Server**: All tunnels go through one SkyStore server
4. **Network Overhead**: Additional latency from SSH tunneling

## Future Enhancements

- Automatic port allocation
- Multiple SkyStore servers for redundancy
- Direct peer-to-peer tunneling between s3-proxies
- Dynamic tunnel management (add/remove services without restart)