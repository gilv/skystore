#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Call scripts from the script's directory
"$SCRIPT_DIR/add_s3proxy_env_prv_key.sh" env.base
"$SCRIPT_DIR/add_s3proxy_env_s3_cfg.sh" env.base.withprvkey aws.config
"$SCRIPT_DIR/add_s3proxy_env_s3pjson_cfg.sh" env.base.withprvkey.withs3cfg s3proxy.json
mv env.base.withprvkey.withs3cfg.withs3pjsoncfg env.final
rm -f *with*

