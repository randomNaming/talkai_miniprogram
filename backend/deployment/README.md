# TalkAI 微信小程序 - AI英语学习助手

## 📖 项目概述

TalkAI是一个基于微信小程序的AI英语学习助手，提供智能对话练习、语法纠错、词汇管理等功能。

### 核心功能
- 🤖 **智能对话**: AI驱动的英语对话练习
- ✅ **语法纠错**: 实时语法错误检测和修正
- 📚 **词汇管理**: 个人词汇库管理和同步
- 📖 **词典查询**: 40万词典数据查询
- 📊 **学习分析**: 自动生成学习进度报告
- 👥 **多用户**: 支持微信登录和数据隔离

### 技术架构
- **前端**: 微信小程序 (WeChat Mini Program)
- **后端**: Python FastAPI + SQLite + Redis
- **部署**: Docker + Nginx + 腾讯云

---

## 🚀 选择部署方式

  新手用户: README.md → QUICK_START.md → CONFIG_REFERENCE.md
  有经验用户: README.md → EXISTING_SERVER_DEPLOYMENT.md
  技术深度用户: README.md → DEPLOYMENT_GUIDE.md
  遇到问题: TROUBLESHOOTING.md
  配置疑问: CONFIG_REFERENCE.md
  
### 🎯 部署场景选择

| 场景 | 文档 | 适用对象 | 部署时间 | 技术要求 |
|------|------|----------|----------|----------|
| 🆕 **全新服务器** | [完整部署指南](./DEPLOYMENT_GUIDE.md) | 空白服务器，需要完整配置 | 30-60分钟 | 中高级 |
| 🏠 **现有服务器** | [现有环境部署](./EXISTING_SERVER_DEPLOYMENT.md) | 已有网站运行的服务器 | 15-30分钟 | 中级 |
| ⚡ **快速体验** | [5分钟快速开始](./QUICK_START.md) | 快速测试和验证 | 5-10分钟 | 初级 |

### 📋 部署前准备

#### 服务器要求
- **配置**: 腾讯云 CVM 2核4G (推荐)
- **系统**: Ubuntu 20.04 LTS
- **环境**: Docker & Docker Compose, Nginx
- **网络**: 域名和SSL证书

#### API密钥准备
```bash
# AI服务（必需其一）
MOONSHOT_API_KEY=your_moonshot_key    # Moonshot AI (推荐)
OPENAI_API_KEY=your_openai_key        # OpenAI

# 微信小程序配置
WECHAT_APP_ID=your_app_id
WECHAT_APP_SECRET=your_app_secret
```

---

## ⚡ 快速开始

### 1分钟了解部署流程

```bash
# 1. 克隆项目
git clone <your-repo-url>
cd talkai_miniprogram

# 2. 选择部署方式
# 现有服务器（推荐）
./deployment/deploy-existing-server.sh --interactive

# 或者使用配置文件
./deployment/deploy-existing-server.sh --config deployment/quick-deploy-config.sh
```

### 部署成功验证

```bash
# 检查服务状态
curl https://api.jimingge.net/health

# 查看详细信息
./deployment/deploy-existing-server.sh --status
```

---

## 📁 项目结构
```
talkai_miniprogram/
├── README.md                    # 项目介绍和部署入口 (本文件)
├── backend/                     # 后端API服务
│   ├── app/                    # FastAPI应用核心
│   ├── deployment/             # 部署脚本和配置
│   ├── docker-compose.yml     # Docker编排配置
│   └── requirements.txt       # Python依赖
├── frontend/                   # 微信小程序前端
│   ├── pages/                 # 小程序页面
│   ├── services/             # API服务调用
│   └── app.json              # 小程序配置
├── deployment/                 # 部署工具
│   ├── deploy-existing-server.sh  # 现有服务器部署脚本
│   └── quick-deploy-config.sh     # 快速配置模板
└── docs/                      # 详细文档（即将整理）
```

---

## 📱 微信小程序配置

部署完成后，需要配置微信小程序：

### 1. 更新API地址
```javascript
// frontend/services/api.js
const BASE_URL = 'https://api.jimingge.net/api/v1';
```

### 2. 微信公众平台配置
在[微信公众平台](https://mp.weixin.qq.com)配置服务器域名：
```
request合法域名: https://api.jimingge.net
```

### 3. 上传小程序
1. 使用微信开发者工具导入 `frontend/` 目录
2. 编译并上传代码
3. 提交审核和发布

---

## 🔧 运维管理

### 常用管理命令
```bash
# 查看服务状态
./deployment/deploy-existing-server.sh --status

# 查看日志
docker-compose -f backend/docker-compose.yml logs -f

# 重启服务
docker-compose -f backend/docker-compose.yml restart

# 数据备份
./deployment/backup.sh
```

### 监控检查
```bash
# 健康检查
curl https://api.jimingge.net/health

# API测试
curl https://api.jimingge.net/api/v1/dict/query?word=hello
```

---

## 📞 获取帮助

### 🔍 问题排查顺序
1. 查看 [故障排除手册](./TROUBLESHOOTING.md)
2. 检查部署日志: `/tmp/talkai-deploy.log`
3. 查看应用日志: `docker-compose logs`
4. 检查Nginx日志: `/var/log/nginx/talkai_error.log`

### 📋 检查清单
- [ ] 服务器配置满足要求
- [ ] API密钥配置正确
- [ ] 域名DNS解析正常
- [ ] SSL证书有效
- [ ] 端口未被占用
- [ ] 微信小程序域名已配置

---

## 📈 性能指标

- **并发用户**: 支持200-300并发用户
- **注册用户**: 支持1000-5000用户规模
- **API响应**: 平均响应时间 < 2秒
- **AI推理**: QPS ≥ 20
- **可用性**: 99.5% SLA

---

## 📄 许可证

本项目遵循 MIT 许可证。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

---

**🎉 开始部署您的TalkAI英语学习小程序吧！**

根据您的服务器情况选择对应的部署文档，按照步骤操作即可快速完成部署。# talkai_server
