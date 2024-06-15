#!/bin/bash

cd base
./build.sh
cd ..

cd server
./build.sh
cd ..

cd s3proxy
./build.sh
cd ..

