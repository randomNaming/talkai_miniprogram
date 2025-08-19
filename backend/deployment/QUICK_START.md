# TalkAI 5分钟快速部署

## ⚡ 快速开始

适用于已有服务器环境，需要快速体验TalkAI功能的用户。

---

## 📋 部署前确认

确保你的服务器已具备：
- ✅ Docker & Docker Compose
- ✅ Nginx 运行中
- ✅ 域名解析 (api.jimingge.net)
- ✅ SSL证书可用

---

## 🚀 一键部署 (5分钟)

### 第1步: 上传项目 (1分钟)
```bash
# 登录服务器
ssh user@your-server

# 进入网站根目录
cd /www/wwwroot

# 克隆或上传项目
git clone <your-repo-url> talkai_miniprogram
# 或: scp -r talkai_miniprogram/ user@server:/www/wwwroot/

cd talkai_miniprogram
```

### 第2步: 交互式配置 (2分钟)
```bash
# 给脚本执行权限
chmod +x deployment/deploy-existing-server.sh

# 启动交互式部署（推荐）
sudo ./deployment/deploy-existing-server.sh --interactive
```

**系统会依次询问:**
1. **子域名**: `api.jimingge.net` (回车确认)
2. **项目目录**: `/www/wwwroot/talkai_miniprogram` (回车确认)
3. **API密钥**: 输入你的 Moonshot 或 OpenAI API密钥
4. **微信配置**: 输入 WeChat AppID 和 AppSecret  
5. **SSL证书**: 系统自动检测 (通常无需修改)
6. **词典位置**: 输入 dictionary400k.db 文件路径

### 第3步: 自动部署 (2分钟)
脚本将自动完成：
- ✅ 环境检查
- ✅ Docker服务配置
- ✅ Nginx反向代理设置
- ✅ SSL证书配置
- ✅ 服务启动和验证

### 第4步: 验证部署 (30秒)
```bash
# 检查服务状态
curl https://api.jimingge.net/health

# 查看详细状态
./deployment/deploy-existing-server.sh --status
```

看到以下输出表示成功：
```json
{"status":"healthy","timestamp":"..."}
```

---

## 🎯 使用配置文件部署 (推荐有经验用户)

### 快速配置
```bash
# 复制配置模板
cp deployment/quick-deploy-config.sh deployment/my-config.sh

# 编辑配置 (只需修改这几项)
nano deployment/my-config.sh
```

**修改内容:**
```bash
# 基础配置 (已预设好)
export DOMAIN="api.jimingge.net"
export PROJECT_DIR="/www/wwwroot/talkai_miniprogram"

# 必需配置 (请填入实际值)
export MOONSHOT_API_KEY="sk-your-actual-key"
export WECHAT_APP_ID="wx1234567890"  
export WECHAT_APP_SECRET="your-secret"
export DICT_DB_PATH="/path/to/dictionary400k.db"
```

### 执行部署
```bash
sudo ./deployment/deploy-existing-server.sh --config deployment/my-config.sh
```

---

## 📱 小程序配置 (1分钟)

部署成功后，快速配置微信小程序：

### 1. 更新API地址
```bash
# 编辑API配置文件
nano frontend/services/api.js

# 确认BASE_URL正确
const BASE_URL = 'https://api.jimingge.net/api/v1';
```

### 2. 微信平台配置
在[微信公众平台](https://mp.weixin.qq.com)添加服务器域名：
```
request合法域名: https://api.jimingge.net
```

### 3. 部署小程序
1. 用微信开发者工具打开 `frontend/` 目录
2. 预览测试无误后上传代码
3. 提交审核

---

## 🔍 快速验证

### API功能测试
```bash
# 健康检查
curl https://api.jimingge.net/health

# 词典查询
curl "https://api.jimingge.net/api/v1/dict/query?word=hello"

# 查看API文档
curl https://api.jimingge.net/docs
```

### 服务状态检查  
```bash
# 查看所有容器状态
docker-compose -f backend/docker-compose.yml ps

# 查看应用日志
docker-compose -f backend/docker-compose.yml logs -f --tail=20

# 检查端口监听
sudo netstat -tlnp | grep -E ':(8001|6380)'
```

---

## ⚠️ 快速故障排除

### 部署失败
```bash
# 查看部署日志
tail -f /tmp/talkai-deploy.log

# 检查环境
./deployment/deploy-existing-server.sh --check-only

# 重新部署
sudo ./deployment/deploy-existing-server.sh --interactive
```

### API无法访问
```bash
# 检查Nginx配置
sudo nginx -t

# 重启Nginx
sudo systemctl reload nginx

# 检查SSL证书
curl -I https://api.jimingge.net
```

### 容器启动失败
```bash
# 查看容器错误
docker-compose -f backend/docker-compose.yml logs

# 重启服务
docker-compose -f backend/docker-compose.yml restart

# 重新构建
docker-compose -f backend/docker-compose.yml up -d --build
```

---

## 🎛️ 常用管理命令

```bash
# 查看服务状态
./deployment/deploy-existing-server.sh --status

# 查看详细信息
./deployment/deploy-existing-server.sh --info

# 重启所有服务
docker-compose -f backend/docker-compose.yml restart

# 查看实时日志
docker-compose -f backend/docker-compose.yml logs -f

# 备份数据
tar -czf backup_$(date +%Y%m%d_%H%M%S).tar.gz backend/data/
```

---

## 📞 需要帮助？

### 快速自助排查
1. 查看 [故障排除手册](./TROUBLESHOOTING.md) - 包含所有常见问题
2. 查看 [配置参考](./CONFIG_REFERENCE.md) - 详细配置说明  
3. 检查部署日志: `tail -f /tmp/talkai-deploy.log`

### 完整部署指南
如需详细了解部署原理和自定义配置:
- [现有服务器部署详解](./EXISTING_SERVER_DEPLOYMENT.md)
- [完整部署指南](./DEPLOYMENT_GUIDE.md)

---

**🎉 5分钟内完成TalkAI部署，立即体验AI英语学习！**

> 如果遇到任何问题，请先查看故障排除手册，90%的问题都能快速解决。