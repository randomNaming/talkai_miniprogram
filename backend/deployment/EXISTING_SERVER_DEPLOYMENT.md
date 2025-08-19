# TalkAI - 现有服务器专业部署指南

## 📋 适用场景

本指南专为已有运行中网站的服务器设计，通过子域名方式部署TalkAI，实现业务隔离和零冲突运行。

### 典型环境
- ✅ 已运行网站 (如 jimingge.net)
- ✅ Nginx + SSL证书配置
- ✅ 有一定的运维管理经验
- ✅ 需要保证现有服务不受影响

### 部署架构
```
现有网站: https://jimingge.net       (端口80/443)
TalkAI API: https://api.jimingge.net  (端口8001)
Redis缓存: 127.0.0.1:6380
数据库: SQLite文件存储
```

---

## 🔍 第1步: 现有环境评估

### 1.1 系统资源评估

```bash
# 系统资源检查脚本
cat > check_resources.sh << 'EOF'
#!/bin/bash
echo "=== 系统资源评估 ==="
echo "CPU核心数: $(nproc)"
echo "总内存: $(free -h | awk 'NR==2{print $2}')"
echo "可用内存: $(free -h | awk 'NR==2{print $7}')"
echo "磁盘使用情况:"
df -h / | tail -1
echo
echo "当前负载:"
uptime
echo
echo "内存使用详情:"
free -m
echo
EOF

bash check_resources.sh
```

**资源要求评估:**
- **CPU**: TalkAI需要额外0.5-1核心
- **内存**: 需要额外1-2GB空闲内存
- **磁盘**: 需要至少5GB可用空间
- **网络**: 额外需要处理AI API调用

### 1.2 现有服务清单识别

```bash
# 服务端口占用检查
echo "=== 当前服务端口占用 ==="
sudo netstat -tlnp | grep -E ':(80|443|8000-8010|6379-6390)' | sort

# 检查Docker服务
echo -e "\n=== Docker容器状态 ==="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

# 检查Nginx配置
echo -e "\n=== Nginx站点配置 ==="
ls -la /etc/nginx/sites-enabled/

# 检查SSL证书
echo -e "\n=== 当前SSL证书 ==="
sudo certbot certificates
```

### 1.3 依赖服务检测

```bash
# 检查关键依赖
check_dependencies() {
    echo "=== 依赖服务检测 ==="
    
    # Docker
    if command -v docker >/dev/null 2>&1; then
        echo "✅ Docker: $(docker --version)"
    else
        echo "❌ Docker: 未安装"
    fi
    
    # Docker Compose
    if command -v docker-compose >/dev/null 2>&1; then
        echo "✅ Docker Compose: $(docker-compose --version)"
    else
        echo "❌ Docker Compose: 未安装"
    fi
    
    # Nginx
    if systemctl is-active --quiet nginx; then
        echo "✅ Nginx: 运行中 ($(nginx -v 2>&1))"
    else
        echo "❌ Nginx: 未运行或未安装"
    fi
    
    # Certbot
    if command -v certbot >/dev/null 2>&1; then
        echo "✅ Certbot: $(certbot --version)"
    else
        echo "⚠️  Certbot: 未安装 (SSL证书管理工具)"
    fi
}

check_dependencies
```

---

## ⚡ 第2步: 服务冲突预防

### 2.1 端口冲突处理

```bash
# 检查TalkAI所需端口
TALKAI_PORTS=(8001 6380)

echo "=== 端口冲突检查 ==="
for port in "${TALKAI_PORTS[@]}"; do
    if sudo netstat -tlnp | grep ":$port " >/dev/null; then
        echo "⚠️  端口 $port 已被占用:"
        sudo netstat -tlnp | grep ":$port "
        echo "   需要停止占用服务或修改TalkAI端口配置"
    else
        echo "✅ 端口 $port 可用"
    fi
done
```

**端口冲突解决方案:**

**方案A: 修改冲突服务端口**
```bash
# 例如修改现有Redis端口
sudo systemctl stop redis
sudo sed -i 's/port 6379/port 6379/' /etc/redis/redis.conf
sudo systemctl start redis
```

