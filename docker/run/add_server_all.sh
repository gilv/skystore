#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call add_server_env_pub_key.sh from the script's directory
"$SCRIPT_DIR/add_server_env_pub_key.sh" env.base
mv env.base.withpubkey env.final
rm -f *with*

