# TalkAI 故障排除手册

## 📋 概述

本手册整合了TalkAI部署和运行过程中可能遇到的各种问题及解决方案。

---

## 🚨 快速诊断

### 问题排查顺序
1. **基础环境检查** - 确认服务器环境和依赖
2. **配置文件验证** - 检查环境变量和配置
3. **服务状态诊断** - 查看容器和进程状态
4. **日志分析** - 分析错误日志信息
5. **网络连通性** - 测试API和网络访问
6. **数据库检查** - 验证数据存储状态

### 自助诊断脚本
```bash
# 快速诊断命令
./deployment/deploy-existing-server.sh --check-only

# 查看服务状态
./deployment/deploy-existing-server.sh --status

# 查看详细信息
./deployment/deploy-existing-server.sh --info
```

---

## 🔧 部署阶段问题

### 1. 环境检查失败

#### 问题：Docker未安装或版本过低
**症状:**
```
Docker未安装，请先安装Docker
```

**解决方案:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 添加用户到docker组
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker-compose --version
```

#### 问题：Nginx未运行
**症状:**
```
Nginx服务未运行，请启动Nginx
```

**解决方案:**
```bash
# 检查Nginx状态
sudo systemctl status nginx

# 启动Nginx
sudo systemctl start nginx

# 设置开机自启
sudo systemctl enable nginx

# 如果Nginx未安装
sudo apt install nginx
```

#### 问题：端口被占用
**症状:**
```
端口 8001 已被占用，无法启动 TalkAI后端
```

**解决方案:**
```bash
# 查看端口占用
sudo netstat -tlnp | grep 8001
sudo lsof -i :8001

# 终止占用进程
sudo kill -9 <PID>

# 或修改端口配置
vim backend/docker-compose.yml
# 将 "8001:8000" 改为 "8002:8000"
```

### 2. 配置文件问题

#### 问题：.env文件缺失或格式错误
**症状:**
```
配置文件加载失败
Environment variable not found
```

**解决方案:**
```bash
# 检查.env文件
ls -la backend/.env

# 如果不存在，复制模板
cp backend/.env.example backend/.env

# 检查文件格式
cat backend/.env | grep -E "^[A-Z_]+=.*$"

# 确保没有空格和特殊字符
sed -i 's/ = /=/g' backend/.env
```

#### 问题：API密钥无效
**症状:**
```
API调用失败: 401 Unauthorized
Invalid API key provided
```

**解决方案:**
```bash
# 验证API密钥格式
grep "API_KEY" backend/.env

# Moonshot密钥应以 sk- 开头
# OpenAI密钥应以 sk- 开头

# 测试API密钥有效性
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.moonshot.cn/v1/models"
```

---

## 🐳 Docker相关问题

### 1. 容器启动失败

#### 问题：镜像构建失败
**症状:**
```bash
docker-compose build
# ERROR: failed to build
```

**解决方案:**
```bash
# 清理Docker缓存
docker system prune -a

# 重新构建
docker-compose build --no-cache

# 查看构建日志
docker-compose build --progress=plain

# 检查Dockerfile语法
docker build . -f backend/Dockerfile
```

#### 问题：容器启动后立即退出
**症状:**
```bash
docker-compose ps
# STATUS: Exited (1)
```

**解决方案:**
```bash
# 查看容器日志
docker-compose logs talkai-backend

# 常见原因和解决：
# 1. 环境变量缺失 - 检查.env文件
# 2. 端口冲突 - 修改端口映射
# 3. 权限问题 - 检查文件权限

# 交互式进入容器调试
docker-compose run --rm talkai-backend bash
```

### 2. 容器连接问题

#### 问题：Redis连接失败
**症状:**
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案:**
```bash
# 检查Redis容器状态
docker-compose ps redis

# 检查网络连接
docker-compose exec talkai-backend ping talkai-redis

# 重启Redis容器
docker-compose restart talkai-redis

# 检查Redis配置
docker-compose logs talkai-redis
```

---

## 🌐 网络和SSL问题

### 1. SSL证书问题

#### 问题：证书文件不存在
**症状:**
```
SSL证书不存在，将只配置HTTP
nginx: [error] SSL certificate not found
```

**解决方案:**
```bash
# 检查证书文件
ls -la /etc/letsencrypt/live/jimingge.net/

# 申请新证书
sudo certbot --nginx -d api.jimingge.net

# 或手动指定证书路径
sudo certbot certonly --standalone -d api.jimingge.net
```

#### 问题：证书权限错误
**症状:**
```
nginx: [error] SSL_CTX_use_certificate_chain_file() failed
Permission denied
```

**解决方案:**
```bash
# 检查证书权限
sudo ls -la /etc/letsencrypt/live/jimingge.net/