**方案B: 修改TalkAI端口配置**
```yaml
# 在docker-compose.yml中修改端口映射
services:
  talkai-backend:
    ports:
      - "8002:8000"  # 改为8002
  talkai-redis:
    ports:
      - "6381:6379"  # 改为6381
```

### 2.2 Docker网络隔离

```bash
# 创建专用Docker网络
docker network create talkai-network \
  --driver bridge \
  --subnet=172.20.0.0/16 \
  --ip-range=172.20.240.0/20 \
  --gateway=172.20.0.1

# 查看网络配置
docker network ls
docker network inspect talkai-network
```

### 2.3 文件系统隔离

```bash
# 创建独立的数据目录
sudo mkdir -p /www/wwwroot/talkai_miniprogram
sudo chown -R $USER:$USER /www/wwwroot/talkai_miniprogram

# 设置适当权限
chmod -R 755 /www/wwwroot/talkai_miniprogram
```

---

## 🌐 第3步: 子域名配置详解

### 3.1 DNS配置最佳实践

```bash
# DNS配置验证脚本
verify_dns() {
    local domain="api.jimingge.net"
    local server_ip=$(curl -s ifconfig.me)
    
    echo "=== DNS配置验证 ==="
    echo "服务器IP: $server_ip"
    echo
    
    # 检查A记录
    echo "检查A记录解析:"
    nslookup $domain 8.8.8.8
    
    # 验证解析结果
    resolved_ip=$(dig +short $domain @8.8.8.8)
    if [ "$resolved_ip" = "$server_ip" ]; then
        echo "✅ DNS解析正确"
    else
        echo "❌ DNS解析错误: $resolved_ip != $server_ip"
    fi
    
    # 检查TTL
    echo "TTL设置:"
    dig $domain | grep -A1 "ANSWER SECTION"
}

verify_dns
```

**DNS配置建议:**
- **TTL设置**: 初始设置为300秒，部署完成后可调整为3600秒
- **A记录**: api.jimingge.net → 服务器IP
- **备用DNS**: 配置多个DNS服务器确保解析稳定性

### 3.2 多DNS服务器验证

```bash
# 多DNS服务器解析测试
test_dns_servers() {
    local domain="api.jimingge.net"
    local dns_servers=("8.8.8.8" "1.1.1.1" "223.5.5.5" "114.114.114.114")
    
    echo "=== 多DNS服务器解析测试 ==="
    for dns in "${dns_servers[@]}"; do
        echo -n "DNS $dns: "
        result=$(dig +short $domain @$dns 2>/dev/null)
        if [ -n "$result" ]; then
            echo "✅ $result"
        else
            echo "❌ 解析失败"
        fi
    done
}

test_dns_servers
```

---

## 🚪 第4步: 端口管理与防火墙

### 4.1 防火墙精细控制

```bash
# TalkAI专用防火墙规则
configure_firewall() {
    echo "=== 配置TalkAI防火墙规则 ==="
    
    # 允许内部Docker通信
    sudo ufw allow from 172.20.0.0/16 to any port 8001
    sudo ufw allow from 172.20.0.0/16 to any port 6380
    
    # 允许Nginx访问后端
    sudo ufw allow from 127.0.0.1 to any port 8001
    
    # 日志记录
    sudo ufw logging on
    
    # 查看规则
    sudo ufw status numbered
    
    echo "✅ 防火墙规则配置完成"
}

configure_firewall
```

### 4.2 系统资源限制

```bash
# 配置systemd资源限制
cat > /etc/systemd/system/talkai.slice << 'EOF'
[Unit]
Description=TalkAI Services Resource Control
Before=slices.target

[Slice]
MemoryAccounting=true
MemoryMax=2G
CPUAccounting=true
CPUQuota=150%
TasksAccounting=true
TasksMax=1000
EOF

sudo systemctl daemon-reload
sudo systemctl start talkai.slice
```

---

## 🔄 第5步: 渐进式部署策略

### 5.1 部署预演 (Dry Run)

