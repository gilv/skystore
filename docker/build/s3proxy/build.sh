#!/bin/bash

DOCKER_BUILDKIT=1 docker buildx build $SKY_BUILD_ARGS -t skystore-s3proxy .

