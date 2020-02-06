#!/bin/bash

# make lua libs available
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# get container ipv4
ipv4=$(host ${AWS_BUCKET_PREFIX}-staging.storage.googleapis.com | grep 'has address' | cut -d\  -f4)

# define supported charset
supported_charset='\/0-9a-zA-Z_ ,:@=\\-\\.\\+\\~\\(\\)\;\&'

# generate mime types map file
mimetypes_raw=$(tr -d '\r\n' < /etc/nginx/mime.types | sed -E 's/^[^\{]*\{(.*)\}[^\{]*$/\1/' | sed -E 's/\s+/ /g' | sed -E 's/;\s/;/g' | sed -E 's/^\s//')
IFS=';'
read -ra MIMETYPES <<< "$mimetypes_raw"
IFS=' '
echo "map \$file_extension \$file_mime_type {" > /etc/nginx/mimetypes.map
echo "default application/binary;" >> /etc/nginx/mimetypes.map
for i in "${MIMETYPES[@]}"
do
    read -ra MIMETYPE <<< "$i"
    for j in "${MIMETYPE[@]:1}"
    do
        echo "."$j" "${MIMETYPE[0]}";" >> /etc/nginx/mimetypes.map
    done
done
echo "}" >> /etc/nginx/mimetypes.map

# generate xslt file (by default, set it up for Google Cloud Storage use)
# For Google Cloud Storage: http://doc.s3.amazonaws.com/2006-03-01
# For CLoud Server: http://s3.amazonaws.com/doc/2006-03-01/
sed -e "s|__AWS_XML_NS__|${AWS_XML_NS:=http://doc.s3.amazonaws.com/2006-03-01}|g" \
    /etc/nginx/browse.raw.xslt.template > /etc/nginx/browse.raw.xslt

# generate nginx configuration
sed -e "s|\${AWS_BUCKET_PREFIX}|${AWS_BUCKET_PREFIX}|g" \
    -e "s|__S3_ENDPOINT__|${ipv4}|g" \
    -e "s|__SUPPORTED_CHARSET__|${supported_charset}|g" \
    /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# launch nginx
exec /usr/local/sbin/nginx -g "daemon off;"
