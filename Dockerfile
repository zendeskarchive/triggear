FROM python:3.6.3-alpine

MAINTAINER Karol Gil <karol.gil@getbase.com>

ENV APP=/usr/src/triggear
RUN mkdir -p $APP
WORKDIR $APP

COPY requirements.txt $APP
RUN pip install -r requirements.txt
COPY . $APP

ENV PYTHONPATH=$APP

ENV CREDS_PATH=$APP/configs/creds.yml
ENV CONFIG_PATH=$APP/config.yml

RUN PYTHONPATH=$APP pytest --cov-report=html --cov=app --junit-xml=report.xml .