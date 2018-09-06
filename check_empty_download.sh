#!/bin/bash
full_url=$1

rm -fr download
mkdir download
cd download
status=$(wget -q -S -O data.empty $full_url 2>&1 | head -1 | sed -e 's/^ *//' | cut -d\  -f2)

echo $status

if [ -n "$status" ] && [ $status -eq 200 ] && [ -f data.empty ] && [ ! -s data.empty ]
then
  exit 0
fi

exit 1
