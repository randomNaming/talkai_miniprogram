# TalkAI 小程序后端手动部署指南

本指南提供不使用 Docker 的传统部署方式，适用于各种 Linux 服务器环境。

## 系统要求

- **操作系统**: CentOS 7+, Ubuntu 18.04+, 或其他主流 Linux 发行版
- **Python**: 3.8+
- **内存**: 建议 2GB+
- **磁盘空间**: 建议 10GB+
- **网络**: 需要访问外部 API (OpenAI/Moonshot)

## 1. 环境准备

### 1.1 安装系统依赖

**CentOS/RHEL:**
```bash
sudo yum update -y
sudo yum install -y python3 python3-pip python3-venv nginx redis git curl wget
sudo systemctl enable --now nginx redis
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx redis-server git curl wget
sudo systemctl enable --now nginx redis-server
```

### 1.2 创建用户和目录

```bash
# 创建专用用户
sudo useradd -m -s /bin/bash talkai
sudo usermod -aG sudo talkai

# 创建项目目录
sudo mkdir -p /www/wwwroot/talkai
sudo chown talkai:talkai /www/wwwroot/talkai

# 切换到项目用户
sudo su - talkai
```

## 2. 项目部署

### 2.1 获取项目代码

```bash
cd /www/wwwroot/talkai
git clone <your-repo-url> .
# 或者上传项目文件到此目录
```

### 2.2 Python环境设置

```bash
# 进入后端目录
cd /www/wwwroot/talkai/backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖（排除Docker相关）
sed '/^docker/d' requirements.txt > requirements_manual.txt
pip install -r requirements_manual.txt

# 如果有特定版本冲突，可以单独安装
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0
```

### 2.3 配置环境变量

```bash
# 创建环境配置文件
cat > /www/wwwroot/talkai/backend/.env << 'EOF'
# 数据库配置
DATABASE_URL=sqlite:///./data/db/talkai.db

# Redis配置 (本地Redis)
REDIS_URL=redis://localhost:6379/0

# AI API配置 (必须配置其中一个)
MOONSHOT_API_KEY=your_moonshot_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here

# 微信小程序配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# 安全配置
SECRET_KEY=your-super-secure-secret-key-at-least-32-characters-long
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用配置
MODEL_PROVIDER=moonshot
DEBUG=False
HOST=0.0.0.0
PORT=8000

# CORS配置
ALLOWED_ORIGINS=https://servicewechat.com,https://your-domain.com

# 性能配置
MAX_CHAT_RECORDS_PER_ANALYSIS=100
VOCAB_AUTO_SYNC_HOURS=24
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
EOF

# 设置环境文件权限
chmod 600 /www/wwwroot/talkai/backend/.env
```

### 2.4 创建必要目录

```bash
cd /www/wwwroot/talkai/backend
mkdir -p data/db logs data/uploads
```

### 2.5 设置词典数据库

```bash
# 如果有词典数据库文件，复制到指定位置
# cp /path/to/dictionary400k.db /www/wwwroot/talkai/backend/data/db/

# 或者创建空的数据库文件（如果没有词典数据库）
touch /www/wwwroot/talkai/backend/data/db/dictionary400k.db
```

## 3. 服务配置

### 3.1 创建systemd服务文件

```bash
sudo tee /etc/systemd/system/talkai.service << 'EOF'
[Unit]
Description=TalkAI Backend Service
After=network.target redis.service
Wants=redis.service

[Service]
Type=exec
User=talkai
Group=talkai
WorkingDirectory=/www/wwwroot/talkai/backend
Environment=PATH=/www/wwwroot/talkai/backend/venv/bin
ExecStart=/www/wwwroot/talkai/backend/venv/bin/python main.py
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

# 性能优化
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
```

### 3.2 使用Gunicorn（生产环境推荐）

