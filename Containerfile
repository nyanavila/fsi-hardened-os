# Use the official RHEL 9 bootable image
FROM registry.redhat.io/rhel9/rhel-bootc:latest

# 1. Setup Blueprint Configuration
# We place the TOML in the specific directory bootc looks for
RUN mkdir -p /usr/lib/bootc/configs/
COPY fsi-server.toml /usr/lib/bootc/configs/fsi-server.toml

# 2. Install Mandatory Security & Audit Tooling
# NOTE: If your build fails here, ensure your GitLab Runner is 
# registered to Red Hat or has the subscription-manager plugin enabled.
RUN dnf -y install \
    openscap-scanner \
    scap-security-guide \
    crypto-policies-scripts \
    && dnf clean all

# 3. User Space Hardening
# This sets the libraries to FIPS mode without touching the bootloader
RUN update-crypto-policies --set FIPS

# 4. SSH Compliance Hardening
RUN sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/PermitEmptyPasswords yes/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# 5. Finalize: Ensure the image knows it is a RHEL system
RUN echo "FSI Hardened RHEL Image v1.0" > /etc/fsi-release