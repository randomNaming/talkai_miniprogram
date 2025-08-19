#!/bin/bash

# TalkAI 现有服务器一键部署脚本
# 适用于已有网站和SSL证书的服务器
# 使用子域名方式部署，避免与现有服务冲突

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志文件
LOG_FILE="/tmp/talkai-deploy.log"
DEPLOY_TIME=$(date '+%Y%m%d_%H%M%S')

# 默认配置
DEFAULT_DOMAIN="api.jimingge.net"
DEFAULT_PROJECT_DIR="/www/wwwroot/talkai_miniprogram"
DEFAULT_NGINX_PORT="8001"
DEFAULT_REDIS_PORT="6380"

# 全局变量
DOMAIN=""
PROJECT_DIR=""
INTERACTIVE_MODE=false
AUTO_MODE=false
CHECK_ONLY=false
CONFIG_FILE=""

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a "$LOG_FILE"
}

# 显示横幅
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║                TalkAI 智能部署工具                    ║"
    echo "║            现有服务器一键部署解决方案                 ║"
    echo "║                                                      ║"
    echo "║  • 自动检测环境  • 智能端口分配  • 零冲突部署         ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 显示帮助信息
show_help() {
    echo "TalkAI 现有服务器部署工具"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --interactive, -i    交互式配置部署"
    echo "  --auto, -a          自动部署 (使用默认配置)"
    echo "  --check-only, -c    仅检查环境，不执行部署"
    echo "  --config FILE       使用指定配置文件"
    echo "  --status            显示服务状态"
    echo "  --info              显示详细信息"
    echo "  --help, -h          显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --interactive          # 交互式部署"
    echo "  $0 --auto                # 自动部署"
    echo "  $0 --config config.sh    # 使用配置文件"
    echo "  $0 --status              # 查看状态"
    echo ""
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interactive|-i)
                INTERACTIVE_MODE=true
                shift
                ;;
            --auto|-a)
                AUTO_MODE=true
                shift
                ;;
            --check-only|-c)
                CHECK_ONLY=true
                shift
                ;;
            --config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            --status)
                show_status
                exit 0
                ;;
            --info)
                show_info
                exit 0
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                error "未知选项: $1"
                ;;
        esac
    done
}

# 加载配置文件
load_config() {
    if [[ -n "$CONFIG_FILE" && -f "$CONFIG_FILE" ]]; then
        info "加载配置文件: $CONFIG_FILE"
        source "$CONFIG_FILE"
    fi
}

# 交互式配置
interactive_config() {
    echo -e "${PURPLE}=== 交互式配置 ===${NC}"
    
    # 域名配置
    read -p "请输入API子域名 (例如: api.jimingge.net): " input_domain
    DOMAIN=${input_domain:-$DEFAULT_DOMAIN}
    
    # 项目目录
    read -p "请输入项目部署目录 [$DEFAULT_PROJECT_DIR]: " input_dir
    PROJECT_DIR=${input_dir:-$DEFAULT_PROJECT_DIR}
    
    # API密钥配置
    echo ""
    echo "请配置API密钥 (必需其一):"
    read -p "Moonshot API Key (留空跳过): " MOONSHOT_API_KEY
    if [[ -z "$MOONSHOT_API_KEY" ]]; then
        read -p "OpenAI API Key: " OPENAI_API_KEY
        if [[ -z "$OPENAI_API_KEY" ]]; then
            error "必须提供至少一个AI API密钥"
        fi
    fi
    
    # 微信小程序配置
    echo ""
    echo "微信小程序配置:"
    read -p "WeChat App ID: " WECHAT_APP_ID
    read -p "WeChat App Secret: " WECHAT_APP_SECRET
    
    # SSL证书路径检测
    echo ""
    info "检测SSL证书..."
    detect_ssl_certificates
    
    # 词典数据库路径
    echo ""
    read -p "词典数据库路径 (dictionary400k.db): " DICT_DB_PATH
    
    # 确认配置
    echo ""
    echo -e "${CYAN}=== 配置确认 ===${NC}"
    echo "域名: $DOMAIN"
    echo "部署目录: $PROJECT_DIR"
    echo "AI API: $([ -n "$MOONSHOT_API_KEY" ] && echo "Moonshot" || echo "OpenAI")"
    echo "微信AppID: $WECHAT_APP_ID"
    echo ""
    read -p "确认配置正确? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "部署已取消"
    fi
}

