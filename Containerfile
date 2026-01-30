# Use the official bootable RHEL image
FROM registry.redhat.io/rhel9/rhel-bootc:latest

# 1. Enforce FIPS mode for FSI compliance
RUN fips-mode-setup --enable

# 2. Install Mandatory Security Tooling
RUN dnf -y install \
    openscap-scanner \
    scap-security-guide \
    crypto-policies-scripts \
    && dnf clean all

# 3. Lockdown SSH (No root login, no empty passwords)
RUN sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/PermitEmptyPasswords yes/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# 4. Set Crypto Policy to FIPS-compliant levels
RUN update-crypto-policies --set FIPS