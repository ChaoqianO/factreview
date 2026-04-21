#!/bin/bash
echo "正在配置 Docker 镜像源..."
# Backup existing config
if [ -f /etc/docker/daemon.json ]; then
    cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
    echo "已备份原配置到 /etc/docker/daemon.json.bak"
fi

# Write new config with currently known working mirrors
# 注意：国内镜像源情况多变，以下列表包含了几个目前较为通用的加速源
sudo cat > /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://huecker.io",
    "https://dockerhub.timeweb.cloud",
    "https://noohub.ru"
  ],
  "insecure-registries": [],
  "debug": false,
  "experimental": false
}
EOF

echo "正在重启 Docker 服务..."
sudo systemctl daemon-reload
sudo systemctl restart docker
echo "✅ Docker 配置更新完成！"
echo "请重试运行 docker run 命令。"
