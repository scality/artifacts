FROM ubuntu:xenial

# Expose port
EXPOSE 80

# Declare volume where cache objects and request bodies will be stored
VOLUME ["/data/nginx"]

# Download and install requirements for entrypoint scripts and nginx compilation
RUN apt-get update && \
    apt-get install --no-install-recommends --no-upgrade --assume-yes curl ca-certificates dnsutils wget gcc make libpcre3-dev libssl-dev libxml2-dev libxslt1-dev zlib1g-dev

# Define components versions
ENV LUA_RESTY_CORE 0.1.17
ENV LUA_RESTY_LRUCACHE 0.09
ENV LUAJIT2_VERSION 2.1-20190626
ENV NGX_DEVEL_KIT_VERSION 0.3.1
ENV LUA_NGINX_MODULE_VERSION 0.10.15
ENV SET_MISC_NGINX_MODULE 0.32
ENV NGINX_VERSION 1.16.1

WORKDIR /tmp

# Download build and install lua-resty-core
RUN wget https://github.com/openresty/lua-resty-core/archive/v${LUA_RESTY_CORE}.tar.gz -O lua-resty-core.tar.gz && \
    mkdir lua-resty-core && \
    tar zxf lua-resty-core.tar.gz  -C lua-resty-core --strip-components=1
RUN make install -C lua-resty-core

# Download build and install lua-resty-lrucache
RUN wget https://github.com/openresty/lua-resty-lrucache/archive/v${LUA_RESTY_LRUCACHE}.tar.gz -O lua-resty-lrucache.tar.gz && \
    mkdir lua-resty-lrucache && \
    tar zxf lua-resty-lrucache.tar.gz -C lua-resty-lrucache --strip-components=1
RUN make install -C lua-resty-lrucache

# Download build and install LuaJIT
RUN wget https://github.com/openresty/luajit2/archive/v${LUAJIT2_VERSION}.tar.gz -O luajit2.tar.gz && \
    mkdir luajit2 && \
    tar zxf luajit2.tar.gz  -C luajit2 --strip-components=1
RUN make -C luajit2
RUN make install -C luajit2

# Tell system where to find LuaJIT 2.1
ENV LUAJIT_LIB=/usr/local/lib
ENV LUAJIT_INC=/usr/local/include/luajit-2.1

# Download ngx_devel_kit
RUN wget https://github.com/simplresty/ngx_devel_kit/archive/v${NGX_DEVEL_KIT_VERSION}.tar.gz -O ngx_devel_kit.tar.gz && \
    mkdir ngx_devel_kit && \
    tar zxf ngx_devel_kit.tar.gz -C ngx_devel_kit --strip-components=1

# Download lua-nginx-module
RUN wget https://github.com/openresty/lua-nginx-module/archive/v${LUA_NGINX_MODULE_VERSION}.tar.gz -O lua-nginx-module.tar.gz && \
    mkdir lua-nginx-module && \
    tar zxf lua-nginx-module.tar.gz -C lua-nginx-module --strip-components=1

# Download set-misc-nginx-module
RUN wget https://github.com/openresty/set-misc-nginx-module/archive/v${SET_MISC_NGINX_MODULE}.tar.gz -O set-misc-nginx-module.tar.gz && \
    mkdir set-misc-nginx-module && \
    tar zxf set-misc-nginx-module.tar.gz -C set-misc-nginx-module --strip-components=1

# Download nginx
RUN wget http://nginx.org/download/nginx-${NGINX_VERSION}.tar.gz -O nginx.tar.gz && \
    mkdir nginx && \
    tar zxf nginx.tar.gz -C nginx --strip-components=1

WORKDIR /tmp/nginx

# Build and install nginx
RUN ./configure --sbin-path=/usr/local/sbin \
                --conf-path=/etc/nginx/nginx.conf \
                --pid-path=/var/run/nginx.pid \
                --error-log-path=/dev/stderr \
                --http-log-path=/dev/stdout \
                --with-http_ssl_module \
                --with-http_xslt_module \
                --add-module=/tmp/ngx_devel_kit \
                --add-module=/tmp/lua-nginx-module \
                --add-module=/tmp/set-misc-nginx-module
RUN make
RUN make install

# Install start scripts
COPY full_listing_cache_update.sh /full_listing_cache_update.sh
COPY start.sh /start.sh

# Install HTML browse includes
COPY include/browse_header.html /etc/nginx/browse_header.html
COPY include/browse_footer.html /etc/nginx/browse_footer.html

# Install and optimize lua scripts
COPY lua/canonicalize_path.lua /etc/nginx/canonicalize_path.lua
COPY lua/compute_aws_s3_signature.lua /etc/nginx/compute_aws_s3_signature.lua
COPY lua/find_build.lua /etc/nginx/find_build.lua
COPY lua/copy_build.lua /etc/nginx/copy_build.lua
COPY lua/browse.lua /etc/nginx/browse.lua

RUN /usr/local/bin/luajit -b /etc/nginx/canonicalize_path.lua /etc/nginx/canonicalize_path.ljbc
RUN /usr/local/bin/luajit -b /etc/nginx/compute_aws_s3_signature.lua /etc/nginx/compute_aws_s3_signature.ljbc
RUN /usr/local/bin/luajit -b /etc/nginx/find_build.lua /etc/nginx/find_build.ljbc
RUN /usr/local/bin/luajit -b /etc/nginx/copy_build.lua /etc/nginx/copy_build.ljbc
RUN /usr/local/bin/luajit -b /etc/nginx/browse.lua /etc/nginx/browse.ljbc

# Install xslt filter
COPY xslt/browse.raw.xslt.template /etc/nginx/browse.raw.xslt.template

# Install nginx configurations file
COPY conf/nginx.conf.template /etc/nginx/nginx.conf.template

# Launch nginx
CMD ["/start.sh"]
