#!/bin/bash

SKY_BUILD_ARGS=""

# Uncomment below to enable build options as needed

# Ignore build cache - force fresh build
#SKY_BUILD_ARGS="$SKY_BUILD_ARGS --no-cache"

# Plain progress - for capturing build errors
#SKY_BUILD_ARGS="$SKY_BUILD_ARGS --progress=plain"

# Multi-platform - simple tags without platform label but requires immediate tag (SKY_TAG_..) and push
#SKY_BUILD_ARGS="$SKY_BUILD_ARGS --platform linux/amd64,linux/arm64 --push"

export SKY_BUILD_ARGS

# Uncomment and set tag values for immediate tags (required for multi-arch)
#export SKY_TAG_PREFIX="y3z2bluo.gra7.container-registry.ovh.net/skystore"
#export SKY_TAG_SUFFIX="tun_v5"

for n in base server s3proxy; do
    cd $n;
    ./build.sh;
    cd ..;
done