```bash
# 创建部署预演脚本
cat > deployment_dryrun.sh << 'EOF'
#!/bin/bash
set -e

echo "=== TalkAI部署预演 ==="

# 1. 环境检查
echo "1️⃣ 环境检查..."
./deployment/deploy-existing-server.sh --check-only

# 2. 配置验证
echo "2️⃣ 配置文件验证..."
if [ ! -f "backend/.env" ]; then
    echo "❌ .env文件不存在"
    exit 1
fi

# 检查必需环境变量
required_vars=("MOONSHOT_API_KEY" "WECHAT_APP_ID" "WECHAT_APP_SECRET")
for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" backend/.env; then
        echo "❌ 缺少环境变量: $var"
        exit 1
    fi
done

# 3. 端口可用性检查
echo "3️⃣ 端口可用性检查..."
if sudo netstat -tlnp | grep -E ':(8001|6380)' >/dev/null; then
    echo "❌ 端口冲突，请先解决"
    exit 1
fi

# 4. Docker镜像预构建
echo "4️⃣ Docker镜像预构建..."
cd backend && docker-compose build --no-cache

echo "✅ 部署预演完成，可以开始正式部署"
EOF

chmod +x deployment_dryrun.sh
./deployment_dryrun.sh
```

### 5.2 分阶段部署流程

```bash
# 阶段1: 基础服务部署
deploy_stage1() {
    echo "=== 阶段1: 基础服务部署 ==="
    
    # 部署Redis缓存
    docker-compose up -d talkai-redis
    
    # 等待Redis启动
    echo "等待Redis启动..."
    sleep 10
    
    # 验证Redis
    if docker-compose exec talkai-redis redis-cli ping | grep -q "PONG"; then
        echo "✅ Redis启动成功"
    else
        echo "❌ Redis启动失败"
        exit 1
    fi
}

# 阶段2: 后端服务部署
deploy_stage2() {
    echo "=== 阶段2: 后端服务部署 ==="
    
    # 部署后端应用
    docker-compose up -d talkai-backend
    
    # 等待应用启动
    echo "等待后端应用启动..."
    sleep 30
    
    # 健康检查
    for i in {1..30}; do
        if curl -f http://localhost:8001/health >/dev/null 2>&1; then
            echo "✅ 后端服务启动成功"
            break
        fi
        sleep 2
    done
}

# 阶段3: Nginx配置
deploy_stage3() {
    echo "=== 阶段3: Nginx反向代理配置 ==="
    
    # 生成Nginx配置
    ./deployment/deploy-existing-server.sh --nginx-only
    
    # 验证配置
    sudo nginx -t
    
    # 重载Nginx
    sudo systemctl reload nginx
    
    echo "✅ Nginx配置完成"
}

# 执行分阶段部署
deploy_stage1
deploy_stage2  
deploy_stage3
```

### 5.3 完整回滚策略

```bash
# 创建回滚脚本
cat > rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== TalkAI服务回滚 ==="

# 1. 停止TalkAI服务
echo "1️⃣ 停止TalkAI服务..."
cd /www/wwwroot/talkai_miniprogram/backend
docker-compose down

# 2. 删除Nginx配置
echo "2️⃣ 删除Nginx配置..."
sudo rm -f /etc/nginx/sites-enabled/talkai-api
sudo rm -f /etc/nginx/sites-available/talkai-api

# 3. 重载Nginx
echo "3️⃣ 重载Nginx配置..."
sudo nginx -t && sudo systemctl reload nginx

# 4. 清理Docker资源
echo "4️⃣ 清理Docker资源..."
docker system prune -f

# 5. 删除项目文件 (可选)
read -p "是否删除项目文件? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo rm -rf /www/wwwroot/talkai_miniprogram
    echo "✅ 项目文件已删除"
fi

echo "✅ 回滚完成"
EOF

chmod +x rollback.sh
```

---

## 🔐 第6步: SSL证书复用策略

### 6.1 现有证书评估

