#!/bin/bash

prefix=$1

# Add slash if prefix is non-empty and does not end with slash
[[ -n "$prefix" ]] && ! [[ "$prefix" == */ ]] && prefix="$prefix/"

for n in base server s3proxy; do
    docker tag skystore-$n:latest "$prefix"skystore-$n:latest;
done
 