# 自动检测SSL证书
detect_ssl_certificates() {
    local cert_paths=(
        "/etc/letsencrypt/live/${DOMAIN%.*.*}"
        "/etc/letsencrypt/live/$(echo $DOMAIN | sed 's/^[^.]*\.//')"
        "/etc/ssl/certs"
        "/etc/nginx/ssl"
    )
    
    for path in "${cert_paths[@]}"; do
        if [[ -d "$path" ]]; then
            SSL_CERT_PATH="$path/fullchain.pem"
            SSL_KEY_PATH="$path/privkey.pem"
            if [[ -f "$SSL_CERT_PATH" && -f "$SSL_KEY_PATH" ]]; then
                success "检测到SSL证书: $path"
                return 0
            fi
        fi
    done
    
    warn "未检测到SSL证书，需要手动配置"
    read -p "SSL证书路径 (fullchain.pem): " SSL_CERT_PATH
    read -p "SSL私钥路径 (privkey.pem): " SSL_KEY_PATH
}

# 环境检查
check_environment() {
    info "检查系统环境..."
    
    # 检查root权限
    if [[ $EUID -ne 0 ]]; then
        error "请使用sudo运行此脚本"
    fi
    
    # 检查操作系统
    if ! command -v apt-get &> /dev/null && ! command -v yum &> /dev/null; then
        error "不支持的操作系统，仅支持Ubuntu/CentOS"
    fi
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        error "Docker未安装，请先安装Docker"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose未安装，请先安装Docker Compose"
    fi
    
    # 检查Nginx
    if ! command -v nginx &> /dev/null; then
        error "Nginx未安装，请先安装Nginx"
    fi
    
    if ! systemctl is-active --quiet nginx; then
        error "Nginx服务未运行，请启动Nginx"
    fi
    
    # 检查端口占用
    check_port_availability "$DEFAULT_NGINX_PORT" "TalkAI后端"
    check_port_availability "$DEFAULT_REDIS_PORT" "TalkAI Redis"
    
    # 检查磁盘空间
    local available_space=$(df / | tail -1 | awk '{print $4}')
    if [[ $available_space -lt 5242880 ]]; then # 5GB in KB
        warn "磁盘可用空间不足5GB，建议清理磁盘空间"
    fi
    
    # 检查内存
    local available_memory=$(free -m | awk 'NR==2{printf "%s", $7}')
    if [[ $available_memory -lt 1024 ]]; then
        warn "可用内存不足1GB，可能影响性能"
    fi
    
    success "环境检查通过"
}

# 检查端口可用性
check_port_availability() {
    local port=$1
    local service_name=$2
    
    if netstat -tlnp | grep -q ":$port "; then
        error "端口 $port 已被占用，无法启动 $service_name"
    fi
}

# 智能安装依赖
install_dependencies() {
    info "安装必要依赖..."
    
    # 更新包管理器
    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y curl wget git net-tools
    elif command -v yum &> /dev/null; then
        yum update -y -q
        yum install -y curl wget git net-tools
    fi
    
    # 安装其他工具
    if ! command -v htop &> /dev/null; then
        info "安装系统监控工具..."
        apt-get install -y htop 2>/dev/null || yum install -y htop 2>/dev/null || true
    fi
}

