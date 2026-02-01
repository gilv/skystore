#!/bin/bash

# Uncomment below to force clean build and plain output for logs
# export SKY_BUILD_ARGS="--no-cache --progress=plain"

for n in base server s3proxy; do
    cd $n;
    ./build.sh;
    cd ..;
done


