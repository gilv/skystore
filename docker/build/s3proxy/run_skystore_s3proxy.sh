#!/bin/bash

# Set up SSH client configuration with private key
mkdir -p $HOME/.ssh
echo "$SKYSTORE_PRV_KEY" | base64 -d > $HOME/.ssh/id_rsa
chmod 600 $HOME/.ssh/id_rsa
chown -R $USER:$USER $HOME/.ssh

# Set up SSH tunnel - skystore server address must be specified and valid
/usr/bin/ssh -o "StrictHostKeyChecking no" -L 3000:localhost:3000 -N -f $SSH_USERNAME@$SKYSTORE_SRV_ADDR
if [[ $? -ne 0 ]]; then
    echo "Could not establish SSH tunnel to: $SSH_USERNAME@$SKYSTORE_SRV_ADDR"
    exit 1
fi

# Set up Rust env
. "$HOME/.cargo/env"

# Must have valid keys for accessing the assigned S3 storage
mkdir -p $HOME/.aws
echo "$S3_CFG" | base64 -d > $HOME/.aws/config

# Load the s3-proxy service from the configuration
echo "$SKYSTORE_S3P_CFG" | base64 -d > /skystore/config.json
cd /skystore/skystore/s3-proxy
skystore init --config=/skystore/config.json 

# S3-proxy is running - infinite loop with sleep to avoid busy wait
while true
do
    sleep 1
done



