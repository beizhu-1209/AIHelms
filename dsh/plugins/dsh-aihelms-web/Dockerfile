FROM python:3.11-slim

ARG NODE_VERSION=24.19.0
ARG TARGETARCH=amd64

WORKDIR /opt/dsh
COPY . /opt/dsh
ENV PATH=/opt/dsh/node_modules/.bin:/usr/local/bin:$PATH
ENV HOME=/home/dsh
ENV DSH_HOME=/opt/dsh/deploy/aihelms/dsh-home
ENV CHOKIDAR_USEPOLLING=true

RUN sed -i \
        -e 's|deb.debian.org|mirrors.aliyun.com|g' \
        -e 's|security.debian.org|mirrors.aliyun.com/debian-security|g' \
        /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl git ripgrep xz-utils \
    && case "$TARGETARCH" in amd64) NODE_ARCH=x64 ;; arm64) NODE_ARCH=arm64 ;; *) echo "Unsupported architecture: $TARGETARCH"; exit 1 ;; esac \
    && curl -fsSL "https://mirrors.aliyun.com/nodejs-release/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${NODE_ARCH}.tar.xz" -o /tmp/node.tar.xz \
    && tar -xJf /tmp/node.tar.xz --strip-components=1 -C /usr/local \
    && node --version \
    && rm -f /tmp/node.tar.xz \
    && apt-get purge -y --auto-remove xz-utils \
    && rm -rf /var/lib/apt/lists/*

# The profile must reference the package inside the image, never a build-host path.
RUN test -f "$DSH_HOME/profiles/web/dsh-aihelms-web.tgz" \
    && grep -Fq '"dsh-aihelms-web": "file:dsh-aihelms-web.tgz"' "$DSH_HOME/profiles/web/package.json" \
    && node --import tsx/esm apps/cli/src/bin.ts --profile web --dump-config \
        | grep -q 'patched by dsh-aihelms-web'

RUN useradd --create-home --uid 1000 --shell /bin/sh dsh \
    && chown -R dsh:dsh /opt/dsh /home/dsh

USER 1000:1000
EXPOSE 3080
CMD ["node", "--import", "tsx/esm", "apps/cli/src/bin.ts", "web", "--no-open"]
