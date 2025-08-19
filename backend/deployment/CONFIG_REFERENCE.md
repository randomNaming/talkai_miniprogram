# TalkAI 配置参考手册

## 📋 配置概览

本文档包含TalkAI部署和运行所需的所有配置说明，适用于所有部署方式。

---

## 🔧 环境变量配置

### 核心配置文件
主要配置文件位置：`backend/.env`

```bash
# TalkAI 环境配置文件
# 请根据实际情况修改以下配置

# =================================
#           数据库配置
# =================================

# SQLite数据库路径
DATABASE_URL=sqlite:///./data/db/talkai.db

# =================================
#           Redis缓存配置
# =================================

# Redis连接URL
REDIS_URL=redis://talkai-redis:6379/0

# =================================
#           AI API配置 (必需其一)
# =================================

# Moonshot AI API密钥 (推荐)
MOONSHOT_API_KEY=sk-your-moonshot-api-key-here

# 或者使用 OpenAI API密钥
# OPENAI_API_KEY=sk-your-openai-api-key-here

# 模型提供商 (自动检测，无需手动设置)
# MODEL_PROVIDER=moonshot  # 或 openai

# =================================
#           微信小程序配置
# =================================

# 微信小程序AppID
WECHAT_APP_ID=wx1234567890abcdef

# 微信小程序AppSecret
WECHAT_APP_SECRET=your-wechat-app-secret-here

# =================================
#           安全配置
# =================================

# JWT密钥 (请使用32字符以上的安全密钥)
SECRET_KEY=your-super-secure-32-character-secret-key-here

# JWT算法
ALGORITHM=HS256

# Token过期时间 (分钟)
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# =================================
#           应用配置
# =================================

# 调试模式 (生产环境请设置为False)
DEBUG=False

# 服务监听地址
HOST=0.0.0.0

# 服务端口
PORT=8000

# =================================
#           跨域配置 (CORS)
# =================================

# 允许的源地址
ALLOWED_ORIGINS=https://servicewechat.com,https://api.jimingge.net

# =================================
#           性能配置
# =================================

# 学习分析时最大聊天记录数
MAX_CHAT_RECORDS_PER_ANALYSIS=100

# 词汇自动同步间隔 (小时)
VOCAB_AUTO_SYNC_HOURS=24

# API速率限制 - 每分钟请求数
RATE_LIMIT_REQUESTS=100

# 速率限制窗口 (秒)
RATE_LIMIT_WINDOW=60

# =================================
#           日志配置
# =================================

# 日志级别 (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# 日志文件路径
LOG_FILE=./logs/app.log
```

---

## 🔑 API密钥获取指南

### 1. Moonshot AI API密钥 (推荐)

