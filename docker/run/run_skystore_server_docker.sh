#!/bin/bash

prefix="$2"

# Add slash if prefix is non-empty and does not end with slash
[[ -n "$prefix" ]] && ! [[ "$prefix" == */ ]] && prefix="$prefix/"

docker run -d --env-file=$1 "$prefix"skystore-server

