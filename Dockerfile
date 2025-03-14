FROM ubuntu:22.04

EXPOSE 2025

# install requirements
RUN apt-get -y update
RUN apt-get -y install git cmake python3 pip bison
RUN pip install --upgrade pip
RUN pip install scikit-learn numpy

WORKDIR /root
RUN echo "ulimit -s unlimited" >> /root/.bashrc
RUN git clone https://github.com/anonymrsfuzz/rsfuzz.git

WORKDIR /root/rsfuzz

RUN bash build-benchmarks.sh


