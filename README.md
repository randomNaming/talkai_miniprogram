# TalkAI - AI英语学习微信小程序

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-red.svg)](https://fastapi.tiangolo.com)
[![WeChat](https://img.shields.io/badge/WeChat-Mini%20Program-green.svg)](https://developers.weixin.qq.com/miniprogram/dev/framework/)

一个基于AI的英语学习微信小程序，提供智能对话练习、语法纠正、词汇管理和词典查询功能。

## 功能特性

### 🤖 AI智能对话
- **智能语音识别** - 支持语音输入，自动转换为文字
- **实时对话练习** - 与AI进行英语对话，提升口语能力
- **语法纠正** - 自动检测并纠正语法错误
- **学习分析** - 生成个性化学习报告和建议

### 📚 词汇管理
- **个人词汇本** - 收藏和管理学习过的单词
- **智能复习** - 基于遗忘曲线的复习提醒
- **词汇统计** - 学习进度和掌握程度分析
- **分类管理** - 按主题或难度分类词汇

### 🔍 词典查询
- **海量词库** - 40万词汇数据库支持
- **详细释义** - 包含发音、词性、例句等完整信息
- **离线查询** - 本地数据库，无需网络连接
- **查询历史** - 自动保存查询记录

### 👤 用户系统
- **微信登录** - 一键授权登录，无需注册
- **学习档案** - 完整的学习历史和进度跟踪
- **个性化设置** - 学习目标和偏好配置
- **数据同步** - 多设备数据云端同步

## 技术架构

### 后端技术栈
- **Python 3.8+** - 核心开发语言
- **FastAPI** - 高性能Web框架
- **SQLAlchemy** - ORM数据库操作
- **SQLite** - 轻量级数据库
- **Redis** - 缓存和会话管理
- **Docker** - 容器化部署
- **Nginx** - 反向代理和负载均衡

### 前端技术栈
- **微信小程序** - 原生小程序开发
- **JavaScript ES6+** - 核心逻辑开发
- **WXML/WXSS** - 页面结构和样式
- **WeChat API** - 微信官方接口集成

### AI服务集成
- **Moonshot AI** - 主要AI对话服务（推荐）
- **OpenAI GPT** - 备选AI服务
- **智能语音识别** - 语音转文字功能
- **自然语言处理** - 语法分析和纠错

## 项目结构

```
talkai_miniprogram/
├── frontend/                 # 微信小程序前端
│   ├── pages/               # 页面文件
│   │   ├── chat/           # 聊天对话页面
│   │   ├── vocab/          # 词汇管理页面
│   │   ├── dict/           # 词典查询页面
│   │   ├── profile/        # 个人中心页面
│   │   └── login/          # 登录页面
│   ├── services/           # API接口服务
│   ├── utils/              # 工具函数
│   ├── components/         # 自定义组件
│   └── images/             # 图片资源
│
├── backend/                  # Python FastAPI后端
│   ├── app/                # 应用核心代码
│   │   ├── api/v1/         # API路由端点
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   ├── data/               # 数据文件
│   │   └── db/             # 数据库文件
│   ├── logs/               # 日志文件
│   └── tests/              # 测试代码
│
├── deployment/               # 部署脚本和配置
├── docs/                    # 项目文档
└── README.md               # 项目说明
```

## 快速开始

### 环境要求

- Python 3.8+
- Docker & Docker Compose
- Redis
- 微信开发者工具
- 有效的AI服务API密钥（Moonshot或OpenAI）

### 后端部署

1. **克隆项目**
```bash
git clone https://github.com/username/talkai_miniprogram.git
cd talkai_miniprogram
```

2. **配置环境变量**
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，配置API密钥和数据库连接
```

3. **使用Docker Compose部署**
```bash
docker-compose up -d
```

4. **验证部署**
```bash
curl http://localhost:8001/health
```

### 前端部署

1. **微信公众平台配置**
   - 登录微信公众平台
   - 配置服务器域名：`https://your-domain.com`
   - 下载开发者工具

2. **导入项目**
```bash
# 在微信开发者工具中导入 frontend/ 目录
```

3. **配置API地址**
```javascript
// frontend/services/api.js
const BASE_URL = 'https://your-domain.com/api/v1';
```

4. **测试和上传**
   - 在开发者工具中测试功能
   - 上传代码并提交审核

## 配置说明

### 环境变量配置

主要配置项在 `backend/.env` 文件中：

```bash
# AI服务配置（二选一）
MOONSHOT_API_KEY=your_moonshot_api_key
OPENAI_API_KEY=your_openai_api_key

# 微信小程序配置
WECHAT_APP_ID=your_wechat_app_id
WECHAT_APP_SECRET=your_wechat_app_secret

# 安全配置
SECRET_KEY=your_32_character_secret_key

# 数据库配置
DATABASE_URL=sqlite:///./data/db/talkai.db
REDIS_URL=redis://localhost:6380

# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### 微信小程序配置

在微信公众平台配置以下信息：

1. **服务器域名配置**
   - request合法域名：`https://your-domain.com`
   - socket合法域名：`wss://your-domain.com`（如需WebSocket）

2. **业务域名配置**
   - 业务域名：`https://your-domain.com`

## 开发指南

### 后端开发

```bash
# 安装依赖
cd backend
pip install -r requirements.txt

# 运行开发服务器
python main.py

# 运行测试
python -m pytest tests/ -v

# 查看API文档
# 访问 http://localhost:8000/docs
```

### 前端开发

```bash
# 使用微信开发者工具打开 frontend/ 目录
# 在工具中进行调试和预览

# 主要开发文件
frontend/pages/         # 页面逻辑
frontend/services/api.js # API接口配置
frontend/utils/         # 工具函数
```

### API接口文档

主要API端点：

- `POST /api/v1/auth/wechat/login` - 微信登录
- `POST /api/v1/chat/send` - 发送聊天消息
- `GET /api/v1/dict/query` - 词典查询
- `POST /api/v1/vocab/add` - 添加词汇
- `GET /api/v1/user/profile` - 用户信息

完整API文档访问：`http://localhost:8001/docs`

## 部署指南

### 生产环境部署

推荐使用自动化部署脚本：

```bash
# 交互式部署
./deployment/deploy-existing-server.sh --interactive

# 使用配置文件部署
./deployment/deploy-existing-server.sh --config deployment/quick-deploy-config.sh

# 检查部署状态
./deployment/deploy-existing-server.sh --status
```

### 手动部署

详细部署步骤参考：
- [部署指南](DEPLOYMENT_GUIDE.md)
- [快速开始](QUICK_START.md)
- [故障排除](TROUBLESHOOTING.md)

## 开发文档

- [GitHub备份指南](GITHUB_BACKUP_GUIDE.md) - Git工作流和备份策略
- [配置参考](CONFIG_REFERENCE.md) - 详细配置说明
- [微信小程序设置](wechat_setup.md) - 微信平台配置
- [Claude开发指南](CLAUDE.md) - AI辅助开发指导

## 贡献指南

欢迎提交Issue和Pull Request！

### 开发流程

1. Fork项目到个人仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交代码：`git commit -m "feat: 描述你的功能"`
4. 推送分支：`git push origin feature/your-feature`
5. 创建Pull Request

### 代码规范

- 后端遵循PEP8 Python代码规范
- 前端遵循微信小程序开发规范
- 提交信息遵循Conventional Commits规范
- 添加适当的测试用例

## 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

## 支持与反馈

- **Issue报告**: [GitHub Issues](https://github.com/username/talkai_miniprogram/issues)
- **功能建议**: [GitHub Discussions](https://github.com/username/talkai_miniprogram/discussions)
- **邮件联系**: your-email@example.com

## 更新日志

### v1.0.0 (2025-08-18)
- ✨ 初始版本发布
- 🤖 AI对话功能
- 📚 词汇管理系统
- 🔍 词典查询功能
- 👤 微信登录集成
- 🐳 Docker容器化部署

---

**TalkAI** - 让AI助力你的英语学习之旅 🚀


------------------
⏺ 前端本地缓存到后端数据库的词汇同步。
  5分钟同步一次
  代码位置：/Users/pean/aiproject/talkai_mini/frontend/config/sync.js:52