```bash
# SSL证书评估脚本
evaluate_ssl() {
    echo "=== SSL证书评估 ==="
    
    # 检查现有证书
    if sudo certbot certificates | grep -q "jimingge.net"; then
        echo "✅ 发现现有证书"
        
        # 检查证书详情
        cert_path="/etc/letsencrypt/live/jimingge.net"
        if [ -f "$cert_path/fullchain.pem" ]; then
            echo "证书路径: $cert_path"
            
            # 检查证书有效期
            expiry=$(openssl x509 -in "$cert_path/fullchain.pem" -noout -enddate | cut -d= -f2)
            echo "到期时间: $expiry"
            
            # 检查域名覆盖
            domains=$(openssl x509 -in "$cert_path/fullchain.pem" -noout -text | grep -A1 "Subject Alternative Name" | grep -o "[a-zA-Z0-9.-]*\.jimingge\.net" | sort -u)
            echo "覆盖域名:"
            echo "$domains"
            
            # 检查是否覆盖api子域名
            if echo "$domains" | grep -q "api.jimingge.net\|*.jimingge.net"; then
                echo "✅ 证书已覆盖api子域名"
                return 0
            else
                echo "⚠️  证书未覆盖api子域名，需要扩展"
                return 1
            fi
        fi
    else
        echo "❌ 未找到jimingge.net证书"
        return 2
    fi
}

evaluate_ssl
ssl_status=$?
```

### 6.2 证书扩展方案

```bash
# 证书扩展策略
extend_certificate() {
    echo "=== 扩展SSL证书 ==="
    
    case $ssl_status in
        0)
            echo "✅ 证书已满足要求，无需操作"
            ;;
        1)
            echo "🔄 扩展现有证书..."
            sudo certbot --nginx -d jimingge.net -d www.jimingge.net -d api.jimingge.net --expand
            ;;
        2)
            echo "🆕 申请新证书..."
            sudo certbot --nginx -d jimingge.net -d www.jimingge.net -d api.jimingge.net
            ;;
    esac
    
    # 验证证书配置
    echo "验证证书配置..."
    openssl s_client -connect api.jimingge.net:443 -servername api.jimingge.net </dev/null 2>/dev/null | openssl x509 -noout -dates
}

if [ $ssl_status -ne 0 ]; then
    extend_certificate
fi
```

### 6.3 自动更新配置

```bash
# 配置证书自动更新
configure_cert_renewal() {
    echo "=== 配置证书自动更新 ==="
    
    # 创建更新后钩子
    cat > /etc/letsencrypt/renewal-hooks/post/talkai-reload.sh << 'EOF'
#!/bin/bash
# TalkAI证书更新后重载服务

# 重载Nginx
systemctl reload nginx

# 记录日志
echo "$(date): SSL证书更新，Nginx已重载" >> /var/log/talkai-cert-renewal.log
EOF
    
    chmod +x /etc/letsencrypt/renewal-hooks/post/talkai-reload.sh
    
    # 测试自动更新
    sudo certbot renew --dry-run
    
    echo "✅ 证书自动更新配置完成"
}

configure_cert_renewal
```

---

## 💾 第7步: 数据迁移与共存

### 7.1 数据库迁移策略

```bash
# 如果从其他环境迁移数据
migrate_database() {
    echo "=== 数据库迁移 ==="
    
    local backup_file="$1"
    local target_db="/www/wwwroot/talkai_miniprogram/backend/data/db/talkai.db"
    
    if [ -f "$backup_file" ]; then
        echo "从备份恢复数据: $backup_file"
        
        # 创建目标目录
        mkdir -p "$(dirname "$target_db")"
        
        # 复制数据库
        cp "$backup_file" "$target_db"
        
        # 设置权限
        chown $USER:$USER "$target_db"
        chmod 644 "$target_db"
        
        echo "✅ 数据库迁移完成"
    else
        echo "ℹ️  未提供备份文件，将创建新数据库"
    fi
}

# 词典数据库处理
setup_dictionary() {
    echo "=== 词典数据库配置 ==="
    
    local dict_path="/www/wwwroot/talkai_miniprogram/backend/data/db/dictionary400k.db"
    
    # 常见词典位置
    local dict_sources=(
        "../dictionary400k.db"
        "/opt/dictionary400k.db" 
        "/home/$USER/dictionary400k.db"
        "./dictionary400k.db"
    )
    
    for source in "${dict_sources[@]}"; do
        if [ -f "$source" ]; then
            echo "发现词典文件: $source"
            cp "$source" "$dict_path"
            echo "✅ 词典数据库配置完成"
            return 0
        fi
    done
    
    echo "⚠️  未找到词典文件，请手动复制到: $dict_path"
}

# 如果有备份文件，取消下面的注释
# migrate_database "/path/to/backup/talkai.db"
setup_dictionary
```

