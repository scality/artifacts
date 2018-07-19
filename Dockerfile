FROM python:3.6-slim

EXPOSE 50000

RUN pip install --upgrade pip

COPY requirements.txt /tmp/requirements.txt

RUN pip install -r /tmp/requirements.txt

COPY ./artifacts /app

WORKDIR /app

CMD ["python", "main.py"]
