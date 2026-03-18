FROM skystore-base:latest

# BEGIN installation of SSH service (secure front end for Sky Store)
# ------------------------------------------------------------------

# Set build argument for SSH port (can be overridden at build time)
ARG SSH_PORT=8222

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV SSH_USERNAME=extract
ENV PASSWORD=mysecretpassword
ENV SKYSTORE_PUB_KEY=""
ENV SUDO=1
ENV SSH_PORT=${SSH_PORT}

# Create the privilege separation directory and fix permissions
RUN mkdir -p /run/sshd \
    && chmod 755 /run/sshd

# Expose SSH port
EXPOSE ${SSH_PORT}

# Create the non-root user with the ability to set a password and authorized keys using environment variables
RUN useradd -ms /bin/bash $SSH_USERNAME

# Set up SSH configuration
RUN mkdir -p /home/$SSH_USERNAME/.ssh && chown $SSH_USERNAME:$SSH_USERNAME /home/$SSH_USERNAME/.ssh \
    && echo "PasswordAuthentication yes" >> /etc/ssh/sshd_config \
    && echo "PermitRootLogin no" >> /etc/ssh/sshd_config

# Copy the script to configure the user's password and authorized keys
COPY docker/build/server/configure-ssh-user.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/configure-ssh-user.sh

# -------------------------------
# END installation of SSH service

# Install Sky Store server script
COPY docker/build/server/run_skystore_server.sh /skystore
RUN chmod +x /skystore/run_skystore_server.sh

# Start Sky Store server + SSH server
CMD ["/skystore/run_skystore_server.sh"]
