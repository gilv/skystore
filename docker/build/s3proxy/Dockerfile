FROM skystore-base:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV SSH_USERNAME=extract
ENV SSH_PORT=22
ENV PASSWORD=mysecretpassword
ENV SKYSTORE_SRV_ADDR="" 
ENV SKYSTORE_PRV_KEY=""
ENV SKYSTORE_S3P_CFG=""
ENV S3_CFG=""
ENV SKY_ACCESS_KEY_ID=""
ENV SKY_SECRET_ACCESS_KEY=""

# Install support software and clean up
RUN apt-get update \
    && apt-get install -y ssh jq iputils-ping telnet iproute2\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Copy the script to execute the service
COPY run_skystore_s3proxy.sh /skystore
RUN chmod +x /skystore/run_skystore_s3proxy.sh

# S3 service port
EXPOSE 8002

# Start SSH tunnel + SkyStore s3-proxy
CMD ["/skystore/run_skystore_s3proxy.sh"]
