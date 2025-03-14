FROM ubuntu:22.04

EXPOSE 2025

# install requirements
RUN apt-get -y update
RUN apt-get -y install git cmake python3 pip
RUN pip install --upgrade pip
RUN pip install scikit-learn numpy

WORKDIR /root
RUN echo "ulimit -s unlimited" >> /root/.bashrc
RUN git clone
ARG BASE_DIR=/root/rsfuzz
ARG SOURCE_DIR=/root/rsfuzz/
