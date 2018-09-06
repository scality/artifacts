#!/bin/bash
full_url=$1

rm -fr download
mkdir download
cd download
status=$(wget -q -S -O data.chunk_size $full_url 2>&1 | head -1 | sed -e 's/^ *//' | cut -d\  -f2)

echo $status

if [ -z "$status" ] || [ $status -ne 200 ]
then
    exit 1
fi

if [ $(wc -c < data.chunk_size) -ne 8192 ]
then
    exit 1
fi

cat ../chunk_size/data.sha1 | sed -e "s/data/data.chunk_size/" > data.sha1
sha1sum -c data.sha1
