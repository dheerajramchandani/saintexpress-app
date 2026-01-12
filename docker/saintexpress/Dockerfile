# Use Ubuntu 20.04 as base image, compatible with SAINTexpress build
FROM ubuntu:20.04

# Set non-interactive for apt (no prompts)
ENV DEBIAN_FRONTEND=noninteractive

# Install build tools, GSL, R, Python 2.7, wget, unzip
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    make \
    # libgsl0 \
    r-base \
    python2.7 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Create build directory
WORKDIR /tmp/build

# Download and extract SAINTexpress source
RUN wget -O saintexpress.zip "https://sourceforge.net/projects/saint-apms/files/SAINTexpress_v3.6.1__2015-05-03.zip/download" \
    && unzip saintexpress.zip \
    && cd SAINTexpress_v3.6.1__2015-05-03 \
    && make all

# Install SAINTexpress binary to /usr/local/bin
RUN cp SAINTexpress_v3.6.1__2015-05-03/bin/SAINTexpress* /usr/local/bin/

# Cleanup build files
RUN rm -rf /tmp/build

# Set working directory to /work (where job files live)
WORKDIR /work

# Set entrypoint to SAINTexpress binary
ENTRYPOINT ["/usr/local/bin/SAINTexpress-spc"]
