#!/bin/bash
# Wrapper script for s3-proxy that handles hostname mapping for forwarded S3 services
# Usage: wrap_s3p.sh <mapping_file> <command> [command arguments...]

set -e

# Check if mapping file and command arguments are provided
if [ $# -lt 2 ]; then
    echo "Error: Missing required arguments" >&2
    echo "Usage: $0 <mapping_file> <command> [command arguments...]" >&2
    exit 1
fi

MAPPING_FILE="$1"
shift  # Remove mapping file from arguments
COMMAND="$1"
shift  # Remove command from arguments, rest are for the command

# Check if mapping file exists
if [ ! -f "$MAPPING_FILE" ]; then
    echo "Error: Mapping file not found: $MAPPING_FILE" >&2
    exit 1
fi

# Read hostnames from mapping file
HOSTNAMES=()
while IFS= read -r line; do
    # Skip empty lines
    if [ -n "$line" ]; then
        HOSTNAMES+=("$line")
    fi
done < "$MAPPING_FILE"

echo "Loaded ${#HOSTNAMES[@]} hostname(s) from mapping file"

# Check RUN_IN_CNTR environment variable (default to 0 if not set)
RUN_IN_CNTR="${RUN_IN_CNTR:-0}"

if [ "$RUN_IN_CNTR" = "1" ]; then
    echo "Running s3-proxy in container mode with /etc/hosts modification"
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo "Error: Container mode requires root privileges" >&2
        exit 1
    fi
    
    # Backup /etc/hosts
    HOSTS_BACKUP="/etc/hosts.skystore.backup"
    if [ ! -f "$HOSTS_BACKUP" ]; then
        cp /etc/hosts "$HOSTS_BACKUP"
        echo "Created backup of /etc/hosts at $HOSTS_BACKUP"
    fi
    
    # Add hostname mappings to /etc/hosts
    echo "" >> /etc/hosts
    echo "# SkyStore S3 Proxy hostname mappings (added by wrap_s3p.sh)" >> /etc/hosts
    for hostname in "${HOSTNAMES[@]}"; do
        # Check if hostname already exists in /etc/hosts
        if ! grep -q "^127.0.0.1[[:space:]].*${hostname}" /etc/hosts; then
            echo "127.0.0.1 ${hostname}" >> /etc/hosts
            echo "Mapped ${hostname} -> 127.0.0.1 in /etc/hosts"
        else
            echo "Hostname ${hostname} already mapped in /etc/hosts"
        fi
    done
    
    # Set up cleanup trap to restore /etc/hosts on exit
    cleanup() {
        echo "Cleaning up /etc/hosts..."
        if [ -f "$HOSTS_BACKUP" ]; then
            # Remove SkyStore entries
            sed -i '/# SkyStore S3 Proxy hostname mappings/,/^$/d' /etc/hosts
            echo "Removed SkyStore hostname mappings from /etc/hosts"
        fi
    }
    trap cleanup EXIT INT TERM
    
    # Execute command
    echo "Executing: $COMMAND $@"
    exec "$COMMAND" "$@"
    
else
    echo "Running s3-proxy with mount namespace isolation (unshare)"
    
    # Check if unshare is available
    if ! command -v unshare &> /dev/null; then
        echo "Error: unshare command is not available" >&2
        echo "Please install util-linux package or set RUN_IN_CNTR=1 if running in a container" >&2
        exit 1
    fi
    
    # Create a temporary directory for our custom /etc
    TEMP_ETC=$(mktemp -d)
    trap "rm -rf $TEMP_ETC" EXIT
    
    # Copy system /etc/hosts to temp location
    cp /etc/hosts "$TEMP_ETC/hosts"
    
    # Add hostname mappings to the custom hosts file
    echo "" >> "$TEMP_ETC/hosts"
    echo "# SkyStore S3 Proxy hostname mappings" >> "$TEMP_ETC/hosts"
    for hostname in "${HOSTNAMES[@]}"; do
        echo "127.0.0.1 ${hostname}" >> "$TEMP_ETC/hosts"
        echo "Mapping ${hostname} -> 127.0.0.1"
    done
    
    # Use unshare to create a mount namespace and bind mount our custom hosts file
    echo "Executing: unshare -m bash -c 'mount --bind $TEMP_ETC/hosts /etc/hosts && $COMMAND $@'"
    exec unshare -m bash -c "mount --bind $TEMP_ETC/hosts /etc/hosts && exec $COMMAND $*"
fi

# Made with Bob