# 创建项目目录
setup_project_directory() {
    info "设置项目目录..."
    
    if [[ -d "$PROJECT_DIR" ]]; then
        warn "项目目录已存在: $PROJECT_DIR"
        if [[ "$AUTO_MODE" != true ]]; then
            read -p "是否继续? 这将覆盖现有配置 (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                error "部署已取消"
            fi
        else
            warn "自动模式：继续使用现有目录"
        fi
    fi
    
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    
    # 如果当前目录不是项目目录，复制文件
    local script_dir=$(dirname "$(dirname "$(readlink -f "$0")")")
    if [[ "$script_dir" != "$PROJECT_DIR" ]]; then
        info "从 $script_dir 复制项目文件..."
        cp -r "$script_dir"/* "$PROJECT_DIR"/ 2>/dev/null || true
    else
        info "已在项目目录中，跳过文件复制"
    fi
}

# 配置环境变量
setup_environment() {
    info "配置环境变量..."
    
    local env_file="$PROJECT_DIR/backend/.env"
    
    # 生成安全密钥
    local secret_key=$(openssl rand -hex 16)
    
    cat > "$env_file" << EOF
# TalkAI 环境配置文件
# 自动生成于: $(date)

# 数据库配置
DATABASE_URL=sqlite:///./data/db/talkai.db

# Redis配置
REDIS_URL=redis://talkai-redis:6379/0

# AI API配置
EOF

    if [[ -n "$MOONSHOT_API_KEY" ]]; then
        echo "MOONSHOT_API_KEY=$MOONSHOT_API_KEY" >> "$env_file"
    fi
    
    if [[ -n "$OPENAI_API_KEY" ]]; then
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> "$env_file"
    fi

    cat >> "$env_file" << EOF

# 微信小程序配置
WECHAT_APP_ID=$WECHAT_APP_ID
WECHAT_APP_SECRET=$WECHAT_APP_SECRET

# 安全配置
SECRET_KEY=$secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用配置
MODEL_PROVIDER=$([ -n "$MOONSHOT_API_KEY" ] && echo "moonshot" || echo "openai")
DEBUG=False
HOST=0.0.0.0
PORT=8000

# CORS配置
ALLOWED_ORIGINS=https://servicewechat.com,https://$DOMAIN

# 性能配置
MAX_CHAT_RECORDS_PER_ANALYSIS=100
VOCAB_AUTO_SYNC_HOURS=24
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
EOF
    
    success "环境变量配置完成"
}

# 修改Docker配置
setup_docker_config() {
    info "配置Docker服务..."
    
    # 修改docker-compose.yml使用不同端口
    local compose_file="$PROJECT_DIR/backend/docker-compose.yml"
    
    cat > "$compose_file" << EOF
version: '3.8'

services:
  talkai-backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: talkai-backend
    restart: unless-stopped
    ports:
      - "$DEFAULT_NGINX_PORT:8000"
    environment:
      - DATABASE_URL=sqlite:///./data/db/talkai.db
      - REDIS_URL=redis://talkai-redis:6379/0
      - DEBUG=False
      - HOST=0.0.0.0
      - PORT=8000
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - talkai-redis
    networks:
      - talkai-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  talkai-redis:
    image: redis:7-alpine
    container_name: talkai-redis
    restart: unless-stopped
    ports:
      - "$DEFAULT_REDIS_PORT:6379"
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - talkai_redis_data:/data
    networks:
      - talkai-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3

volumes:
  talkai_redis_data:
    driver: local

networks:
  talkai-network:
    driver: bridge
    name: talkai-network
EOF
    
    success "Docker配置完成"
}

# 复制词典数据库
setup_dictionary() {
    info "设置词典数据库..."
    
    local dict_dir="$PROJECT_DIR/backend/data/db"
    mkdir -p "$dict_dir"
    
    if [[ -n "$DICT_DB_PATH" && -f "$DICT_DB_PATH" ]]; then
        cp "$DICT_DB_PATH" "$dict_dir/dictionary400k.db"
        success "词典数据库复制完成"
    else
        # 尝试从常见位置查找
        local common_paths=(
            "../dictionary400k.db"
            "../../dictionary400k.db"
            "/opt/dictionary400k.db"
            "/home/*/dictionary400k.db"
        )
        
        for path in "${common_paths[@]}"; do
            if [[ -f $path ]]; then
                cp "$path" "$dict_dir/dictionary400k.db"
                success "从 $path 复制词典数据库"
                return 0
            fi
        done
        
        warn "未找到词典数据库，请手动复制 dictionary400k.db 到 $dict_dir/"
    fi
}

