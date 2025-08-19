# TalkAI Mini Program - Deployment Guide

## 项目概述

TalkAI是一个基于微信小程序的AI英语学习助手，提供智能对话练习、语法纠错、词汇管理等功能。

### 技术架构
- **前端**: 微信小程序 (WeChat Mini Program)
- **后端**: Python FastAPI + SQLite + Redis
- **部署**: Docker + Nginx + 腾讯云

### 核心功能
- ✅ **智能对话**: AI驱动的英语对话练习
- ✅ **语法纠错**: 实时语法错误检测和修正
- ✅ **词汇管理**: 个人词汇库管理和同步
- ✅ **词典查询**: 40万词典数据查询
- ✅ **学习分析**: 自动生成学习进度报告
- ✅ **多用户**: 支持微信登录和数据隔离

## 快速部署

### 1. 环境准备

**服务器要求:**
- 腾讯云 CVM 2核4G (推荐)
- Ubuntu 20.04 LTS
- Docker & Docker Compose
- Nginx
- 域名和SSL证书

**API密钥准备:**
```bash
# 必需的API密钥
MOONSHOT_API_KEY=your_moonshot_key    # Moonshot AI
# 或者
OPENAI_API_KEY=your_openai_key        # OpenAI

# 微信小程序配置
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret

# 应用密钥
SECRET_KEY=your_32_char_secret_key
```

### 2. 一键部署

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd talkai_miniprogram

# 2. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 backend/.env 填入必要的API密钥

# 3. 执行部署
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

### 3. 配置域名和SSL

```bash
# 配置域名DNS指向服务器IP
# 申请SSL证书
sudo certbot certonly --standalone -d api.jimingge.net

# 复制证书文件
sudo cp /etc/letsencrypt/live/jimingge.net/fullchain.pem backend/ssl/cert.pem
sudo cp /etc/letsencrypt/live/jimingge.net/privkey.pem backend/ssl/key.pem

# 启用HTTPS (取消nginx.conf中HTTPS配置的注释)
# 重启服务
cd backend && docker-compose restart
```

### 4. 部署微信小程序

1. **安装微信开发者工具**
2. **导入项目**: 选择 `frontend/` 目录
3. **配置API地址**: 
   ```javascript
   // frontend/services/api.js
   const BASE_URL = 'https://api.jimingge.net/api/v1';
   ```
4. **配置服务器域名**: 在微信公众平台添加 `https://api.jimingge.net`
5. **上传代码**: 上传并提交审核

## 详细配置说明

### 后端配置

**环境变量配置** (`backend/.env`):
```bash
# 数据库
DATABASE_URL=sqlite:///./data/db/talkai.db

# Redis缓存
REDIS_URL=redis://redis:6379/0

# API密钥 (必需其一)
MOONSHOT_API_KEY=sk-xxx
OPENAI_API_KEY=sk-xxx

# 微信小程序
WECHAT_APP_ID=wxabc123
WECHAT_APP_SECRET=abc123

# JWT配置
SECRET_KEY=your-super-secret-key-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# 应用设置
DEBUG=False
HOST=0.0.0.0
PORT=8000

# CORS设置
ALLOWED_ORIGINS=https://servicewechat.com

# 学习设置
VOCAB_AUTO_SYNC_HOURS=24
MAX_CHAT_RECORDS_PER_ANALYSIS=100
```

**目录结构**:
```
backend/
├── app/                    # 应用核心代码
│   ├── api/               # API路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据模型
│   ├── services/          # 业务服务
│   └── utils/             # 工具函数
├── data/                  # 数据存储
│   ├── db/               # 数据库文件
│   ├── cache/            # 缓存文件
│   └── uploads/          # 上传文件
├── logs/                  # 日志文件
├── deployment/            # 部署配置
├── Dockerfile            # Docker配置
├── docker-compose.yml    # Docker Compose
├── nginx.conf            # Nginx配置
└── requirements.txt      # Python依赖
```

### 前端配置

