FROM tiangolo/uwsgi-nginx-flask:python3.6

RUN pip install --upgrade pip
RUN pip install awscli requests uwsgitop

COPY ./artifacts /app

RUN mkdir -p /data/nginx
RUN cp /app/cache.conf /etc/nginx/conf.d/cache.conf
RUN cp /app/nginx.conf /etc/nginx/conf.d/nginx.conf
RUN cp /app/uwsgi.ini /etc/uwsgi/uwsgi.ini
RUN cat /app/cache_settings.conf >> /etc/nginx/uwsgi_params

ENV NGINX_WORKER_PROCESSES 1
ENV NGINX_MAX_UPLOAD 8g
