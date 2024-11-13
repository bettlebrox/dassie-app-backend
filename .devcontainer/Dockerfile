FROM mcr.microsoft.com/vscode/devcontainers/base:ubuntu

# use this Dockerfile to install additional tools you might need, e.g.
# RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
#     && apt-get -y install --no-install-recommends <your-package-list-here>
RUN git config --global user.email "474346+bettlebrox@users.noreply.github.com"
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends python3-pip \
RUN curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb" \
    && dpkg -i session-manager-plugin.deb \
    && rm session-manager-plugin.deb