# 启动Docker服务
start_docker_services() {
    info "启动Docker服务..."
    
    cd "$PROJECT_DIR/backend"
    
    # 停止可能存在的旧服务
    docker-compose down 2>/dev/null || true
    
    # 构建并启动服务
    docker-compose build --no-cache
    docker-compose up -d
    
    # 等待服务启动
    info "等待服务启动..."
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -f "http://localhost:$DEFAULT_NGINX_PORT/health" >/dev/null 2>&1; then
            success "Docker服务启动成功"
            return 0
        fi
        
        attempt=$((attempt + 1))
        sleep 2
        echo -n "."
    done
    
    error "Docker服务启动超时"
}

# 配置Nginx
setup_nginx() {
    info "配置Nginx..."
    
    local nginx_conf="/etc/nginx/sites-available/talkai-api"
    local upstream_port="$DEFAULT_NGINX_PORT"
    
    # 确保SSL证书路径存在
    if [[ ! -f "$SSL_CERT_PATH" || ! -f "$SSL_KEY_PATH" ]]; then
        warn "SSL证书不存在，将只配置HTTP"
        SSL_CERT_PATH=""
        SSL_KEY_PATH=""
    fi
    
    cat > "$nginx_conf" << EOF
# TalkAI API 配置文件
# 自动生成于: $(date)

upstream talkai_backend {
    server 127.0.0.1:$upstream_port;
    keepalive 32;
}

# 限流配置
limit_req_zone \$binary_remote_addr zone=talkai_api:10m rate=10r/s;
limit_req_zone \$binary_remote_addr zone=talkai_auth:10m rate=5r/s;

EOF

    # HTTPS配置
    if [[ -n "$SSL_CERT_PATH" && -n "$SSL_KEY_PATH" ]]; then
        cat >> "$nginx_conf" << EOF
# HTTPS配置
server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL证书配置
    ssl_certificate $SSL_CERT_PATH;
    ssl_certificate_key $SSL_KEY_PATH;
    
    # SSL安全配置
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;

    # 安全头
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # API路由
    location /api/ {
        limit_req zone=talkai_api burst=20 nodelay;
        
        proxy_pass http://talkai_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 微信小程序CORS
        add_header Access-Control-Allow-Origin https://servicewechat.com always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With" always;
        add_header Access-Control-Allow-Credentials true always;
        
        # 预检请求处理
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin https://servicewechat.com;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With";
            add_header Access-Control-Allow-Credentials true;
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type text/plain;
            add_header Content-Length 0;
            return 204;
        }
    }

    # 认证路由限流
    location /api/v1/auth/ {
        limit_req zone=talkai_auth burst=5 nodelay;
        
        proxy_pass http://talkai_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 健康检查
    location /health {
        proxy_pass http://talkai_backend/health;
        access_log off;
    }

    # API文档 (生产环境可注释)
    location /docs {
        proxy_pass http://talkai_backend/docs;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 阻止访问敏感文件
    location ~ /\\. {
        deny all;
    }
    
    location ~ \\.(env|log|conf)\$ {
        deny all;
    }

    # 日志
    error_log /var/log/nginx/talkai_error.log warn;
    access_log /var/log/nginx/talkai_access.log combined;
}

EOF
    fi

    # HTTP配置 (重定向到HTTPS或直接提供服务)
    cat >> "$nginx_conf" << EOF
# HTTP配置
server {
    listen 80;
    server_name $DOMAIN;
    
EOF

    if [[ -n "$SSL_CERT_PATH" && -n "$SSL_KEY_PATH" ]]; then
        cat >> "$nginx_conf" << EOF
    # 重定向到HTTPS
    return 301 https://\$server_name\$request_uri;
EOF
    else
        cat >> "$nginx_conf" << EOF
    # HTTP直接提供服务 (生产环境请使用HTTPS)
    location /api/ {
        limit_req zone=talkai_api burst=20 nodelay;
        
        proxy_pass http://talkai_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS配置
        add_header Access-Control-Allow-Origin https://servicewechat.com always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With" always;
    }
    
    location /health {
        proxy_pass http://talkai_backend/health;
        access_log off;
    }
    
    location /docs {
        proxy_pass http://talkai_backend/docs;
    }
EOF
    fi

    cat >> "$nginx_conf" << EOF
}
EOF

    # 启用站点
    ln -sf "$nginx_conf" "/etc/nginx/sites-enabled/"
    
    # 测试Nginx配置
    if nginx -t; then
        systemctl reload nginx
        success "Nginx配置成功"
    else
        error "Nginx配置测试失败"
    fi
}

