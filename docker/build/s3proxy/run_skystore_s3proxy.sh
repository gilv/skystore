#!/bin/bash

: ${RUN_IN_CNTR:=1}

# Set up SSH client configuration with private key
mkdir -p $HOME/.ssh
echo "$SKYSTORE_PRV_KEY" | base64 -d > $HOME/.ssh/id_rsa
chmod 600 $HOME/.ssh/id_rsa
chown -R $USER:$USER $HOME/.ssh

# Set up Rust env
. "$HOME/.cargo/env"

# Must have valid keys for accessing the assigned S3 storage
mkdir -p $HOME/.aws
echo "$S3_CFG" | base64 -d > $HOME/.aws/config

# Write the s3-proxy configuration
echo "$SKYSTORE_S3P_CFG" | base64 -d > /skystore/config.json

cd /skystore/s3-proxy

# Set up SSH tunnel - skystore server address must be specified and valid
echo "Setting up SSH tunnel[s] to SkyStore server"
python tunneler/tunneler.py /skystore/config.json $SKYSTORE_SRV_ADDR $SSH_PORT $SSH_USERNAME /skystore/mapping.txt
if [[ $? -ne 0 ]]; then
    echo "Could not establish SSH tunnel[s] to: $SSH_USERNAME@$SKYSTORE_SRV_ADDR"
    exit 1
fi

# Check if mapping.txt exists and is non-empty
if [[ ! -f /skystore/mapping.txt ]] || [[ ! -s /skystore/mapping.txt ]]; then
    echo "mapping.txt is non-existent or empty, running s3-proxy directly"
    ./run_s3p.sh /skystore/config.json
else
    echo "mapping.txt exists and is non-empty, using wrap_s3p.sh"
    tunneler/wrap_s3p.sh /skystore/mapping.txt ./run_s3p.sh /skystore/config.json
fi


