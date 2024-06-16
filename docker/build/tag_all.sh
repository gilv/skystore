#!/bin/bash

prefix=$1

for n in base server s3proxy; do
    docker tag skystore-$n:latest $prefix/skystore-$n:latest;
done
 
