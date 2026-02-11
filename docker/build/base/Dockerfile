FROM python:3.12.1

RUN apt-get update \
    && apt-get install -y openssh-server ssh jq iputils-ping telnet iproute2 sudo\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Sky Store
WORKDIR /skystore
COPY install_skystore.sh .
RUN chmod +x /skystore/install_skystore.sh
RUN /skystore/install_skystore.sh


