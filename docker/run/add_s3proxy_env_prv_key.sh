#!/bin/bash

basepath=$(dirname $0)

cp $1 $1.withprvkey
echo "SKYSTORE_PRV_KEY="$($basepath/encode.sh keys/skystore) >> $1.withprvkey
 
