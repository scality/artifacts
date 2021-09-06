#!/bin/bash

mkdir -p /data/nginx/artifacts_github_auth_cache
chmod 755 /data/nginx/artifacts_github_auth_cache
chown -R nobody /data/nginx/artifacts_github_auth_cache

while true
do
  find /data/nginx/artifacts_github_auth_cache -type f -mmin -60 -delete
  sleep 60
done
