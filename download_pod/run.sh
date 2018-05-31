#!/bin/bash

URL="http://artifacts/builds/bitbucket:scality:ring:dev-staging-8.0.0.0.r180523081704.a66e0ba.pre-merge.00000723/repo/centos6/scality/thirdparty/grafana-4.3.2-1.x86_64.rpm"


while true; do
    curl -vvv $URL > grafana.rpm
    if [ $? != 0 ]; then
	echo 'FAILURE'
    fi
done
