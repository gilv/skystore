#!/bin/bash

# Rust env
. "$HOME/.cargo/env"

# Env w/default values
: ${AUTHORIZED_KEYS:="$SKYSTORE_PUB_KEY"}
: ${INIT_REGIONS:="aws:eu-central-1,aws:eu-west-1"}
: ${SKYSTORE_BUCKET_PREFIX:="skystore-extract"}

# Launch Sky Store server
cd /skystore/skystore/s3-proxy
just run-skystore-server &

# Launch the SSH service using the inherited ENV
/usr/local/bin/configure-ssh-user.sh




