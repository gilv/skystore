#!/bin/bash

prefix=$1

TAG_SUFFIX=$2
: ${TAG_SUFFIX:=latest}

# Add slash if prefix is non-empty and does not end with slash
[[ -n "$prefix" ]] && ! [[ "$prefix" == */ ]] && prefix="$prefix/"

for n in base server s3proxy; do
    docker push "$prefix"skystore-$n:$TAG_SUFFIX;
done
 
