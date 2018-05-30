#!/bin/bash

URL='http://artifacts/builds/bitbucket%3Ascality%3Aring%3Adev-staging-8.0.0.0.r180517072727.323d6b3.pre-merge.00000691/installer/'

#wget -r $URL
#tar -chvzf artifacts.tar.gz artifacts


dd if=/dev/urandom of=big bs=1M count=1024
dd if=/dev/urandom of=big-2 bs=1M count=1024

tar -chvzf artifacts.tar.gz big big-2
while true; do
    curl -X PUT -vvv -s -T artifacts.tar.gz http://artifacts/upload/test-thomas
    if [ $? != 0 ]; then
	echo "FAILURE"
    fi
done
