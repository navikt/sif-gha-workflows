#!/bin/bash

FILES=$(find .github -type f -name "*.yml")

for FILE in $FILES; do
    docker run -it --rm -v "${PWD}:${PWD}" -w "${PWD}" ghcr.io/sethvargo/ratchet:0.10.2 pin $FILE

    #Med github token
    #docker run -it --rm -e GITHUB_TOKEN="${GITHUB_TOKEN}" -v "${PWD}:${PWD}" -w "${PWD}" ghcr.io/sethvargo/ratchet:0.10.2 pin $FILE
done