# 运行最终验证
run_verification() {
    info "运行部署验证..."
    
    local protocol="https"
    if [[ -z "$SSL_CERT_PATH" || -z "$SSL_KEY_PATH" ]]; then
        protocol="http"
        warn "使用HTTP协议 (建议配置HTTPS)"
    fi
    
    local api_url="$protocol://$DOMAIN"
    
    # 等待服务完全启动
    sleep 5
    
    # 测试健康检查
    if curl -f -s "$api_url/health" >/dev/null; then
        success "健康检查通过"
    else
        error "健康检查失败"
    fi
    
    # 测试API文档
    if curl -f -s "$api_url/docs" >/dev/null; then
        success "API文档访问正常"
    else
        warn "API文档访问失败 (可能需要额外配置)"
    fi
    
    # 测试基本API
    local test_result
    test_result=$(curl -s "$api_url/api/v1/dict/query?word=hello" || echo "fail")
    if [[ "$test_result" != "fail" ]]; then
        success "API测试通过"
    else
        warn "API测试失败 (可能需要配置API密钥)"
    fi
}

# 显示部署结果
show_deployment_result() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                   🎉 部署成功！                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    local protocol="https"
    if [[ -z "$SSL_CERT_PATH" || -z "$SSL_KEY_PATH" ]]; then
        protocol="http"
    fi
    
    echo -e "${CYAN}📍 服务信息:${NC}"
    echo "   API地址: $protocol://$DOMAIN/api/v1"
    echo "   健康检查: $protocol://$DOMAIN/health"
    echo "   API文档: $protocol://$DOMAIN/docs"
    echo "   项目目录: $PROJECT_DIR"
    echo ""
    
    echo -e "${CYAN}🔧 管理命令:${NC}"
    echo "   查看状态: docker-compose ps"
    echo "   查看日志: docker-compose logs -f"
    echo "   重启服务: docker-compose restart"
    echo "   停止服务: docker-compose down"
    echo ""
    
    echo -e "${CYAN}📱 微信小程序配置:${NC}"
    echo "   1. 更新 frontend/services/api.js 中的 BASE_URL"
    echo "   2. 在微信公众平台添加服务器域名: $protocol://$DOMAIN"
    echo "   3. 使用微信开发者工具上传小程序代码"
    echo ""
    
    echo -e "${CYAN}⚠️  重要提醒:${NC}"
    echo "   • 请妥善保管 .env 文件中的API密钥"
    echo "   • 定期备份数据库和配置文件"
    echo "   • 监控服务运行状态和日志"
    if [[ -z "$SSL_CERT_PATH" || -z "$SSL_KEY_PATH" ]]; then
        echo "   • 建议配置HTTPS以提高安全性"
    fi
    echo ""
}