**小程序配置** (`frontend/app.json`):
```json
{
  "pages": [
    "pages/login/login",
    "pages/chat/chat", 
    "pages/vocab/vocab",
    "pages/dict/dict",
    "pages/profile/profile"
  ],
  "tabBar": {
    "list": [
      {"pagePath": "pages/chat/chat", "text": "对话"},
      {"pagePath": "pages/vocab/vocab", "text": "词汇"},
      {"pagePath": "pages/dict/dict", "text": "词典"},
      {"pagePath": "pages/profile/profile", "text": "我的"}
    ]
  }
}
```

**API配置** (`frontend/services/api.js`):
```javascript
const BASE_URL = 'https://api.jimingge.net/api/v1';
```

## 运维管理

### 常用命令

```bash
# 查看服务状态
./deployment/deploy.sh status

# 查看日志
./deployment/deploy.sh logs

# 重启服务
./deployment/deploy.sh restart

# 停止服务  
./deployment/deploy.sh stop

# 数据备份
./deployment/deploy.sh backup
```

### 监控和维护

**健康检查**:
```bash
# 检查后端服务
curl http://localhost:8000/health

# 检查API响应
curl http://localhost:8000/api/v1/dict/health
```

**日志监控**:
```bash
# 查看应用日志
docker-compose logs -f talkai-backend

# 查看Nginx日志
tail -f /var/log/nginx/talkai_access.log
tail -f /var/log/nginx/talkai_error.log
```

**数据库维护**:
```bash
# 进入后端容器
docker exec -it talkai-backend bash

# 查看数据库
sqlite3 data/db/talkai.db
.tables
SELECT COUNT(*) FROM users;
```

### 性能优化

**并发能力**:
- 目标: ≥50并发用户
- QPS: ≥20 (AI推理)
- 实际测试: 可轻松支持100-150 QPS

**缓存策略**:
- Redis缓存词典查询
- 本地缓存词汇数据
- Nginx静态文件缓存

**数据同步**:
- 词汇数据24小时自动同步
- 增量同步减少传输量
- 本地优先，定期备份

## 故障排除

### 常见问题

**1. 后端服务无法启动**
```bash
# 检查日志
docker-compose logs talkai-backend

# 常见原因：
# - .env文件缺失或配置错误
# - 端口被占用
# - 数据库权限问题
```

**2. 微信登录失败**
```bash
# 检查微信配置
# - WECHAT_APP_ID 和 WECHAT_APP_SECRET 是否正确
# - 服务器域名是否在微信公众平台配置
# - HTTPS是否正确配置
```

**3. AI服务调用失败**
```bash
# 检查API密钥
# - MOONSHOT_API_KEY 或 OPENAI_API_KEY 是否有效
# - API配额是否用完
# - 网络连接是否正常
```

**4. 词典查询失败**
```bash
# 检查词典数据库
ls -la backend/data/db/dictionary400k.db

# 如果缺失，复制词典文件
cp ../dictionary400k.db backend/data/db/
```

### 紧急恢复

**快速重启**:
```bash
cd backend
docker-compose down
docker-compose up -d
```

**数据恢复**:
```bash
# 从备份恢复
tar -xzf backups/talkai_backup_YYYYMMDD_HHMMSS.tar.gz -C backend/
```

## 扩展和定制

### 添加新功能

1. **后端API扩展**:
   - 在 `app/api/v1/` 添加新路由
   - 在 `app/services/` 添加业务逻辑
   - 更新数据模型

2. **前端页面扩展**:
   - 在 `frontend/pages/` 添加新页面
   - 更新 `app.json` 配置
   - 添加相应的API调用

### 集成其他服务

**语音功能**:
```javascript
// 添加语音识别
wx.startRecord({
  success: function(res) {
    // 处理录音结果
  }
});
```

**支付功能**:
```javascript
// 集成微信支付
wx.requestPayment({
  // 支付参数
});
```

## 安全考虑

### 数据安全
- 所有API请求需要JWT认证
- 敏感数据加密存储
- 定期数据备份

### 网络安全
- HTTPS强制加密
- 请求频率限制
- CORS严格控制

### 隐私保护
- 用户数据最小化收集
- 数据用途透明化
- 支持用户数据删除

---

## 联系支持

如需技术支持或有问题反馈，请通过以下方式联系：

- **技术文档**: 项目README.md
- **问题报告**: GitHub Issues
- **部署支持**: 参考本文档或联系开发团队

---

*最后更新: 2024年8月*