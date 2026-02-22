# wrap_s3p.sh - S3 Proxy Wrapper Script

This wrapper script enables s3-proxy to access S3 services through SSH-forwarded ports by mapping hostnames to localhost.

## Overview

The wrapper script works in conjunction with the tunneler to enable hostname resolution for forwarded S3 services. It supports two modes of operation:

1. **Container Mode** (`RUN_IN_CNTR=1`): Directly modifies `/etc/hosts` (requires root in container)
2. **Namespace Mode** (default): Uses `unshare` to create an isolated mount namespace with a custom `/etc/hosts`

## Usage

```bash
./wrap_s3p.sh <mapping_file> [s3-proxy arguments...]
```

### Arguments

- `mapping_file`: Path to the hostname mapping file created by tunneler
- `[s3-proxy arguments...]`: All remaining arguments are passed to the s3-proxy (skystore) command

### Environment Variables

- `RUN_IN_CNTR`: Set to `1` to run in container mode (default: `0`)

## Examples

### Container Mode (Docker/Kubernetes)

```bash
export RUN_IN_CNTR=1
./wrap_s3p.sh /tmp/hostname_mapping.txt init --config=/etc/skystore/config.json
```

### Namespace Mode (Host System)

```bash
./wrap_s3p.sh /tmp/hostname_mapping.txt init --config=/etc/skystore/config.json
```

## How It Works

### Container Mode

1. Reads hostnames from the mapping file
2. Backs up `/etc/hosts` to `/etc/hosts.skystore.backup`
3. Appends hostname mappings to `/etc/hosts` (all mapped to 127.0.0.1)
4. Executes s3-proxy with the modified `/etc/hosts`
5. On exit, removes the added mappings from `/etc/hosts`

### Namespace Mode

1. Reads hostnames from the mapping file
2. Creates a temporary directory with a custom `hosts` file
3. Copies system `/etc/hosts` and adds hostname mappings
4. Uses `unshare -m` to create a mount namespace
5. Bind mounts the custom hosts file over `/etc/hosts`
6. Executes s3-proxy in the isolated namespace
7. Cleans up temporary files on exit

## Integration with Tunneler

The typical workflow is:

1. **Tunneler** sets up SSH tunnels and creates the mapping file
2. **wrap_s3p.sh** uses the mapping file to configure hostname resolution
3. **s3-proxy** accesses forwarded S3 services through localhost

Example complete workflow:

```bash
# Step 1: Start tunneler (runs in background)
./tunneler/tunneler.py 192.168.1.100 22 skystore /etc/skystore/config.json /tmp/hostname_mapping.txt

# Step 2: Run s3-proxy with wrapper
export RUN_IN_CNTR=1  # If in container
./wrap_s3p.sh /tmp/hostname_mapping.txt init --config=/etc/skystore/config.json
```

## Requirements

### Container Mode
- Root privileges inside the container
- Write access to `/etc/hosts`

### Namespace Mode
- `unshare` command (from util-linux package)
- Sufficient privileges to create mount namespaces

## Troubleshooting

### "unshare command is not available"

Install the util-linux package:
```bash
# Debian/Ubuntu
apt-get install util-linux

# RHEL/CentOS
yum install util-linux
```

Or use container mode instead:
```bash
export RUN_IN_CNTR=1
```

### "Container mode requires root privileges"

Ensure you're running as root inside the container, or use a container runtime that provides root access.

### Hostname mappings not working

1. Verify the mapping file exists and contains hostnames
2. Check that the tunneler successfully created the file
3. Ensure hostnames in the mapping file match those in the configuration

## Security Considerations

- **Container Mode**: Modifies system-wide `/etc/hosts`, affecting all processes in the container
- **Namespace Mode**: Isolated to the s3-proxy process only, more secure
- Both modes clean up on exit, but unexpected termination may leave mappings in place
- The backup file `/etc/hosts.skystore.backup` is created only once to preserve the original state