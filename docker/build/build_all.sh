#!/bin/bash

SKY_BULD_ARGS=""

# Uncomment below to enable build options as needed

# Ignore build cache - force fresh build
# SKY_BULD_ARGS="$SKY_BUILD_ARGS --no-cache"

# Plain progress - for capturing build errors
# SKY_BULD_ARGS="$SKY_BUILD_ARGS --progress=plain"

# Multi-platform - simple tags without platform label
# SKY_BULD_ARGS="$SKY_BUILD_ARGS --platform linux/amd64,linux/arm64"

export SKY_BUILD_ARGS

for n in base server s3proxy; do
    cd $n;
    ./build.sh;
    cd ..;
done


