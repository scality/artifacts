FROM tiangolo/uwsgi-nginx-flask:flask

RUN pip install awscli, requests, flask, moto[server]

COPY ./app /app
COPY upload_1g.conf /etc/nginx/conf.d/
