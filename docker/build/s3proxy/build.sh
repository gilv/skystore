#!/bin/bash

: ${SKY_TAG_PREFIX:=""}
: ${SKY_TAG_SUFFIX:="latest"}

[[ -n "$SKY_TAG_PREFIX" ]] && ! [[ "$SKY_TAG_PREFIX" == */ ]] && SKY_TAG_PREFIX="$SKY_TAG_PREFIX/"

DOCKER_BUILDKIT=1 docker buildx build $SKY_BUILD_ARGS -t ${SKY_TAG_PREFIX}skystore-s3proxy:${SKY_TAG_SUFFIX} .

