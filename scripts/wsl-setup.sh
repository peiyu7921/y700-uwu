#!/bin/bash
# Install the AOSP/uwuAOSP 17 build dependencies inside the WSL2 Ubuntu distro.
#
#   wsl.exe -d Ubuntu-24.04 -u root bash /mnt/d/projects/y700-uwu/scripts/wsl-setup.sh
#
# JDK 21 comes from the debs under docker/jdk/ because this network reliably drops the
# 45/79 MB openjdk debs from every mirror.
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive

echo "== switching apt to Aliyun mirror =="
sed -i \
    -e 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' \
    -e 's|http://security.ubuntu.com/ubuntu/|http://mirrors.aliyun.com/ubuntu/|g' \
    /etc/apt/sources.list.d/ubuntu.sources

printf 'Acquire::Retries "10";\nAcquire::http::Timeout "60";\n' \
    > /etc/apt/apt.conf.d/99retries

apt-get update

echo "== installing build dependencies =="
apt-get install -y --no-install-recommends \
    bc bison build-essential ca-certificates ccache curl file flex \
    g++-multilib gcc-multilib git git-lfs gnupg gperf imagemagick \
    lib32readline-dev lib32z1-dev libelf-dev liblz4-tool libsdl1.2-dev \
    libssl-dev libxml2 libxml2-utils lzop pngcrush python3 python-is-python3 \
    repo rsync schedtool squashfs-tools unzip xsltproc zip zlib1g-dev

echo "== installing JDK 21 from local debs =="
dpkg -i /mnt/d/projects/y700-uwu/docker/jdk/*.deb || true
apt-get -f install -y --no-install-recommends

echo "== versions =="
java -version 2>&1 | head -2
python3 --version
git --version
echo "== setup done =="