# 修复权限
sudo chown root:root /etc/letsencrypt/live/jimingge.net/*
sudo chmod 644 /etc/letsencrypt/live/jimingge.net/fullchain.pem
sudo chmod 600 /etc/letsencrypt/live/jimingge.net/privkey.pem
```

### 2. 域名解析问题

#### 问题：域名无法解析
**症状:**
```bash
curl: (6) Could not resolve host: api.jimingge.net
```

**解决方案:**
```bash
# 检查DNS解析
nslookup api.jimingge.net
dig api.jimingge.net

# 检查DNS服务器
cat /etc/resolv.conf

# 更换DNS服务器
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# 检查hosts文件
grep jimingge /etc/hosts
```

---

## 🗄️ 数据库相关问题

### 1. SQLite数据库问题

#### 问题：数据库文件权限错误
**症状:**
```
sqlite3.OperationalError: unable to open database file
Permission denied
```

**解决方案:**
```bash
# 检查数据库文件权限
ls -la backend/data/db/

# 修复权限
sudo chown -R $USER:$USER backend/data/
chmod -R 755 backend/data/

# 确保目录存在
mkdir -p backend/data/db
```

#### 问题：词典数据库缺失
**症状:**
```
Dictionary database not found: dictionary400k.db
```

**解决方案:**
```bash
# 检查词典文件
ls -la backend/data/db/dictionary400k.db

# 从备份复制
cp /path/to/backup/dictionary400k.db backend/data/db/

# 或下载词典文件
wget -O backend/data/db/dictionary400k.db "https://your-backup-url/dictionary400k.db"

# 验证文件完整性
file backend/data/db/dictionary400k.db
```

### 2. 数据库连接问题

#### 问题：数据库锁定
**症状:**
```
sqlite3.OperationalError: database is locked
```

**解决方案:**
```bash
# 查看数据库进程
fuser backend/data/db/talkai.db

# 重启应用服务
docker-compose restart talkai-backend

# 如果持续锁定，备份并重建
cp backend/data/db/talkai.db backend/data/db/talkai.db.backup
sqlite3 backend/data/db/talkai.db ".backup backup.db"
mv backup.db backend/data/db/talkai.db
```

---

## 🔌 API调用问题

### 1. 认证相关问题

#### 问题：JWT Token无效
**症状:**
```json
{"detail": "Could not validate credentials"}
```

**解决方案:**
```bash
# 检查JWT配置
grep SECRET_KEY backend/.env

# 确保SECRET_KEY足够安全（32字符以上）
python3 -c "import secrets; print(secrets.token_hex(16))"

# 重新生成Token
curl -X POST http://localhost:8001/api/v1/auth/wechat/login \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code"}'
```

#### 问题：微信登录失败
**症状:**
```json
{"detail": "WeChat login failed"}
```

**解决方案:**
```bash
# 检查微信配置
grep WECHAT backend/.env

# 确认AppID和AppSecret正确
# 检查微信API连通性
curl "https://api.weixin.qq.com/sns/jscode2session?appid=YOUR_APPID&secret=YOUR_SECRET&js_code=test&grant_type=authorization_code"
```

### 2. AI服务问题

#### 问题：AI API调用失败
**症状:**
```
OpenAI API error: Rate limit exceeded
Moonshot API error: Insufficient quota
```

**解决方案:**
```bash
# 检查API配额
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.moonshot.cn/v1/models"

# 切换API提供商
# 在.env中注释当前API_KEY，启用另一个

# 实现请求重试机制
# 检查app/services/ai.py中的重试逻辑
```

---

## 📱 微信小程序问题

### 1. 小程序无法连接API

#### 问题：请求域名不合法
**症状:**
```
request:fail url not in domain list
```

**解决方案:**
```bash
# 在微信公众平台配置服务器域名
# 开发管理 -> 开发设置 -> 服务器域名
# 添加: https://api.jimingge.net

# 检查域名HTTPS可访问性
curl https://api.jimingge.net/health

# 确保域名已备案
```

#### 问题：HTTPS证书问题
**症状:**
```
request:fail ssl handshake error
```

**解决方案:**
```bash
# 检查SSL证书有效性
openssl s_client -connect api.jimingge.net:443 -servername api.jimingge.net

# 更新证书
sudo certbot renew

# 检查证书链完整性
curl -I https://api.jimingge.net
```

### 2. API调用问题

#### 问题：跨域请求失败
**症状:**
```
Access to XMLHttpRequest blocked by CORS policy
```

**解决方案:**
```bash
# 检查CORS配置
grep ALLOWED_ORIGINS backend/.env

# 确保包含微信域名
# ALLOWED_ORIGINS=https://servicewechat.com,https://api.jimingge.net

# 重启服务
docker-compose restart talkai-backend
```

---

## 🔍 日志分析

### 1. 主要日志文件位置

```bash
# 部署日志
/tmp/talkai-deploy.log

# 应用日志
backend/logs/app.log

# Docker容器日志
docker-compose logs -f talkai-backend
docker-compose logs -f talkai-redis

# Nginx日志
/var/log/nginx/talkai_access.log
/var/log/nginx/talkai_error.log
/var/log/nginx/error.log

# 系统日志
/var/log/syslog
journalctl -u docker
```

### 2. 日志分析命令

```bash
# 查看最新错误
tail -f /var/log/nginx/talkai_error.log

# 分析访问模式
tail -f /var/log/nginx/talkai_access.log | grep -E "(POST|GET)"

# 查看API错误
docker-compose logs talkai-backend | grep -i error

# 分析性能问题
docker-compose logs talkai-backend | grep -i "slow\|timeout"

# 查看内存使用
docker stats talkai-backend
```

---

## 🚨 紧急恢复

### 1. 服务快速重启

```bash
# 完全重启所有服务
docker-compose down
docker-compose up -d

# 仅重启后端服务
docker-compose restart talkai-backend

# 重载Nginx配置
sudo nginx -t && sudo systemctl reload nginx
```

### 2. 数据恢复

#### 从备份恢复数据
```bash
# 停止服务
docker-compose down

# 恢复数据库
cp backup/talkai.db backend/data/db/talkai.db

# 恢复词典
cp backup/dictionary400k.db backend/data/db/dictionary400k.db

# 重启服务
docker-compose up -d
```

#### 重置到初始状态
```bash
# 停止所有服务
docker-compose down

# 清理数据（谨慎操作）
rm -rf backend/data/db/talkai.db
rm -rf backend/logs/*

# 重新部署
./deployment/deploy-existing-server.sh --auto
```

### 3. 回滚部署

```bash
# 停止当前服务
docker-compose down

# 删除当前部署
sudo rm -rf /www/wwwroot/talkai_miniprogram

# 删除Nginx配置
sudo rm -f /etc/nginx/sites-enabled/talkai-api
sudo rm -f /etc/nginx/sites-available/talkai-api

# 重载Nginx
sudo systemctl reload nginx

# 从备份恢复（如果有）
tar -xzf backup/talkai_backup_YYYYMMDD.tar.gz -C /www/wwwroot/
```

---

## 📊 性能问题诊断

### 1. 系统资源检查

```bash
# CPU使用率
top
htop

# 内存使用情况
free -h
docker stats

# 磁盘使用情况
df -h
du -sh backend/data/

# 网络连接
ss -tlnp | grep -E ':(8001|6380)'
```

### 2. 应用性能分析

```bash
# API响应时间测试
curl -w "@curl-format.txt" https://api.jimingge.net/health

# 数据库查询性能
sqlite3 backend/data/db/talkai.db "EXPLAIN QUERY PLAN SELECT * FROM users LIMIT 10;"

# Redis性能检查
docker-compose exec talkai-redis redis-cli info memory
docker-compose exec talkai-redis redis-cli slowlog get 10
```

### 3. 并发测试

```bash
# 简单并发测试
ab -n 100 -c 10 https://api.jimingge.net/health

# 使用wrk进行压力测试
wrk -t12 -c400 -d30s https://api.jimingge.net/health
```

---

## 📋 故障排除检查清单

### 部署前检查
- [ ] 服务器配置满足要求 (2核4G)
- [ ] Docker和Docker Compose已安装
- [ ] Nginx运行正常
- [ ] 域名DNS解析正确
- [ ] 端口8001和6380未被占用
- [ ] 磁盘空间充足 (>10GB)
- [ ] SSL证书有效

### 配置检查
- [ ] .env文件存在且格式正确
- [ ] API密钥有效且有足够配额
- [ ] 微信小程序配置正确
- [ ] 数据库文件存在且可访问
- [ ] 词典文件已复制

### 服务状态检查
- [ ] Docker容器运行正常
- [ ] 健康检查通过
- [ ] Nginx配置生效
- [ ] HTTPS访问正常
- [ ] API调用成功
- [ ] 数据库连接正常
- [ ] Redis缓存工作

### 微信小程序检查
- [ ] 服务器域名已配置
- [ ] API地址正确
- [ ] 登录功能正常
- [ ] 各页面功能正常

---

## 📞 获取更多帮助

### 自助排查资源
1. **配置参考**: [CONFIG_REFERENCE.md](./CONFIG_REFERENCE.md)
2. **部署文档**: [README.md](./README.md)
3. **日志分析**: 查看上述日志文件位置

### 诊断信息收集
在寻求帮助时，请提供以下信息：
```bash
# 系统信息
uname -a
docker --version
docker-compose --version

# 服务状态
./deployment/deploy-existing-server.sh --status

# 错误日志 (最近50行)
tail -50 /tmp/talkai-deploy.log
docker-compose logs --tail=50 talkai-backend

# 配置信息 (隐藏敏感信息)
grep -v "KEY\|SECRET" backend/.env
```

---

**记住: 大部分问题都可以通过仔细检查配置和日志来解决。保持冷静，逐步排查！** 🔧