### 7.2 配置文件整合

```bash
# 整合现有服务配置
integrate_configs() {
    echo "=== 配置文件整合 ==="
    
    # 备份现有Nginx配置
    backup_dir="/www/wwwroot/talkai_miniprogram/config/backup"
    mkdir -p "$backup_dir"
    
    sudo cp -r /etc/nginx/sites-enabled "$backup_dir/nginx-sites-enabled-$(date +%Y%m%d_%H%M%S)"
    
    # 检查现有的环境变量冲突
    if [ -f "/etc/environment" ]; then
        grep -E "(MOONSHOT|OPENAI|WECHAT)" /etc/environment > "$backup_dir/system-env-vars.txt" 2>/dev/null || true
    fi
    
    echo "✅ 配置备份完成: $backup_dir"
}

integrate_configs
```

---

## ✅ 第8步: 部署验证与测试

### 8.1 服务可用性验证

```bash
# 完整的服务验证脚本
comprehensive_validation() {
    echo "=== 服务可用性全面验证 ==="
    
    local base_url="https://api.jimingge.net"
    local errors=0
    
    # 1. 基础连通性测试
    echo "1️⃣ 基础连通性测试"
    if curl -f -s "$base_url/health" >/dev/null; then
        echo "✅ 健康检查端点正常"
    else
        echo "❌ 健康检查失败"
        ((errors++))
    fi
    
    # 2. API功能测试
    echo "2️⃣ API功能测试"
    
    # 词典查询测试
    dict_result=$(curl -s "$base_url/api/v1/dict/query?word=hello")
    if echo "$dict_result" | grep -q "word"; then
        echo "✅ 词典API正常"
    else
        echo "❌ 词典API异常"
        ((errors++))
    fi
    
    # 3. SSL证书验证
    echo "3️⃣ SSL证书验证"
    if openssl s_client -connect api.jimingge.net:443 -servername api.jimingge.net </dev/null 2>&1 | grep -q "Verify return code: 0"; then
        echo "✅ SSL证书有效"
    else
        echo "❌ SSL证书问题"
        ((errors++))
    fi
    
    # 4. 性能基准测试
    echo "4️⃣ 基础性能测试"
    response_time=$(curl -o /dev/null -s -w "%{time_total}" "$base_url/health")
    if (( $(echo "$response_time < 2.0" | bc -l) )); then
        echo "✅ 响应时间正常: ${response_time}s"
    else
        echo "⚠️  响应时间较慢: ${response_time}s"
    fi
    
    # 总结
    echo
    if [ $errors -eq 0 ]; then
        echo "🎉 所有验证通过！TalkAI部署成功"
    else
        echo "❌ 发现 $errors 个问题，请检查日志"
    fi
    
    return $errors
}

comprehensive_validation
```

### 8.2 性能基准测试

```bash
# 性能基准测试
performance_benchmark() {
    echo "=== 性能基准测试 ==="
    
    local base_url="https://api.jimingge.net"
    
    # 并发连接测试
    echo "测试并发连接性能..."
    ab -n 100 -c 10 "$base_url/health" > performance_test.log 2>&1
    
    # 提取关键指标
    echo "性能测试结果:"
    grep -E "(Requests per second|Time per request|Connection Times)" performance_test.log
    
    # API响应时间测试
    echo "API响应时间分析:"
    for i in {1..10}; do
        time=$(curl -o /dev/null -s -w "%{time_total}" "$base_url/health")
        echo "请求 $i: ${time}s"
        sleep 1
    done
}

performance_benchmark
```

