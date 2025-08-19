#!/bin/bash
# TalkAI 快速部署配置文件
# 请根据你的实际情况修改以下配置

# =================================
#           基础配置
# =================================

# 子域名配置 (基于你的域名 jimingge.net)
export DOMAIN="api.jimingge.net"

# 项目部署目录 (与你的网站目录同级)
export PROJECT_DIR="/www/wwwroot/talkai_miniprogram"

# =================================
#          API密钥配置
# =================================

# Moonshot AI API密钥 (推荐)
export MOONSHOT_API_KEY="sk-yryK7utQieu5e7rys1aJK9ulVy1aTeGGabuVILOneeqN0AQb"

# 或者使用OpenAI API密钥
# export OPENAI_API_KEY="sk-your-openai-api-key-here"

# =================================
#        微信小程序配置
# =================================

# 微信小程序AppID
export WECHAT_APP_ID="wxb45f0d5fa6530db4"

# 微信小程序AppSecret
export WECHAT_APP_SECRET="d4c8f6491a2ab0d80997f5b0f88101a7"

# =================================
#         SSL证书配置
# =================================
# 查找到的实际路径：
export SSL_CERT_PATH="/www/server/panel/vhost/ssl/jimingge.net/fullchain.pem"
export SSL_KEY_PATH="/www/server/panel/vhost/ssl/jimingge.net/privkey.pem"

# SSL证书路径 (基于你的域名 jimingge.net)
# export SSL_CERT_PATH="/etc/letsencrypt/live/jimingge.net/fullchain.pem"
# export SSL_KEY_PATH="/etc/letsencrypt/live/jimingge.net/privkey.pem"

# 如果你使用通配符证书，可能路径如下
# export SSL_CERT_PATH="/etc/letsencrypt/live/*.jimingge.net/fullchain.pem"
# export SSL_KEY_PATH="/etc/letsencrypt/live/*.jimingge.net/privkey.pem"

# =================================
#         词典数据库配置
# =================================

# 词典数据库路径
# /www/wwwroot/talkai_miniprogram/backend/data/db/dictionary400k.db
export DICT_DB_PATH="/www/wwwroot/talkai_miniprogram/backend/data/db/dictionary400k.db"

# 常见位置 (取消注释你的实际路径)
# export DICT_DB_PATH="/home/ubuntu/dictionary400k.db"
# export DICT_DB_PATH="/opt/dictionary400k.db"
# export DICT_DB_PATH="../dictionary400k.db"

# =================================
#          高级配置
# =================================

# Nginx配置目录 (通常无需修改)
export NGINX_AVAILABLE="/etc/nginx/sites-available"
export NGINX_ENABLED="/etc/nginx/sites-enabled"

# Docker端口配置 (避免与现有服务冲突)
export NGINX_PORT="8001"
export REDIS_PORT="6380"

# 数据库配置
export DATABASE_URL="sqlite:///./data/db/talkai.db"
export REDIS_URL="redis://talkai-redis:6379/0"

# =================================
#       一键部署使用示例
# =================================
# 
# 1. 编辑此配置文件，填入你的实际信息
# 2. 上传整个项目到服务器
# 3. 运行以下命令：
#
#    chmod +x deployment/deploy-existing-server.sh
#    sudo ./deployment/deploy-existing-server.sh --config deployment/quick-deploy-config.sh
#
# 或者使用交互式配置：
#    sudo ./deployment/deploy-existing-server.sh --interactive
#