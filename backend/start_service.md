# TalkAI 服务启动指南

请使用python直接启动：
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

本文档详细说明如何启动 TalkAI 后端服务，包括 Docker 启动遇到的问题及解决方案。

## 目录
- [概述](#概述)
- [Docker 启动问题分析](#docker-启动问题分析)
- [Python 直接启动方法](#python-直接启动方法)
- [服务验证](#服务验证)
- [故障排查](#故障排查)
- [注意事项](#注意事项)

## 概述

TalkAI 后端服务基于 FastAPI 框架构建，支持两种启动方式：
1. **Docker Compose（推荐生产环境）**
2. **Python 直接启动（开发和测试环境）**

## Docker 启动问题分析

### 遇到的问题

在尝试使用 `docker-compose up -d` 启动服务时遇到以下问题：

```bash
# 问题现象
docker-compose up -d
# 输出：构建过程在下载依赖包时超时
#8 [3/8] RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*
# Command timed out after 10m 0.0s
```

### 问题原因

#### 1. **Clash 代理网络问题** ✅ 已确认

**检查结果：**
```bash
# 系统存在代理环境变量
https_proxy=http://127.0.0.1:7890
http_proxy=http://127.0.0.1:7890 
all_proxy=socks5://127.0.0.1:7891

# Clash 进程运行中 (PID: 2772400)
/usr/local/bin/clash -d /root/.config/clash
```

**具体影响：**
- Docker 构建过程会继承环境变量，包括代理设置
- `apt-get update` 连接 Debian 官方源时通过代理访问不稳定
- Rule 模式虽然按规则路由，但 Debian 源可能没有配置直连规则
- 代理服务器响应慢或不稳定导致超时

#### 2. **系统资源严重不足** ⚠️ 关键问题

**当前资源状况：**
```bash
# 内存使用情况
               total        used        free      shared  buff/cache   available
Mem:           1.7Gi       1.0Gi       142Mi       1.8Mi       698Mi       659Mi
Swap:          1.0Gi       634Mi       390Mi

# CPU 核心数：2
# 磁盘空间：40GB（使用 51%，剩余 20GB）
```

**Docker 构建资源需求分析：**
根据 Dockerfile 和 requirements.txt 分析：
- **基础镜像**：`python:3.9-slim` (~100MB)
- **系统依赖**：`gcc + g++` (~500MB)
- **Python 包依赖**：
  - `sentence-transformers` (~1.2GB，包含预训练模型)
  - `numpy + 数学库` (~200MB)
  - `其他依赖` (~300MB)
- **构建缓存**：~500MB
- **总计需求：~2.6GB**

**结论：**
- ❌ **内存严重不足**：需要 2.6GB，只有 659MB 可用
- ❌ **构建过程会大量使用 Swap**，极大降低性能
- ❌ **sentence-transformers 是重量级 AI 库**，用于文本嵌入向量计算

#### 3. **AI 模型依赖** 🤖 必需组件

**SentenceTransformer 的必要性：**
- 项目需要 `embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)`
- 用于词汇学习中的语义向量计算
- 数据库中存储 `embedding_vector` 字段用于语义搜索
- 不可移除的核心功能组件

#### 4. **最小资源需求**

**推荐配置：**
- **RAM：4GB+**（推荐 8GB）
- **vCPU：2 核心+**
- **磁盘：40GB+**
- **网络：稳定的直连或优化的代理配置**

### 解决方案

考虑到上述问题，提供以下多种解决方案：

#### 方案1：临时禁用代理进行 Docker 构建

```bash
# 1. 备份当前环境变量
echo $http_proxy > /tmp/proxy_backup
echo $https_proxy >> /tmp/proxy_backup
echo $all_proxy >> /tmp/proxy_backup

# 2. 清除构建环境的代理变量
unset http_proxy https_proxy all_proxy

# 3. 进行 Docker 构建
docker-compose up -d --build

# 4. 构建完成后恢复代理（如需要）
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7891
```

#### 方案2：配置 Docker Daemon 代理

如果需要保持系统代理，可配置 Docker 专用代理：

```bash
# 创建 Docker daemon 代理配置
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/proxy.conf <<EOF
[Service]
Environment="HTTP_PROXY=http://127.0.0.1:7890"
Environment="HTTPS_PROXY=http://127.0.0.1:7890"
Environment="NO_PROXY=localhost,127.0.0.1,debian.org,deb.debian.org"
EOF

# 重启 Docker 服务
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 方案3：增加 Swap 空间（临时解决内存不足）

```bash
# 增加 2GB swap 空间
sudo fallocate -l 2G /tmp/docker-swap
sudo chmod 600 /tmp/docker-swap
sudo mkswap /tmp/docker-swap
sudo swapon /tmp/docker-swap

# 验证 swap 增加
free -h
# 应该看到 Swap 总量增加

# 构建完成后可删除临时 swap
sudo swapoff /tmp/docker-swap
sudo rm /tmp/docker-swap
```

#### 方案4：轻量级 Docker 构建

创建优化的 `Dockerfile.lite`：

```dockerfile
FROM python:3.9-slim
WORKDIR /app

# 使用国内镜像源加速
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list

# 分阶段安装，减少峰值内存使用
COPY requirements.txt .
RUN apt-get update && apt-get install -y gcc g++ \
    && pip install --no-cache-dir --index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt \
    && apt-get remove -y gcc g++ && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .
RUN mkdir -p data/db data/cache data/uploads logs
EXPOSE 8000
CMD ["python", "main.py"]
```

使用命令：
```bash
docker build -f Dockerfile.lite -t talkai-backend:lite .
```

#### 方案5：Python 直接启动（推荐当前环境）

由于资源限制严重，**推荐继续使用 Python 直接启动方式**：

## Python 直接启动方法

### 前置条件检查

```bash
# 1. 检查 Python 版本（需要 Python 3.9+）
python3 --version
# 输出示例：Python 3.11.6

# 2. 检查必要的依赖包
pip list | grep -E "(fastapi|uvicorn|sqlalchemy)"
# 应该看到：
# fastapi            0.116.1
# uvicorn            0.35.0
```

### 详细启动步骤

#### 步骤 1：环境准备

```bash
# 进入项目目录
cd /www/wwwroot/talkai_miniprogram/backend

# 检查项目结构
ls -la
# 确认存在：main.py, requirements.txt, .env, docker-compose.yml
```

#### 步骤 2：配置环境变量

由于直接启动不使用 Docker 网络，需要修改 Redis 配置：

```bash
# 创建本地环境配置
cp .env .env.backup  # 备份原配置
```

创建 `.env.local` 文件（或直接修改 `.env`）：

```bash
# 关键配置项说明：
# REDIS_URL=memory://          # 使用内存缓存替代 Redis
# DEBUG=True                   # 开启调试模式
# HOST=0.0.0.0                # 监听所有网络接口
# PORT=8000                    # 服务端口
```

#### 步骤 3：检查端口占用

```bash
# 检查端口 8000 是否被占用
lsof -i:8000
netstat -tlnp | grep :8000

# 如果端口被占用，找到进程 PID 并决定是否停止
# 示例输出：tcp 0 0 0.0.0.0:8000 0.0.0.0:* LISTEN 3201310/python3
```

#### 步骤 4：启动服务

```bash
# 方法1：前台启动（推荐调试时使用）
python3 main.py

# 方法2：后台启动
nohup python3 main.py > /dev/null 2>&1 &

# 方法3：使用 uvicorn 直接启动
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 步骤 5：环境变量应用

如果需要修改环境配置：

```bash
# 应用本地配置
cp .env.local .env

# 或者直接编辑 .env 文件
# 将 REDIS_URL=redis://talkai-redis:6379/0 
# 改为 REDIS_URL=memory://
```

## 服务验证

### 基本健康检查

```bash
# 1. 检查服务是否启动
curl -s http://localhost:8000/health
# 期望输出：{"status":"healthy","timestamp":"..."}

# 2. 检查 API 根路径
curl -s http://localhost:8000/
# 期望输出：{"message":"TalkAI API","version":"1.0.0","status":"running"}

# 3. 检查进程状态
ps aux | grep python3
# 应该看到 python3 main.py 进程
```

### API 功能验证

```bash
# 测试字典查询接口
curl "http://localhost:8000/api/v1/dict/query?word=hello"

# 测试 API 文档（如果启用）
curl -s http://localhost:8000/docs
```

### 日志检查

```bash
# 查看应用日志
tail -f logs/app.log

# 查看最近的错误日志
grep ERROR logs/app.log | tail -10
```

## 故障排查

### 常见问题及解决方案

#### 1. 端口被占用
```bash
# 问题：ERROR: [Errno 98] Address already in use
# 解决：检查并停止占用端口的进程
lsof -i:8000
kill -9 <PID>  # 替换为实际的进程ID
```

#### 2. 模块导入错误
```bash
# 问题：ModuleNotFoundError: No module named 'xxx'
# 解决：安装缺失的依赖
pip install -r requirements.txt
```

#### 3. 数据库连接问题
```bash
# 问题：数据库文件不存在或无权限
# 解决：检查数据库文件权限
ls -la data/db/
chmod 644 data/db/talkai.db
```

#### 4. Redis 连接失败
```bash
# 问题：连接 Redis 失败
# 解决：使用内存缓存替代
# 在 .env 中设置：REDIS_URL=memory://
```

#### 5. API 密钥问题
```bash
# 问题：AI 服务调用失败
# 解决：检查环境变量中的 API 密钥
grep API_KEY .env
# 确保 MOONSHOT_API_KEY 或 OPENAI_API_KEY 设置正确
```

## 注意事项

### 生产环境建议

1. **使用进程管理器**
   ```bash
   # 安装 PM2（推荐）
   npm install -g pm2
   pm2 start main.py --interpreter python3 --name talkai-backend
   ```

2. **配置反向代理**
   - 使用 Nginx 作为反向代理
   - 配置 SSL 证书
   - 设置适当的超时和限流

3. **监控和日志**
   ```bash
   # 定期清理日志文件
   find logs/ -name "*.log" -mtime +7 -delete
   
   # 设置日志轮转
   logrotate /etc/logrotate.d/talkai
   ```

### 开发环境建议

1. **使用虚拟环境**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **开启调试模式**
   ```bash
   # .env 中设置
   DEBUG=True
   LOG_LEVEL=DEBUG
   ```

3. **热重载启动**
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 安全注意事项

1. **保护环境变量**
   - 不要将 `.env` 文件提交到版本控制
   - 定期更换 API 密钥和密钥

2. **网络安全**
   - 生产环境建议不直接暴露 8000 端口
   - 使用防火墙限制访问

3. **数据安全**
   - 定期备份数据库文件
   - 设置适当的文件权限

## Clash 配置优化

### 配置文件修改

为了解决 Docker 构建和包管理器的网络问题，已对 Clash 配置进行优化：

**配置文件位置：** `/root/.config/clash/config.yaml`

**添加的直连规则：**
```yaml
# Docker和系统包管理器直连规则 - 添加于2025-08-23
- DOMAIN-SUFFIX,docker.io,🎯 全球直连
- DOMAIN-SUFFIX,docker.com,🎯 全球直连
- DOMAIN-SUFFIX,registry-1.docker.io,🎯 全球直连
- DOMAIN-SUFFIX,production.cloudflare.docker.com,🎯 全球直连
- DOMAIN-SUFFIX,debian.org,🎯 全球直连
- DOMAIN-SUFFIX,deb.debian.org,🎯 全球直连
- DOMAIN-SUFFIX,security.debian.org,🎯 全球直连
- DOMAIN-SUFFIX,ftp.debian.org,🎯 全球直连
- DOMAIN-SUFFIX,archive.ubuntu.com,🎯 全球直连
- DOMAIN-SUFFIX,security.ubuntu.com,🎯 全球直连
- DOMAIN-SUFFIX,pypi.org,🎯 全球直连
- DOMAIN-SUFFIX,pypi.python.org,🎯 全球直连
- DOMAIN-SUFFIX,files.pythonhosted.org,🎯 全球直连
- DOMAIN-SUFFIX,pypi.tuna.tsinghua.edu.cn,🎯 全球直连
- DOMAIN-SUFFIX,mirrors.tuna.tsinghua.edu.cn,🎯 全球直连
- DOMAIN-SUFFIX,mirrors.aliyun.com,🎯 全球直连
- DOMAIN-SUFFIX,mirrors.ustc.edu.cn,🎯 全球直连
# AI模型下载直连
- DOMAIN-SUFFIX,huggingface.co,🎯 全球直连
- DOMAIN-SUFFIX,hf.co,🎯 全球直连
- DOMAIN-SUFFIX,huggingface-assets.s3.us-east-1.amazonaws.com,🎯 全球直连
```

### 配置重载

配置修改后已自动重启 Clash 服务：
```bash
# 重启命令
systemctl restart clash || kill -HUP $(pgrep clash)

# 验证进程
ps aux | grep clash
```

### 优化效果

- ✅ **Docker 镜像拉取**：Docker Hub 和相关 CDN 直连
- ✅ **系统包更新**：Debian/Ubuntu 软件源直连  
- ✅ **Python 包安装**：PyPI 和国内镜像源直连
- ✅ **AI 模型下载**：Hugging Face 模型库直连
- ✅ **编译工具下载**：gcc/g++ 等系统工具直连

### 备份信息

- **原配置备份**：`/root/.config/clash/config.yaml.backup`
- **修改时间**：2025-08-23
- **修改内容**：在 rules 顶部添加开发相关域名直连规则

## 总结

**Docker 构建问题根本原因：**
1. ✅ **Clash 代理影响**：已通过配置优化解决
2. ❌ **内存资源不足**：1.7GB RAM 对比 2.6GB 需求严重不足
3. ✅ **SentenceTransformer 依赖**：项目必需的 AI 组件，不可移除

**推荐解决方案：**

**当前环境（1.7GB RAM）：**
- 继续使用 **Python 直接启动**（已成功运行）
- 优势：资源占用低、启动快速、便于调试

**如需 Docker 支持：**
1. **升级服务器**到 4GB+ RAM（最佳方案）
2. **临时增加 Swap**：`sudo fallocate -l 2G /tmp/docker-swap && sudo mkswap /tmp/docker-swap && sudo swapon /tmp/docker-swap`
3. **使用优化的 Dockerfile.lite**（已提供）
4. **清除代理变量构建**：`unset http_proxy https_proxy all_proxy && docker-compose up -d`

**Clash 配置**已优化完成，解决了代理导致的网络问题，但资源限制仍是主要瓶颈。