```bash
# 创建Gunicorn配置文件
cat > /www/wwwroot/talkai/backend/gunicorn.conf.py << 'EOF'
# Gunicorn配置文件
import multiprocessing
import os

# 服务器套接字
bind = "127.0.0.1:8000"
backlog = 2048

# Worker进程
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# 超时
timeout = 30
keepalive = 2

# 日志
accesslog = "/www/wwwroot/talkai/backend/logs/access.log"
errorlog = "/www/wwwroot/talkai/backend/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# 进程命名
proc_name = "talkai-backend"

# 优雅重启
preload_app = True
enable_stdio_inheritance = True
EOF

# 更新systemd服务文件使用Gunicorn
sudo tee /etc/systemd/system/talkai.service << 'EOF'
[Unit]
Description=TalkAI Backend Service (Gunicorn)
After=network.target redis.service
Wants=redis.service

[Service]
Type=notify
User=talkai
Group=talkai
WorkingDirectory=/www/wwwroot/talkai/backend
Environment=PATH=/www/wwwroot/talkai/backend/venv/bin
ExecStart=/www/wwwroot/talkai/backend/venv/bin/gunicorn main:app -c gunicorn.conf.py
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=10
KillMode=mixed
StandardOutput=journal
StandardError=journal

# 性能优化
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF
```

## 4. Nginx配置

### 4.1 创建Nginx配置文件

```bash
sudo tee /etc/nginx/sites-available/talkai << 'EOF'
# TalkAI API 配置
server {
    listen 80;
    server_name your-domain.com api.your-domain.com;  # 替换为你的域名
    
    # 重定向到HTTPS (如果有SSL证书)
    # return 301 https://$server_name$request_uri;
    
    # 如果没有SSL证书，可以直接在HTTP上提供服务
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # CORS配置
        add_header Access-Control-Allow-Origin "https://servicewechat.com" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With" always;
        add_header Access-Control-Allow-Credentials true always;
        
        # 预检请求处理
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin "https://servicewechat.com";
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Authorization, Content-Type, X-Requested-With";
            add_header Access-Control-Allow-Credentials true;
            add_header Access-Control-Max-Age 1728000;
            add_header Content-Type text/plain;
            add_header Content-Length 0;
            return 204;
        }
    }
    
    # 健康检查
    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
    
    # API文档 (可选，生产环境建议注释)
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 阻止访问敏感文件
    location ~ /\. {
        deny all;
    }
    
    location ~ \.(env|log|conf)$ {
        deny all;
    }
    
    # 日志
    error_log /var/log/nginx/talkai_error.log warn;
    access_log /var/log/nginx/talkai_access.log combined;
}

# HTTPS配置 (如果有SSL证书)
# server {
#     listen 443 ssl http2;
#     server_name your-domain.com api.your-domain.com;
#     
#     ssl_certificate /path/to/your/certificate.crt;
#     ssl_certificate_key /path/to/your/private.key;
#     
#     # SSL安全配置
#     ssl_protocols TLSv1.2 TLSv1.3;
#     ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-RSA-AES128-GCM-SHA256;
#     ssl_prefer_server_ciphers off;
#     ssl_session_cache shared:SSL:10m;
#     ssl_session_timeout 10m;
#     
#     # 其他location配置与HTTP相同...
# }
EOF
```

### 4.2 启用Nginx配置

```bash
# 启用站点配置
sudo ln -sf /etc/nginx/sites-available/talkai /etc/nginx/sites-enabled/

# 测试Nginx配置
sudo nginx -t

# 如果测试通过，重新加载Nginx
sudo systemctl reload nginx
```

## 5. 启动服务

### 5.1 启动系统服务

```bash
# 重新加载systemd配置
sudo systemctl daemon-reload

# 启用并启动TalkAI服务
sudo systemctl enable talkai
sudo systemctl start talkai

# 检查服务状态
sudo systemctl status talkai

# 查看日志
sudo journalctl -u talkai -f
```

### 5.2 检查Redis服务

```bash
# 检查Redis状态
sudo systemctl status redis
# 或者 (Ubuntu)
sudo systemctl status redis-server

# 测试Redis连接
redis-cli ping
```

## 6. 验证部署

### 6.1 健康检查

```bash
# 本地健康检查
curl http://localhost:8000/health

# 通过Nginx检查
curl http://your-domain.com/health
```