---

## 📊 第9步: 运维监控配置

### 9.1 日志管理配置

```bash
# 配置日志管理
setup_logging() {
    echo "=== 配置日志管理 ==="
    
    # 创建日志目录
    mkdir -p /www/wwwroot/talkai_miniprogram/logs
    
    # 配置logrotate
    cat > /etc/logrotate.d/talkai << 'EOF'
/www/wwwroot/talkai_miniprogram/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 www-data www-data
    postrotate
        docker-compose -f /www/wwwroot/talkai_miniprogram/backend/docker-compose.yml restart talkai-backend
    endscript
}
EOF
    
    # 配置rsyslog收集Docker日志
    cat > /etc/rsyslog.d/49-talkai.conf << 'EOF'
# TalkAI Docker日志收集
if $programname == 'talkai-backend' then /www/wwwroot/talkai_miniprogram/logs/backend.log
if $programname == 'talkai-redis' then /www/wwwroot/talkai_miniprogram/logs/redis.log
& stop
EOF
    
    sudo systemctl restart rsyslog
    
    echo "✅ 日志管理配置完成"
}

setup_logging
```

### 9.2 监控告警配置

```bash
# 基础监控脚本
cat > /usr/local/bin/talkai-monitor.sh << 'EOF'
#!/bin/bash
# TalkAI服务监控脚本

LOG_FILE="/var/log/talkai-monitor.log"
ALERT_EMAIL="admin@jimingge.net"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查服务状态
check_service() {
    if ! curl -f -s https://api.jimingge.net/health >/dev/null; then
        log "ERROR: TalkAI服务无响应"
        
        # 尝试重启
        cd /www/wwwroot/talkai_miniprogram/backend
        docker-compose restart talkai-backend
        
        # 发送告警邮件 (需要配置邮件服务)
        # echo "TalkAI服务异常，已尝试重启" | mail -s "TalkAI Alert" "$ALERT_EMAIL"
        
        return 1
    else
        log "INFO: 服务状态正常"
        return 0
    fi
}

# 检查资源使用
check_resources() {
    # 内存使用率
    mem_usage=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
    if (( $(echo "$mem_usage > 90" | bc -l) )); then
        log "WARNING: 内存使用率过高: ${mem_usage}%"
    fi
    
    # 磁盘使用率
    disk_usage=$(df /www/wwwroot | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 85 ]; then
        log "WARNING: 磁盘使用率过高: ${disk_usage}%"
    fi
}

# 执行检查
check_service
check_resources

EOF

chmod +x /usr/local/bin/talkai-monitor.sh

# 添加到crontab
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/talkai-monitor.sh") | crontab -
```

---

## 🚨 第10步: 故障恢复预案

### 10.1 自动故障检测

```bash
# 故障自动恢复脚本
cat > /usr/local/bin/talkai-auto-recovery.sh << 'EOF'
#!/bin/bash
# TalkAI自动故障恢复

RECOVERY_LOG="/var/log/talkai-recovery.log"
PROJECT_DIR="/www/wwwroot/talkai_miniprogram"

log_recovery() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$RECOVERY_LOG"
}

# 服务恢复
recover_service() {
    log_recovery "开始服务恢复流程"
    
    cd "$PROJECT_DIR/backend"
    
    # 停止服务
    docker-compose down
    
    # 清理异常容器
    docker system prune -f
    
    # 重启服务
    docker-compose up -d
    
    # 等待服务启动
    sleep 30
    
    # 验证恢复
    if curl -f -s https://api.jimingge.net/health >/dev/null; then
        log_recovery "✅ 服务恢复成功"
        return 0
    else
        log_recovery "❌ 服务恢复失败"
        return 1
    fi
}

# 数据备份
backup_data() {
    log_recovery "创建数据备份"
    
    backup_dir="$PROJECT_DIR/backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 备份数据库
    cp "$PROJECT_DIR/backend/data/db/"*.db "$backup_dir/"
    
    # 备份配置
    cp "$PROJECT_DIR/backend/.env" "$backup_dir/"
    
    log_recovery "数据备份完成: $backup_dir"
}

# 主恢复流程
main() {
    if ! curl -f -s https://api.jimingge.net/health >/dev/null; then
        log_recovery "检测到服务异常，开始恢复"
        
        # 创建备份
        backup_data
        
        # 尝试恢复
        if recover_service; then
            log_recovery "自动恢复成功"
        else
            log_recovery "自动恢复失败，需要人工介入"
            # 发送紧急告警
            echo "TalkAI服务自动恢复失败，需要人工处理" | mail -s "TalkAI Emergency" admin@jimingge.net 2>/dev/null || true
        fi
    fi
}

main "$@"
EOF

chmod +x /usr/local/bin/talkai-auto-recovery.sh
```

