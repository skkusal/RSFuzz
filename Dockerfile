FROM ubuntu:22.04

EXPOSE 2025

# install requirements
RUN apt-get -y update && apt-get -y upgrade
RUN apt-get -y install git cmake python3 pip bison wget openjdk-17-jdk
RUN pip install --upgrade pip
RUN pip install scikit-learn numpy exrex

RUN echo "ulimit -s unlimited" >> /root/.bashrc

# Clone rsfuzz repository
WORKDIR /root/
RUN git clone https://github.com/anonymrsfuzz/rsfuzz.git
WORKDIR /root/rsfuzz

RUN bash build-benchmarks.sh