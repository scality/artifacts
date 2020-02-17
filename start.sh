#!/bin/bash

# make lua libs available
export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Defaulting to google cloud storage S3 compatible endpoint
ENDPOINT_URL=${ENDPOINT_URL:=https://storage.googleapis.com}

# generate xslt file (by default, set it up for Google Cloud Storage use)
# For Google Cloud Storage: http://doc.s3.amazonaws.com/2006-03-01
# For CLoud Server: http://s3.amazonaws.com/doc/2006-03-01/
AWS_XML_NS=${AWS_XML_NS:=http://doc.s3.amazonaws.com/2006-03-01}

# Parsing and splitting up the S3 endpoint url
# Explicitly retrieved from https://stackoverflow.com/questions/6174220/parse-url-in-shell-script#6174447
#
S3_ENDPOINT_PROTO="$(echo $ENDPOINT_URL | sed -e's,^\(.*://\).*,\1,g')"
S3_ENDPOINT_URL="$(echo ${ENDPOINT_URL/$S3_ENDPOINT_PROTO/})"
S3_ENDPOINT_USER="$(echo $S3_ENDPOINT_URL | grep @ | cut -d@ -f1)"
S3_ENDPOINT_HOSTPORT="$(echo ${S3_ENDPOINT_URL/$S3_ENDPOINT_USER@/} | cut -d/ -f1)"
S3_ENDPOINT_HOST="$(echo $S3_ENDPOINT_HOSTPORT | sed -e 's,:.*,,g')"
S3_ENDPOINT_PORT="$(echo $S3_ENDPOINT_HOSTPORT | grep : | sed -e 's,^\(.*\):\([0-9]*\)\(.*\),\2,')"

# Retrieve S3 endpoint ip address
S3_ENDPOINT_IPV4=$(host $S3_ENDPOINT_HOST | grep 'has address' | cut -d\  -f4)

if [[  ${S3_ENDPOINT_IPV4} == "" ]]; then
    echo "ipv4 not found for ${ENDPOINT_URL}. Using S3 host instead..."
    S3_ENDPOINT_IPV4=${S3_ENDPOINT_HOST}
fi

# Ensure the S3_ENDPOINT_PORT is explicitly setup
if [[ ${S3_ENDPOINT_PORT} == "" ]]; then
    if [[ ${S3_ENDPOINT_PROTO} == "https://" ]]; then
        S3_ENDPOINT_PORT=443
    elif [[ ${S3_ENDPOINT_PROTO} == "http://" ]]; then
        S3_ENDPOINT_PORT=80
    fi
fi

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


# Debugging options
echo "ENDPOINT_URL: ${ENDPOINT_URL}"
echo "S3_ENDPOINT_URL: ${S3_ENDPOINT_URL}"
echo "S3_ENDPOINT_PROTO: ${S3_ENDPOINT_PROTO}"
echo "S3_ENDPOINT_HOST: ${S3_ENDPOINT_HOST}"
echo "S3_ENDPOINT_PORT: ${S3_ENDPOINT_PORT}"
echo "S3_ENDPOINT_IPV4: ${S3_ENDPOINT_IPV4}"
echo "AWS_XML_NS: ${AWS_XML_NS}"

sed -e "s|__AWS_XML_NS__|${AWS_XML_NS}|g" \
    /etc/nginx/browse.raw.xslt.template > /etc/nginx/browse.raw.xslt

# generate nginx configuration
sed -e "s|\${AWS_BUCKET_PREFIX}|${AWS_BUCKET_PREFIX}|g" \
    -e "s|__S3_ENDPOINT_IPV4__|${S3_ENDPOINT_IPV4}|g" \
    -e "s|__S3_ENDPOINT_URL__|${S3_ENDPOINT_URL}|g" \
    -e "s|__S3_ENDPOINT_PROTO__|${S3_ENDPOINT_PROTO}|g" \
    -e "s|__S3_ENDPOINT_USER__|${S3_ENDPOINT_USER}|g" \
    -e "s|__S3_ENDPOINT_HOST__|${S3_ENDPOINT_HOST}|g" \
    -e "s|__S3_ENDPOINT_PORT__|${S3_ENDPOINT_PORT}|g" \
    -e "s|__SUPPORTED_CHARSET__|$supported_charset|g" \
    /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Launch updater
/full_listing_cache_update.sh &

# launch nginx
exec /usr/local/sbin/nginx -g "daemon off;"
