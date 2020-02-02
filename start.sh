#!/bin/bash

# make lua libs available
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# get container ipv4
ipv4=$(host ${AWS_BUCKET_PREFIX}-staging.storage.googleapis.com | grep 'has address' | cut -d\  -f4)

# define supported charset
supported_charset='\/0-9a-zA-Z_ ,:@=\\-\\.\\+\\~\\(\\)\;\&'

# generate nginx configuration
sed -e "s/\${AWS_BUCKET_PREFIX}/${AWS_BUCKET_PREFIX}/g" \
    -e "s/__S3_ENDPOINT__/$ipv4/g" \
    -e "s/__SUPPORTED_CHARSET__/$supported_charset/g" \
    /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# launch nginx
exec /usr/local/sbin/nginx -g "daemon off;"
