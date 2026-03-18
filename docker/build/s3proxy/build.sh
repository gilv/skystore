#!/bin/bash

: ${SKY_TAG_PREFIX:=""}
: ${SKY_TAG_SUFFIX:=""}
: ${BUILD_CMD:="docker build"}
: ${SCRIPT_DIR:="."}

[[ -n "$SKY_TAG_PREFIX" ]] && ! [[ "$SKY_TAG_PREFIX" == */ ]] && SKY_TAG_PREFIX="$SKY_TAG_PREFIX/"

CUSTOM_TAG=""
[[ -n "$SKY_TAG_PREFIX" ]] && [[ -z "$SKY_TAG_SUFFIX" ]] && SKY_TAG_SUFFIX="latest"
([[ -n "$SKY_TAG_PREFIX" ]] || [[ -n "$SKY_TAG_SUFFIX" ]]) && CUSTOM_TAG="-t ${SKY_TAG_PREFIX}skystore-s3proxy:${SKY_TAG_SUFFIX}"

${BUILD_CMD} $SKY_BUILD_ARGS -f ${SCRIPT_DIR}/s3proxy/Dockerfile -t skystore-s3proxy:latest ${CUSTOM_TAG} .

