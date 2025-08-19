# TalkAI 部署问题记录与解决方案

本文档记录了 TalkAI 项目部署过程中遇到的问题及解决方案，为后续部署提供参考。

## 部署环境信息
- 操作系统: Linux 6.6.47-12.oc9.x86_64 (OpenCloudOS)
- Python版本: 3.11.6
- Nginx版本: 1.26.3
- Docker: 已安装
- 部署日期: 2025-08-18

## 主要问题与解决方案

### 1. Docker容器构建超时问题

**问题描述:**
```bash
docker-compose up -d --build
# 命令超时，容器构建失败
```

**原因分析:**
- 网络连接慢导致下载依赖包超时
- Python依赖包（特别是PyTorch相关）体积过大

**解决方案:**
直接在宿主机安装Python依赖并运行，跳过Docker容器化：

```bash
# 修复requirements.txt中的错误
# 移除 sqlite3 行（Python内置模块）
pip3 install fastapi uvicorn sqlalchemy python-dotenv redis loguru
pip3 install pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart

# 直接运行后端
python3 main.py
```

### 2. 配置文件格式错误

**问题描述:**
```
pydantic_settings.exceptions.SettingsError: error parsing value for field "allowed_origins"
```

**原因分析:**
`.env`文件中的`ALLOWED_ORIGINS`配置格式不正确，pydantic期望JSON数组格式。

**解决方案:**
修改`backend/.env`文件：
```bash
# 错误格式
ALLOWED_ORIGINS=https://servicewechat.com,https://api.jimingge.net

# 正确格式
ALLOWED_ORIGINS=["https://servicewechat.com","https://api.jimingge.net"]
```

### 3. Redis连接配置问题

**问题描述:**
Redis容器运行在6380端口，但应用配置指向容器内部网络。

**解决方案:**
修改`backend/.env`中的Redis连接：
```bash
# 原配置（容器内网络）
REDIS_URL=redis://talkai-redis:6379/0

# 修改为本地连接
REDIS_URL=redis://localhost:6380/0
```

### 4. 缺失依赖模块

**问题描述:**
```
ModuleNotFoundError: No module named 'jose'
ModuleNotFoundError: No module named 'pydantic_settings'
```

**解决方案:**
逐步安装缺失的依赖：
```bash
pip3 install pydantic-settings
pip3 install python-jose[cryptography] passlib[bcrypt] python-multipart
```

### 5. 认证模块函数缺失

**问题描述:**
```
NameError: name 'get_current_user' is not defined
```

**原因分析:**
`app/core/security.py`中缺少`get_current_user`函数，且`app/api/v1/auth.py`中有重复定义。

**解决方案:**
1. 在`security.py`中添加`get_current_user`函数：
```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

2. 从`auth.py`中移除重复的函数定义
3. 更新导入语句：
```python
from app.core.security import create_access_token, generate_user_id, get_current_user
```

### 6. Nginx代理配置问题

**问题描述:**
- 应用运行在8000端口，但外部需要通过8001端口访问
- Nginx配置文件位置不正确

**解决方案:**
1. 创建Nginx虚拟主机配置文件：
```bash
# 正确的vhost目录
/www/server/panel/vhost/nginx/talkai-backend.conf
```

2. 配置内容：
```nginx
server {
    listen 8001;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS配置
        add_header Access-Control-Allow-Origin "https://servicewechat.com" always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
    }
}
```

3. 重载Nginx配置：
```bash
/www/server/nginx/sbin/nginx -s reload
```

## 快速部署指南（下次部署）

### 前置要求
- 确保Redis容器正在运行
- 确保所需目录存在

### 一键部署脚本

```bash
#!/bin/bash
cd /www/wwwroot/talkai_miniprogram/backend

# 1. 安装核心依赖
pip3 install fastapi uvicorn sqlalchemy python-dotenv redis loguru pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart

# 2. 检查并修正配置文件
echo '检查.env配置...'
if grep -q 'ALLOWED_ORIGINS=\[' .env; then
    echo 'CORS配置正确'
else
    echo '修正CORS配置...'
    sed -i 's/ALLOWED_ORIGINS=.*/ALLOWED_ORIGINS=["https:\/\/servicewechat.com","https:\/\/api.jimingge.net"]/' .env
fi

# 3. 启动Redis（如果未运行）
if ! docker ps | grep -q talkai-redis; then
    echo '启动Redis容器...'
    docker run -d --name talkai-redis -p 6380:6379 redis:7-alpine
fi

# 4. 启动后端应用
echo '启动后端应用...'
nohup python3 main.py > /tmp/talkai-backend.log 2>&1 &

# 5. 配置Nginx代理
echo '配置Nginx代理...'
if [ ! -f "/www/server/panel/vhost/nginx/talkai-backend.conf" ]; then
    # 创建Nginx配置（此处省略具体内容，参考上面的配置）
    /www/server/nginx/sbin/nginx -s reload
fi

# 6. 验证部署
sleep 5
echo '验证部署状态...'
curl -s http://localhost:8001/health && echo "✅ 部署成功!" || echo "❌ 部署失败!"
```

### 手动部署步骤

1. **环境准备**
```bash
cd /www/wwwroot/talkai_miniprogram/backend
```

2. **安装依赖**
```bash
pip3 install fastapi uvicorn sqlalchemy python-dotenv redis loguru pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart
```

3. **检查配置**
```bash
# 确保.env文件中的ALLOWED_ORIGINS格式正确
grep ALLOWED_ORIGINS .env
# 应该显示: ALLOWED_ORIGINS=["https://servicewechat.com","https://api.jimingge.net"]
```

4. **启动服务**
```bash
# 确保Redis运行
docker ps | grep redis

# 启动后端
python3 main.py
```

5. **配置Nginx**
```bash
# 检查配置文件是否存在
ls /www/server/panel/vhost/nginx/talkai-backend.conf

# 重载Nginx
/www/server/nginx/sbin/nginx -s reload
```

6. **验证部署**
```bash
curl http://localhost:8001/health
curl "http://localhost:8001/api/v1/dict/query?word=hello"
```

## 常见问题排查

### 服务无法启动
1. 检查端口占用：`netstat -tlnp | grep 8000`
2. 查看日志：`tail -f /tmp/talkai-backend.log`
3. 检查Python依赖：`pip3 list | grep fastapi`

### API无法访问
1. 检查Nginx状态：`systemctl status nginx`
2. 检查端口监听：`netstat -tlnp | grep 8001`
3. 测试后端直连：`curl http://localhost:8000/health`

### Redis连接失败
1. 检查Redis容器：`docker ps | grep redis`
2. 测试连接：`redis-cli -h localhost -p 6380 ping`
3. 检查配置：`grep REDIS_URL .env`

## 优化建议

1. **容器化改进**: 创建更轻量的Docker镜像，使用多阶段构建
2. **依赖管理**: 使用虚拟环境隔离Python依赖
3. **配置管理**: 使用配置模板避免手动修改
4. **健康检查**: 添加更完善的服务健康检查机制
5. **日志管理**: 配置日志轮转和集中日志收集

## 备注

- 字典数据库缺失不影响核心功能，但会导致词典查询返回错误
- 学习分析调度器有SQL兼容性问题，但不影响基本API功能
- 生产环境建议使用HTTPS和域名访问
- 建议定期备份SQLite数据库文件

最后更新: 2025-08-18