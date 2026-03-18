FROM python:3.12.1

RUN apt-get update \
    && apt-get install -y openssh-server ssh jq iputils-ping telnet iproute2 sudo\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Sky Store
WORKDIR /skystore
COPY . .
RUN /skystore/docker/build/base/build_skystore.sh