### 6.2 API测试

```bash
# 测试API文档
curl http://your-domain.com/docs

# 测试字典查询 (如果有词典数据库)
curl "http://your-domain.com/api/v1/dict/query?word=hello"
```

## 7. 维护命令

### 7.1 常用管理命令

```bash
# 查看服务状态
sudo systemctl status talkai

# 重启服务
sudo systemctl restart talkai

# 停止服务
sudo systemctl stop talkai

# 查看实时日志
sudo journalctl -u talkai -f

# 查看应用日志
tail -f /www/wwwroot/talkai/backend/logs/app.log

# 查看访问日志
sudo tail -f /var/log/nginx/talkai_access.log
```

### 7.2 数据备份

```bash
# 备份数据库
cp /www/wwwroot/talkai/backend/data/db/talkai.db /backup/talkai_$(date +%Y%m%d).db

# 备份配置文件
cp /www/wwwroot/talkai/backend/.env /backup/talkai_env_$(date +%Y%m%d).backup
```

## 8. 故障排查

### 8.1 常见问题

1. **服务启动失败**
   ```bash
   # 检查Python环境
   /www/wwwroot/talkai/backend/venv/bin/python --version
   
   # 检查依赖安装
   /www/wwwroot/talkai/backend/venv/bin/pip list
   
   # 手动启动测试
   cd /www/wwwroot/talkai/backend
   source venv/bin/activate
   python main.py
   ```

2. **Redis连接失败**
   ```bash
   # 检查Redis状态
   sudo systemctl status redis
   
   # 检查Redis配置
   redis-cli ping
   
   # 查看Redis日志
   sudo journalctl -u redis -f
   ```

3. **数据库问题**
   ```bash
   # 检查数据库文件权限
   ls -la /www/wwwroot/talkai/backend/data/db/
   
   # 手动创建数据库表
   cd /www/wwwroot/talkai/backend
   source venv/bin/activate
   python -c "from app.core.database import create_tables; create_tables()"
   ```

4. **Nginx配置问题**
   ```bash
   # 测试Nginx配置
   sudo nginx -t
   
   # 查看Nginx错误日志
   sudo tail -f /var/log/nginx/error.log
   
   # 检查端口占用
   sudo netstat -tlnp | grep :8000
   ```

### 8.2 性能优化

1. **调整worker数量**
   - 编辑 `/www/wwwroot/talkai/backend/gunicorn.conf.py`
   - 根据CPU核心数调整 `workers` 参数

2. **数据库优化**
   ```bash
   # 如果使用PostgreSQL替代SQLite
   pip install psycopg2-binary
   # 在.env中修改DATABASE_URL
   ```

3. **缓存优化**
   ```bash
   # 调整Redis内存设置
   sudo vim /etc/redis/redis.conf
   # 设置maxmemory和maxmemory-policy
   ```

## 9. 安全建议

1. **防火墙设置**
   ```bash
   # 只开放必要端口
   sudo ufw allow 22    # SSH
   sudo ufw allow 80    # HTTP
   sudo ufw allow 443   # HTTPS
   sudo ufw enable
   ```

2. **SSL证书配置**
   - 使用Let's Encrypt获取免费SSL证书
   - 或购买商业SSL证书

3. **定期更新**
   ```bash
   # 定期更新系统和依赖
   sudo yum update -y  # 或 sudo apt update && sudo apt upgrade -y
   pip install --upgrade -r requirements.txt
   ```

4. **备份策略**
   - 设置定时备份数据库和配置文件
   - 使用`crontab -e`创建定时任务

---

## 配置文件模板

完成部署后，记得：
1. 修改 `.env` 文件中的API密钥
2. 更新Nginx配置中的域名
3. 配置SSL证书（生产环境）
4. 设置定期备份
5. 监控服务运行状态

如有问题，请查看日志文件：
- 应用日志: `/www/wwwroot/talkai/backend/logs/app.log`
- 系统日志: `sudo journalctl -u talkai`
- Nginx日志: `/var/log/nginx/talkai_error.log`