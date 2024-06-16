#!/bin/bash

prefix=$1

for n in base server s3proxy; do
    docker push $prefix/skystore-$n:latest;
done
 