# 显示服务状态
show_status() {
    echo -e "${CYAN}TalkAI 服务状态${NC}"
    echo "=========================="
    
    if [[ -d "/www/wwwroot/talkai_miniprogram/backend" ]]; then
        cd "/www/wwwroot/talkai_miniprogram/backend"
        
        echo -e "\n${YELLOW}Docker容器状态:${NC}"
        docker-compose ps
        
        echo -e "\n${YELLOW}端口监听状态:${NC}"
        netstat -tlnp | grep -E ':(8001|6380)' || echo "未检测到TalkAI端口"
        
        echo -e "\n${YELLOW}Nginx配置:${NC}"
        if [[ -f "/etc/nginx/sites-enabled/talkai-api" ]]; then
            echo "✅ Nginx配置已启用"
        else
            echo "❌ Nginx配置未启用"
        fi
        
        echo -e "\n${YELLOW}服务健康检查:${NC}"
        if curl -f -s "http://localhost:8001/health" >/dev/null; then
            echo "✅ 后端服务正常"
        else
            echo "❌ 后端服务异常"
        fi
    else
        echo "❌ TalkAI未部署或目录不存在"
    fi
}

# 显示详细信息
show_info() {
    echo -e "${CYAN}TalkAI 详细信息${NC}"
    echo "=========================="
    
    echo -e "\n${YELLOW}系统信息:${NC}"
    echo "操作系统: $(uname -o)"
    echo "内核版本: $(uname -r)"
    echo "CPU架构: $(uname -m)"
    
    echo -e "\n${YELLOW}Docker信息:${NC}"
    docker --version
    docker-compose --version
    
    echo -e "\n${YELLOW}Nginx信息:${NC}"
    nginx -v
    
    echo -e "\n${YELLOW}资源使用:${NC}"
    echo "内存使用: $(free -h | awk 'NR==2{printf "已用:%s 可用:%s 使用率:%.2f%%", $3,$7,$3*100/$2}')"
    echo "磁盘使用: $(df -h / | awk 'NR==2{printf "已用:%s 可用:%s 使用率:%s", $3,$4,$5}')"
    
    if [[ -d "/www/wwwroot/talkai_miniprogram" ]]; then
        echo -e "\n${YELLOW}TalkAI配置:${NC}"
        echo "项目目录: /www/wwwroot/talkai_miniprogram"
        echo "配置文件: $(ls -la /www/wwwroot/talkai_miniprogram/backend/.env 2>/dev/null || echo "不存在")"
        echo "数据目录: $(ls -ld /www/wwwroot/talkai_miniprogram/backend/data 2>/dev/null || echo "不存在")"
    fi
}

# 主部署流程
main_deployment() {
    show_banner
    
    log "开始TalkAI部署流程..."
    log "部署时间: $DEPLOY_TIME"
    log "日志文件: $LOG_FILE"
    
    # 检查环境
    check_environment
    
    if [[ "$CHECK_ONLY" == true ]]; then
        success "环境检查完成，系统符合部署要求"
        exit 0
    fi
    
    # 配置流程
    if [[ "$INTERACTIVE_MODE" == true ]]; then
        interactive_config
    elif [[ "$AUTO_MODE" == true ]]; then
        warn "使用自动模式，将使用默认配置"
        DOMAIN="$DEFAULT_DOMAIN"
        PROJECT_DIR="$DEFAULT_PROJECT_DIR"
        warn "请确保已在脚本中配置API密钥"
    else
        error "请指定部署模式: --interactive 或 --auto"
    fi
    
    # 安装依赖
    install_dependencies
    
    # 设置项目目录
    setup_project_directory
    
    # 配置环境变量
    setup_environment
    
    # 配置Docker
    setup_docker_config
    
    # 设置词典数据库
    setup_dictionary
    
    # 启动Docker服务
    start_docker_services
    
    # 配置Nginx
    setup_nginx
    
    # 运行验证
    run_verification
    
    # 显示结果
    show_deployment_result
    
    log "部署完成: $DEPLOY_TIME"
}

# 错误处理
trap 'error "部署过程中发生错误，请查看日志: $LOG_FILE"' ERR

# 主程序入口
main() {
    # 初始化日志文件
    echo "TalkAI 部署日志 - $(date)" > "$LOG_FILE"
    
    # 解析参数
    parse_args "$@"
    
    # 加载配置
    load_config
    
    # 执行主流程
    main_deployment
}

# 如果直接运行脚本
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi