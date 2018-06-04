#!/bin/bash

URL="http://artifacts/builds/bitbucket:scality:ring:promoted-7.4.0.0/repo/centos6/scality/thirdparty/grafana-4.3.2-1.x86_64.rpm"


while true; do
    curl --trace-ascii - --output /dev/null $URL
    if [ $? != 0 ]; then
        echo 'FAILURE'
    fi
done
