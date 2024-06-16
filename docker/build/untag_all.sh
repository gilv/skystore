#!/bin/bash

prefix=$1

for n in base server s3proxy; do
    docker image rm -f $prefix/skystore-$n:latest;
done
 
