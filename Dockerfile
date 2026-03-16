FROM openresty/openresty:1.29.2.1-alpine-fat

# Expose port
EXPOSE 80

# Declare volume where github auth cache and listing cache will be stored
VOLUME ["/data/nginx"]

# Install runtime dependencies:
# - bash: required by start.sh (#!/bin/bash)
# - curl: used by stop.sh to poll nginx_status
# - bind-tools: provides 'host' command used by start.sh for DNS resolution
RUN apk add --no-cache bash curl bind-tools

# Create compatibility symlinks so start.sh/stop.sh work without modification:
# - /usr/local/sbin/nginx -> OpenResty nginx binary
# - /etc/nginx -> OpenResty conf dir (also makes mime.types available at /etc/nginx/mime.types)
RUN mkdir -p /usr/local/sbin && \
    ln -sf /usr/local/openresty/nginx/sbin/nginx /usr/local/sbin/nginx && \
    rm -rf /etc/nginx && \
    ln -sf /usr/local/openresty/nginx/conf /etc/nginx

# Install start scripts
COPY full_listing_cache_update.sh /full_listing_cache_update.sh
COPY github_auth_cache_cleaner.sh /github_auth_cache_cleaner.sh
COPY start.sh stop.sh /

# Install HTML browse includes
COPY include/browse_header.html /etc/nginx/browse_header.html
COPY include/browse_footer.html /etc/nginx/browse_footer.html

# Install and optimize lua scripts
COPY lua/canonicalize_path.lua /etc/nginx/canonicalize_path.lua
COPY lua/compute_aws_s3_signature.lua /etc/nginx/compute_aws_s3_signature.lua
COPY lua/find_build.lua /etc/nginx/find_build.lua
COPY lua/copy_build.lua /etc/nginx/copy_build.lua
COPY lua/version_object.lua /etc/nginx/version_object.lua
COPY lua/add_metadata.lua /etc/nginx/add_metadata.lua
COPY lua/search_metadata.lua /etc/nginx/search_metadata.lua
COPY lua/browse.lua /etc/nginx/browse.lua
COPY lua/github_access.lua /etc/nginx/github_access.lua

RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/canonicalize_path.lua /etc/nginx/canonicalize_path.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/compute_aws_s3_signature.lua /etc/nginx/compute_aws_s3_signature.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/find_build.lua /etc/nginx/find_build.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/copy_build.lua /etc/nginx/copy_build.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/version_object.lua /etc/nginx/version_object.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/add_metadata.lua /etc/nginx/add_metadata.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/search_metadata.lua /etc/nginx/search_metadata.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/browse.lua /etc/nginx/browse.ljbc
RUN /usr/local/openresty/luajit/bin/luajit -b /etc/nginx/github_access.lua /etc/nginx/github_access.ljbc

# Install xslt filter
COPY xslt/browse.raw.xslt.template /etc/nginx/browse.raw.xslt.template

# Install nginx configuration file
COPY conf/nginx.conf.template /etc/nginx/nginx.conf.template

# Launch nginx
CMD ["/start.sh"]
