FROM python:3.8

VOLUME /home/workspace

WORKDIR /home/workspace

COPY requirements.txt /app/

RUN pip install -r /app/requirements.txt

CMD ["pytest"]
