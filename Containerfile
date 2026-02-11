FROM quay.io/centos-bootc/centos-bootc:stream9

# 1. Handle Kernel-level FIPS via bootc kargs
COPY 01-fips.toml /usr/lib/bootc/kargs.d/

# 2. Configure User-space Crypto Policy
RUN update-crypto-policies --no-reload --set FIPS

# 3. Install Security & Compliance Tooling
RUN dnf -y install \
    openscap-scanner \
    openscap-utils \
    scap-security-guide \
    && dnf clean all

# 4. FSI Hardening: Lockdown SSH
RUN sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# 5. Inject our User/Filesystem Blueprint
RUN mkdir -p /usr/lib/bootc/configs/
COPY fsi-server.toml /usr/lib/bootc/configs/fsi-server.toml