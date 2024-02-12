#!/bin/bash

FILES=$(find .github -type f -name "*.yml")

for FILE in $FILES; do
    docker run -it --rm -v "${PWD}:${PWD}" -w "${PWD}" ghcr.io/sethvargo/ratchet:0.6.0 pin $FILE
done