### 10.2 数据备份与恢复

```bash
# 完整备份脚本
cat > /usr/local/bin/talkai-backup.sh << 'EOF'
#!/bin/bash
# TalkAI完整备份脚本

PROJECT_DIR="/www/wwwroot/talkai_miniprogram"
BACKUP_DIR="/backup/talkai"
RETENTION_DAYS=30

# 创建备份
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"
    
    mkdir -p "$backup_path"
    
    echo "创建完整备份: $backup_path"
    
    # 备份数据库
    cp -r "$PROJECT_DIR/backend/data" "$backup_path/"
    
    # 备份配置文件
    cp "$PROJECT_DIR/backend/.env" "$backup_path/"
    cp "$PROJECT_DIR/backend/docker-compose.yml" "$backup_path/"
    
    # 备份Nginx配置
    sudo cp /etc/nginx/sites-available/talkai-api "$backup_path/" 2>/dev/null || true
    
    # 创建压缩包
    tar -czf "$backup_path.tar.gz" -C "$BACKUP_DIR" "$timestamp"
    rm -rf "$backup_path"
    
    echo "备份完成: $backup_path.tar.gz"
}

# 清理旧备份
cleanup_old_backups() {
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    echo "清理 $RETENTION_DAYS 天前的备份"
}

mkdir -p "$BACKUP_DIR"
create_backup
cleanup_old_backups
EOF

chmod +x /usr/local/bin/talkai-backup.sh

# 配置定期备份
(crontab -l 2>/dev/null; echo "0 2 * * * /usr/local/bin/talkai-backup.sh") | crontab -
```

---

## 📈 部署完成验证

部署完成后，执行以下验证确保所有功能正常：

```bash
# 最终验证脚本
final_verification() {
    echo "=== TalkAI部署最终验证 ==="
    
    # 1. 服务状态
    ./deployment/deploy-existing-server.sh --status
    
    # 2. 完整功能测试
    comprehensive_validation
    
    # 3. 性能测试
    performance_benchmark
    
    # 4. 监控配置验证
    echo "检查监控配置:"
    crontab -l | grep talkai
    
    echo
    echo "🎉 TalkAI现有服务器部署完成！"
    echo
    echo "访问地址:"
    echo "  - API: https://api.jimingge.net"
    echo "  - 健康检查: https://api.jimingge.net/health"
    echo "  - API文档: https://api.jimingge.net/docs"
    echo
    echo "管理命令:"
    echo "  - 服务状态: ./deployment/deploy-existing-server.sh --status"
    echo "  - 查看日志: docker-compose -f backend/docker-compose.yml logs -f"
    echo "  - 重启服务: docker-compose -f backend/docker-compose.yml restart"
    echo "  - 备份数据: /usr/local/bin/talkai-backup.sh"
    echo
}

final_verification
```

---

**✅ 现有服务器部署完成！**

本指南提供了专业级的现有服务器部署方案，包含完整的监控、备份和恢复机制。如遇问题，请参考：
- [配置参考手册](./CONFIG_REFERENCE.md)
- [故障排除指南](./TROUBLESHOOTING.md)
- [快速开始指南](./QUICK_START.md)