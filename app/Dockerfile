FROM python:3.9-slim-bullseye

RUN apt-get -y update
RUN apt-get install -y ffmpeg git

WORKDIR usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
