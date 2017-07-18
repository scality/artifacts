FROM tiangolo/uwsgi-nginx-flask:flask-python3.5-upload

RUN pip install awscli, requests, flask, moto[server]

COPY ./artifacts /app
COPY upload_1g.conf /etc/nginx/conf.d/
