#!/bin/bash

mkdir -p /var/artifacts_full_listing_cache
chmod 755 /var/artifacts_full_listing_cache

while true
do
  tmp_file=$(mktemp -p /var/artifacts_full_listing_cache)
  chmod 644 ${tmp_file}
  date --utc > ${tmp_file}
  curl --silent --fail --max-time 300 http://127.0.0.1/refresh_full_listing/ >> ${tmp_file} 2> /dev/null && mv -f ${tmp_file} /var/artifacts_full_listing_cache/listing
  rm -f ${tmp_file}
  sleep 60
done
