# Use the official bootable RHEL image
FROM registry.redhat.io/rhel9/rhel-bootc:latest

# Create the directory for bootc configuration drop-ins
RUN mkdir -p /usr/lib/bootc/configs/

# Copy your TOML blueprint into the image
COPY fsi-server.toml /usr/lib/bootc/configs/fsi-server.toml

# Install Mandatory Security Tooling
RUN dnf -y install \
    openscap-scanner \
    scap-security-guide \
    crypto-policies-scripts \
    && dnf clean all

# Lockdown SSH (No root login, no empty passwords)
RUN sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/PermitEmptyPasswords yes/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# Set Crypto Policy to FIPS-compliant levels
RUN update-crypto-policies --set FIPS