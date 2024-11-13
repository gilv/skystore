#!/bin/bash

# Uncomment below to force clean build
# export SKY_BUILD_ARGS="--no-cache"

for n in base server s3proxy; do
    cd $n;
    ./build.sh;
    cd ..;
done