**获取步骤:**
1. 访问 [Moonshot AI 官网](https://platform.moonshot.cn/)
2. 注册账号并完成实名认证
3. 进入控制台，创建新的API密钥
4. 复制API密钥，格式类似：`sk-xxxxxxxxxxxxxxxxxxxxx`

**优势:**
- 中文支持更好
- 响应速度快
- 成本相对较低

**配置:**
```bash
MOONSHOT_API_KEY=sk-your-moonshot-api-key
```

### 2. OpenAI API密钥 (备选)

**获取步骤:**
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册账号并绑定付费方式
3. 创建API密钥
4. 复制API密钥，格式类似：`sk-xxxxxxxxxxxxxxxxxxxxx`

**配置:**
```bash
OPENAI_API_KEY=sk-your-openai-api-key
```

**注意事项:**
- 需要海外支付方式
- 可能需要代理访问
- 成本相对较高

---

## 📱 微信小程序配置

### 1. 获取微信小程序配置

**步骤:**
1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 选择"小程序" → "开发管理" → "开发设置"
3. 获取以下信息：
   - **AppID**: 小程序唯一标识符
   - **AppSecret**: 小程序密钥

**配置:**
```bash
WECHAT_APP_ID=wx1234567890abcdef
WECHAT_APP_SECRET=your-app-secret-here
```

### 2. 服务器域名配置

在微信公众平台配置服务器域名：

**位置:** 小程序后台 → 开发管理 → 开发设置 → 服务器域名

**配置内容:**
```
request合法域名: https://api.jimingge.net
uploadFile合法域名: https://api.jimingge.net
downloadFile合法域名: https://api.jimingge.net
```

**注意事项:**
- 域名必须支持HTTPS
- 域名必须已备案
- 不支持IP地址直接访问

---

## 🔒 SSL证书配置

### 1. 证书文件位置

**标准位置 (Let's Encrypt):**
```bash
# 证书文件
SSL_CERT_PATH=/etc/letsencrypt/live/jimingge.net/fullchain.pem

# 私钥文件
SSL_KEY_PATH=/etc/letsencrypt/live/jimingge.net/privkey.pem
```

**自定义位置:**
```bash
# 可以放在任何位置，只要Nginx可以访问
SSL_CERT_PATH=/path/to/your/cert.pem
SSL_KEY_PATH=/path/to/your/key.pem
```

### 2. 申请免费SSL证书

**使用Certbot (推荐):**
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 为域名申请证书
sudo certbot --nginx -d jimingge.net -d api.jimingge.net

# 或者使用DNS验证
sudo certbot certonly --manual --preferred-challenges dns -d jimingge.net -d api.jimingge.net
```

**证书续期:**
```bash
# 测试续期
sudo certbot renew --dry-run

# 设置自动续期
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

---

## 🗄️ 数据库配置

### 1. SQLite配置 (默认)

**优势:**
- 无需额外安装
- 配置简单
- 适合中小型应用

**配置:**
```bash
DATABASE_URL=sqlite:///./data/db/talkai.db
```

**文件位置:**
```
backend/data/db/
├── talkai.db          # 主数据库
└── dictionary400k.db  # 词典数据库
```

### 2. 词典数据库

**文件要求:**
- 文件名：`dictionary400k.db`
- 位置：`backend/data/db/dictionary400k.db`
- 大小：约100MB

**获取方式:**
1. 从原桌面版应用复制
2. 使用提供的词典数据文件
3. 确保文件权限正确

---

## 🚦 端口配置

### 默认端口分配

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| TalkAI Backend | 8000 | 8001 | 主应用服务 |
| Redis | 6379 | 6380 | 缓存服务 |
| Nginx | 80/443 | 80/443 | 反向代理 |

### 端口冲突处理

**检查端口占用:**
```bash
# 检查指定端口
sudo netstat -tlnp | grep :8001
sudo lsof -i :8001

# 检查所有TalkAI端口
sudo netstat -tlnp | grep -E ':(8001|6380)'
```

**修改端口:**
如果端口被占用，可修改`docker-compose.yml`：
```yaml
services:
  talkai-backend:
    ports:
      - "8002:8000"  # 修改外部端口为8002
  
  talkai-redis:
    ports:
      - "6381:6379"  # 修改外部端口为6381
```

---

## 🛡️ 安全配置

### 1. JWT密钥生成

**生成安全密钥:**
```bash
# 方法1: 使用openssl
openssl rand -hex 16

# 方法2: 使用Python
python3 -c "import secrets; print(secrets.token_hex(16))"

# 方法3: 使用uuid
python3 -c "import uuid; print(str(uuid.uuid4()).replace('-', ''))"
```

### 2. 环境变量安全

**保护.env文件:**
```bash
# 设置文件权限
chmod 600 backend/.env

# 确保不被版本控制
echo "backend/.env" >> .gitignore
```

**生产环境建议:**
- 使用环境变量而非文件存储敏感信息
- 定期轮换API密钥
- 监控异常访问

---

## 📊 性能优化配置

### 1. Redis缓存优化

**内存限制:**
```bash
# 在docker-compose.yml中配置Redis
command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
```

**缓存策略:**
- `allkeys-lru`: 删除最近最少使用的key
- `allkeys-lfu`: 删除最不经常使用的key
- `volatile-ttl`: 删除即将过期的key

### 2. 应用性能配置

**并发设置:**
```bash
# 工作进程数 (建议为CPU核心数)
WORKERS=2

# 每个进程的线程数
THREADS=4

# 请求超时时间
TIMEOUT=30
```

**资源限制:**
```bash
# 最大上传文件大小
MAX_UPLOAD_SIZE=10MB

# 请求体大小限制
MAX_REQUEST_SIZE=10MB
```

---

## 🔍 配置验证

### 1. 配置文件检查

**验证.env文件:**
```bash
# 检查文件存在
ls -la backend/.env

# 检查文件内容（隐藏敏感信息）
grep -v "KEY\|SECRET" backend/.env
```

### 2. 服务连通性测试

**API连接测试:**
```bash
# 健康检查
curl http://localhost:8001/health

# 词典API测试
curl "http://localhost:8001/api/v1/dict/query?word=hello"

# 认证API测试
curl -X POST http://localhost:8001/api/v1/auth/wechat/login \
  -H "Content-Type: application/json" \
  -d '{"code": "test_code"}'
```

**数据库连接测试:**
```bash
# 检查数据库文件
ls -la backend/data/db/

# 检查数据库表
sqlite3 backend/data/db/talkai.db ".tables"
```

---

## 📝 配置模板

### 完整.env模板

```bash
# =================================
#         TalkAI 环境配置
# =================================

# 数据库
DATABASE_URL=sqlite:///./data/db/talkai.db
REDIS_URL=redis://talkai-redis:6379/0

# AI API (必需其一)
MOONSHOT_API_KEY=sk-your-moonshot-key-here
# OPENAI_API_KEY=sk-your-openai-key-here

# 微信小程序
WECHAT_APP_ID=wx1234567890abcdef
WECHAT_APP_SECRET=your-wechat-app-secret

# 安全配置
SECRET_KEY=your-32-character-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用配置
DEBUG=False
HOST=0.0.0.0
PORT=8000

# CORS配置
ALLOWED_ORIGINS=https://servicewechat.com,https://api.jimingge.net

# 性能配置
MAX_CHAT_RECORDS_PER_ANALYSIS=100
VOCAB_AUTO_SYNC_HOURS=24
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

---

## 🆘 配置问题排查

### 常见配置错误

1. **API密钥无效**
   - 检查密钥格式是否正确
   - 确认密钥未过期
   - 验证账户余额充足

2. **微信配置错误**
   - 确认AppID和AppSecret匹配
   - 检查服务器域名配置
   - 验证HTTPS证书有效

3. **数据库连接失败**
   - 检查数据库文件权限
   - 确认路径正确
   - 验证磁盘空间充足

4. **端口冲突**
   - 使用netstat检查端口占用
   - 修改docker-compose.yml端口映射
   - 重启相关服务

### 配置验证清单

- [ ] .env文件存在且权限正确
- [ ] 所有必需环境变量已配置
- [ ] API密钥有效且有足够配额
- [ ] 微信小程序配置正确
- [ ] 数据库文件存在且可访问
- [ ] 端口未被占用
- [ ] SSL证书有效
- [ ] 域名DNS解析正确

---

*配置如有疑问，请参考具体部署文档或故障排除手册*