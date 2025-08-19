#！ bash
  # 1. 更新系统并安装必要工具
  sudo yum update -y
  sudo yum install -y yum-utils device-mapper-persistent-data lvm2 curl wget

  # 2. 添加Docker官方仓库
  sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

  # 3. 安装Docker
  sudo yum install -y docker-ce docker-ce-cli containerd.io

  # 4. 启动Docker服务
  sudo systemctl start docker
  sudo systemctl enable docker

  # 5. 将当前用户添加到docker组（这样不需要每次都用sudo）
  sudo usermod -aG docker $USER

  # 6. 安装Docker Compose
  sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose

  # 7. 创建软链接
  sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

  # 安装完成后验证：

  # 验证Docker安装
  docker --version
  docker-compose --version

  # 测试Docker是否工作
  sudo docker run hello-world

#   重要提醒：
#   - 安装完成后，请重新登录SSH或运行 newgrp docker 使docker用户组生效
#   - 如果网络较慢，Docker镜像下载可能需要一些时间

#   安装完成后，再次运行TalkAI部署脚本：

  sudo ./deployment/deploy-existing-server.sh --config deployment/quick-deploy-config.sh