#!/bin/bash

prefix="$2"
TAG_SUFFIX=$3
: ${TAG_SUFFIX:=latest}


# Add slash if prefix is non-empty and does not end with slash
[[ -n "$prefix" ]] && ! [[ "$prefix" == */ ]] && prefix="$prefix/"

docker run -d --env-file=$1 "$prefix"skystore-server:$TAG_SUFFIX

