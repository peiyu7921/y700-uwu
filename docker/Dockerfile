# Build environment for uwuAOSP 17 (Android 17).
# Usage:
#   docker build -t aosp-builder:17 docker/
#   docker run --rm -it -v /d/projects/y700-uwu:/src -w /src aosp-builder:17
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Aliyun mirror plus explicit retries: on this network the Tsinghua mirror keeps
# dropping the large packages (openjdk-21, libllvm20), which aborts the whole layer.
RUN sed -i \
        -e 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' \
        -e 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' \
        -e 's|http://ports.ubuntu.com/ubuntu-ports/|http://mirrors.aliyun.com/ubuntu-ports/|g' \
        /etc/apt/sources.list.d/ubuntu.sources && \
    printf 'Acquire::Retries "10";\nAcquire::http::Timeout "60";\nAcquire::https::Timeout "60";\n' \
        > /etc/apt/apt.conf.d/99retries && \
    apt-get update

RUN apt-get install -y --no-install-recommends \
        bc \
        bison \
        build-essential \
        ca-certificates \
        ccache \
        curl \
        file \
        flex \
        g++-multilib \
        gcc-multilib \
        git \
        git-lfs \
        gnupg \
        gperf \
        imagemagick \
        lib32readline-dev \
        lib32z1-dev \
        libelf-dev \
        liblz4-tool \
        libsdl1.2-dev \
        libssl-dev \
        libxml2 \
        libxml2-utils \
        lzop \
        pngcrush \
        python3 \
        python-is-python3 \
        repo \
        rsync \
        schedtool \
        squashfs-tools \
        xsltproc \
        zip \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# JDK 21 is installed from debs fetched on the host: this network reliably drops the
# 45/79 MB openjdk debs from every mirror, which aborts the whole layer.
COPY jdk/ /tmp/jdk/
# dpkg -i, not apt install: apt re-resolves openjdk from the mirror and drops the same
# 46/79 MB debs that keep failing on this network.
RUN dpkg -i /tmp/jdk/*.deb || true; \
    apt-get update && \
    apt-get -f install -y --no-install-recommends && \
    rm -rf /tmp/jdk /var/lib/apt/lists/* && \
    java -version

# AOSP's toolchain wants a predictable git identity and a large post buffer for
# big fetches over a proxy.
RUN git config --global user.name "elden builder" && \
    git config --global user.email "builder@localhost" && \
    git config --global http.postBuffer 524288000 && \
    git config --global http.lowSpeedLimit 1000 && \
    git config --global http.lowSpeedTime 120

WORKDIR /src
