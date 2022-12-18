# pull official base image
# FROM python:3.9.5-slim-buster
# FROM python:3.9.5-alpine
FROM python:3.9.5


# RUN apk update
# RUN apk add --no-cache gcc
# RUN apk add git


# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .
