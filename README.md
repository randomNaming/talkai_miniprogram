# TalkAI Mini - AI英语学习微信小程序

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.68+-red.svg)](https://fastapi.tiangolo.com)
[![WeChat](https://img.shields.io/badge/WeChat-Mini%20Program-green.svg)](https://developers.weixin.qq.com/miniprogram/dev/framework/)

一个基于AI的英语学习微信小程序，提供智能对话练习、语法纠正、词汇管理和词典查询功能。从桌面版本talkai_py移植而来，保持原有的命名规则、逻辑和功能。

## 🚀 功能特性

### 🤖 AI智能对话练习
- **实时对话** - 与AI进行自然英语对话，提升口语表达
- **语法纠正** - 自动检测语法错误并提供修正建议
- **词汇推荐** - 基于对话内容智能推荐学习词汇
- **学习分析** - 生成个性化学习报告和改进建议

### 📚 个人词汇管理
- **智能词汇库** - 自动收集AI纠错和词典查询的词汇
- **学习进度** - 跟踪词汇掌握度和学习统计
- **分级词汇** - 按学习等级(小学/中学/CET4/CET6等)加载词汇
- **复习系统** - 基于使用频率的智能复习提醒

### 🔍 在线词典查询
- **海量词库** - 40万英文词汇数据库支持
- **详细释义** - 包含音标、词性、中文释义等完整信息
- **一键收藏** - 查词后可直接添加到个人词汇库
- **模糊搜索** - 支持拼写容错和智能匹配

### 👤 用户个人中心
- **微信一键登录** - 无需注册，微信授权即可使用
- **学习档案** - 完整的使用统计和学习历史
- **个性化设置** - 年级、年龄等学习偏好配置
- **词汇状态** - 实时显示词汇库统计和掌握情况

## 📁 项目结构详解

### 前端架构 (`frontend/`)

```
frontend/
├── app.js                    # 全局应用入口，用户状态管理，词汇同步初始化
├── app.json                  # 微信小程序配置，页面路由，TabBar设置
├── app.wxss                  # 全局样式定义
├── project.config.json       # 微信开发者工具项目配置
│
├── pages/                    # 核心页面模块
│   ├── chat/                # 聊天对话页面
│   │   ├── chat.js          # 对话逻辑，AI交互，语法纠错，词汇添加
│   │   ├── chat.wxml        # 对话界面布局，消息列表，输入框
│   │   └── chat.wxss        # 对话样式，消息气泡，动画效果
│   │
│   ├── vocab/               # 词汇管理页面
│   │   ├── vocab.js         # 词汇列表逻辑，过滤最近学习词汇，学习进度
│   │   ├── vocab.wxml       # 词汇列表界面，统计展示，搜索功能
│   │   └── vocab.wxss       # 词汇页面样式，进度条，词汇卡片
│   │
│   ├── dict/                # 词典查询页面
│   │   ├── dict.js          # 词典搜索逻辑，词汇查询，添加到词汇库
│   │   ├── dict.wxml        # 搜索界面，查询结果展示
│   │   └── dict.wxss        # 词典页面样式，搜索框，结果列表
│   │
│   ├── profile/             # 个人中心页面
│   │   ├── profile.js       # 用户信息管理，设置编辑，词汇状态显示
│   │   ├── profile.wxml     # 个人信息界面，设置表单，统计展示
│   │   └── profile.wxss     # 个人中心样式，表单设计，数据展示
│   │
│   └── login/               # 登录页面
│       ├── login.js         # 微信登录逻辑，用户认证流程
│       ├── login.wxml       # 登录界面，授权按钮
│       └── login.wxss       # 登录页面样式
│
├── services/                # API服务层
│   ├── api.js               # 核心HTTP客户端，JWT认证，错误处理，所有API端点
│   └── vocab-sync.js        # 词汇数据同步管理器，定期同步，缓存策略
│
├── utils/                   # 工具函数库
│   └── storage.js           # 本地存储封装，token管理，离线缓存
│
└── config/                  # 配置文件
    ├── env.js               # 环境检测，API地址自动切换(本地/生产)
    └── sync.js              # 词汇同步配置，同步间隔，触发条件
```

### 后端架构 (`backend/`)

```
backend/
├── main.py                   # FastAPI应用入口，路由配置，CORS设置
├── requirements.txt          # Python依赖包列表
├── .env                      # 环境变量配置
├── docker-compose.yml        # Docker容器编排配置
├── Dockerfile               # Python应用容器构建
│
├── app/                     # 核心应用代码
│   ├── __init__.py
│   │
│   ├── api/v1/             # API路由端点
│   │   ├── __init__.py
│   │   ├── auth.py         # 微信登录认证，JWT token管理，用户注册
│   │   ├── chat.py         # AI对话接口，语法检查，词汇建议生成
│   │   ├── dict.py         # 词典查询接口，40万词库搜索，词汇释义
│   │   ├── learning_vocab.py # 学习词汇管理，个人词汇CRUD，统计分析
│   │   ├── sync.py         # 数据同步接口，前后端数据一致性
│   │   ├── user.py         # 用户信息管理，档案设置，学习统计
│   │   └── vocab.py        # 词汇库操作，批量管理，导入导出
│   │
│   ├── core/               # 核心配置模块
│   │   ├── __init__.py
│   │   ├── config.py       # 应用配置，环境变量，安全设置
│   │   ├── database.py     # 数据库连接，SQLAlchemy配置，会话管理
│   │   └── security.py     # JWT认证，密码加密，安全中间件
│   │
│   ├── models/             # 数据模型定义
│   │   ├── __init__.py
│   │   ├── user.py         # 用户模型，个人档案，使用统计
│   │   ├── vocab.py        # 词汇模型，学习统计，掌握度跟踪
│   │   └── chat.py         # 聊天记录模型，对话历史，会话管理
│   │
│   ├── services/           # 业务逻辑服务
│   │   ├── __init__.py
│   │   ├── ai.py           # AI服务集成，Moonshot/OpenAI，对话生成
│   │   ├── dictionary.py   # 词典服务，词汇查询，释义获取
│   │   ├── learning_analysis.py # 学习分析，进度统计，报告生成
│   │   ├── vocabulary.py   # 词汇管理服务，语义相似度，掌握度计算
│   │   ├── vocabulary_embedding.py # 词汇向量化，语义搜索
│   │   ├── vocab_loader.py # 分级词汇加载，初始化用户词汇库
│   │   └── wechat.py      # 微信API集成，登录验证，用户信息获取
│   │
│   └── utils/              # 工具函数库
│       ├── __init__.py
│       ├── prompts.py      # AI提示词模板，对话引导，语法检查
│       └── text_utils.py   # 文本处理，词汇提取，中英文检测
│
├── data/                   # 数据存储
│   ├── db/                # 数据库文件
│   │   ├── talkai.db      # 主数据库(用户,词汇,聊天记录)
│   │   └── dictionary400k.db # 词典数据库(40万英文词汇)
│   │
│   └── level_words/       # 分级词汇文件
│       ├── primary_school_all.json    # 小学词汇(439词)
│       ├── middle_school_all.json     # 中学词汇
│       ├── high_school_all.json       # 高中词汇
│       ├── cet4_all.json             # CET4词汇
│       └── cet6_all.json             # CET6词汇
│
└── logs/                   # 应用日志
    └── app.log            # 主要应用日志
```

## 🔧 开发环境设置

### 后端本地开发（推荐流程）

#### 1. 环境要求
- Python **3.10+**（推荐 3.11）
- 已安装 `git`

#### 2. 虚拟环境配置（三选一）

根据个人习惯选择以下任一方式创建并激活虚拟环境：

**选项 A：使用 Conda（推荐 Anaconda/Miniconda 用户）**
```bash
conda create -n talkai python=3.11
conda activate talkai
```

**选项 B：使用 venv（Python 内置）**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**选项 C：系统级 Python（不推荐，可能污染全局环境）**
```bash
# 确保 Python 版本符合要求
python --version  # 应 >= 3.10
# 直接使用系统 pip 安装依赖（跳过虚拟环境创建步骤）
```

#### 3. 安装后端依赖

进入后端目录并安装依赖包（使用 `requirements_manual.txt`）：

```bash
cd backend
pip install -r requirements_manual.txt

# 安装 LangChain 相关依赖（让 pip 自动选择兼容版本）
pip install "langchain-openai" "langchain-community" "langchain"
```

**注意**：如果遇到依赖冲突，可先卸载冲突的包再重新安装：
```bash
pip uninstall -y transformers tokenizers
pip install -r requirements_manual.txt
pip install "langchain-openai" "langchain-community" "langchain"
```

#### 4. 启动后端服务

```bash
# 确保在 backend 目录下
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

#### 5. 可选：配置离线模型（解决网络/SSL 问题）

**场景**：服务器无法访问 `huggingface.co` 或遇到 SSL 证书错误。

首次启动时会自动从 HuggingFace 下载 `sentence-transformers/all-MiniLM-L6-v2` 模型。如果下载失败：

1. 在可联网环境下载模型：
   ```bash
   python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
   ```

2. 将下载的模型拷贝到 `backend/models/all-MiniLM-L6-v2`

3. 修改 `backend/app/services/ai.py` 第 64 行：
   ```python
   # 修改前：
   self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
   
   # 修改后：
   self.embedding_model = SentenceTransformer('models/all-MiniLM-L6-v2')
   ```

**影响范围**：不启用该模型仅影响**词汇相似度推荐**功能，核心的 AI 对话与语法纠正不受影响。

### 前端本地开发

1. 打开微信开发者工具
2. 导入 `frontend/` 目录
3. 确保后端已在 `http://localhost:8000` 启动，前端会自动使用 `http://localhost:8000/api/v1`

**环境自动切换：**
- **开发环境**：微信开发者工具 → `http://localhost:8000/api/v1`
- **生产环境**：真实微信环境 → `https://api.jimingge.net/api/v1`

## 📊 数据库结构

### 用户表 (`users`)
```sql
- id: 用户唯一标识符(VARCHAR, 主键)
- openid: 微信OpenID(VARCHAR, 唯一索引)  
- nickname: 用户昵称
- grade: 学习等级(Primary School, CET4等)
- age, gender: 用户基本信息
- total_usage_time: 总使用时长(秒)
- chat_history_count: 聊天记录数
- created_at, last_login_at: 时间戳
```

### 词汇表 (`vocab_items`)
```sql
- id: 词汇条目ID(INTEGER, 主键)
- user_id: 关联用户ID(外键)
- word: 单词内容(VARCHAR, 索引)
- source: 词汇来源('chat_correction', 'lookup', 'level_vocab')
- level: 难度级别('primary_school', 'cet4'等)
- wrong_use_count, right_use_count: 使用统计
- isMastered: 是否已掌握(布尔值)
- added_date, last_used: 时间戳
- definition, phonetic, translation: 词汇释义信息
```

### 聊天记录表 (`chat_sessions`, `chat_messages`)
```sql
- 用户对话会话管理
- 消息内容和AI响应存储
- 学习分析数据收集
```

## 🔄 核心工作流程

### 用户认证流程
1. **微信登录** → `auth.py:wechat_login()` 
2. **OpenID验证** → 微信API获取用户标识
3. **JWT生成** → 创建访问令牌(24小时有效期)
4. **用户初始化** → 新用户自动加载对应等级词汇库

### AI对话学习流程
1. **用户输入** → `chat.js:onSendMessage()`
2. **语法检查** → `ai.py:check_vocab_from_input()`
3. **AI响应生成** → `ai.py:generate_response_natural()`
4. **词汇分析** → 提取错误词汇，生成学习建议
5. **手动添加** → 用户点击"+"添加词汇到学习库

### 词汇管理流程
1. **词汇来源**：
   - `chat_correction` - AI纠错词汇(用户点+号添加)
   - `lookup` - 词典查询词汇(词典页面添加)
   - `level_vocab` - 等级词汇(按grade自动加载)
2. **掌握度算法** → `right_use_count - wrong_use_count >= 3`
3. **词汇展示** → 词汇页面只显示最近学习词汇(过滤level_vocab)

### 数据同步机制
- **开发环境** → 禁用自动同步，避免认证问题
- **生产环境** → 5分钟定期同步，词汇操作后触发同步
- **同步范围** → 前端本地缓存 ↔ 后端SQLite数据库

## ⚙️ 关键配置文件

### 前端配置

**`config/env.js`** - 环境检测和API地址切换
```javascript
// 自动检测运行环境
const isDevelopment = wx.getSystemInfoSync().platform === 'devtools';
const API_BASE_URL = isDevelopment ? 
  'http://localhost:8000/api/v1' : 
  'https://api.jimingge.net/api/v1';
```

**`config/sync.js`** - 词汇同步配置
```javascript
SYNC_CONFIG = {
  VOCAB_SYNC_INTERVAL: 5 * 60 * 1000,  // 5分钟同步
  SYNC_TRIGGERS: {
    APP_LAUNCH: false,     // 开发环境禁用
    PERIODIC: false,       // 开发环境禁用
    MANUAL: true          // 保留手动同步
  }
}
```

**`services/api.js`** - API客户端
- JWT Bearer token认证
- 自动错误处理和重试
- 开发环境mock响应
- 30秒请求超时

### 后端配置

**`core/config.py`** - 应用配置
```python
# AI服务配置
MOONSHOT_API_KEY / OPENAI_API_KEY
# 微信小程序配置  
WECHAT_APP_ID, WECHAT_APP_SECRET
# 安全配置
SECRET_KEY (JWT签名密钥)
# 数据库配置
DATABASE_URL, REDIS_URL
```

**`core/database.py`** - 数据库配置
- SQLAlchemy ORM配置
- SQLite主数据库连接
- 外部词典数据库集成

## 🚀 部署指南

### 快速部署
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 生产部署
```bash
# 使用Docker Compose
docker-compose up -d

# 检查服务状态
curl http://localhost:8001/health
```

### 微信小程序发布
1. **域名配置** - 微信公众平台添加 `https://api.jimingge.net`
2. **代码上传** - 微信开发者工具上传审核
3. **版本发布** - 审核通过后正式发布

## 🔍 数据库查询示例

### 用户和词汇统计
```bash
sqlite3 data/db/talkai.db "
SELECT u.id, u.nickname, u.grade, 
       COUNT(v.id) as total_vocab,
       COUNT(CASE WHEN v.source='chat_correction' THEN 1 END) as corrections,
       COUNT(CASE WHEN v.source='lookup' THEN 1 END) as lookups
FROM users u 
LEFT JOIN vocab_items v ON u.id = v.user_id 
WHERE u.id = 'USER_ID_HERE'
GROUP BY u.id;"
```

### 查询特定词汇
```bash
sqlite3 data/db/talkai.db "
SELECT word, source, wrong_use_count, right_use_count, isMastered, added_date 
FROM vocab_items 
WHERE user_id = 'USER_ID_HERE' AND word = 'WORD_HERE';"
```

### 最近学习词汇
```bash
sqlite3 data/db/talkai.db "
SELECT word, source, added_date 
FROM vocab_items 
WHERE user_id = 'USER_ID_HERE' 
AND source IN ('chat_correction', 'lookup') 
ORDER BY added_date DESC 
LIMIT 20;"
```

## 🧩 核心功能实现

### AI对话与纠错
- **入口**：`chat.js:onSendMessage()`
- **语法检查**：`ai.py:check_vocab_from_input()`
- **错误分析**：提取`words_deserve_to_learn`数组
- **词汇建议**：基于语义相似度推荐学习词汇

### 词汇管理系统
- **添加机制**：`vocabulary.py:add_vocabulary_item()`
- **掌握度计算**：`right_use_count - wrong_use_count >= 3`
- **来源分类**：chat_correction(改错) / lookup(查词) / level_vocab(等级)
- **展示过滤**：词汇页面只显示用户主动学习的词汇

### 用户认证与权限
- **微信登录**：`auth.py:wechat_login()` 
- **JWT管理**：24小时有效期，自动刷新
- **开发环境**：固定用户ID避免重复创建
- **权限控制**：基于用户ID的数据隔离

## 🛠️ 开发注意事项

### 开发环境特殊处理
- **自动同步禁用** - 避免认证问题导致console刷屏
- **固定用户ID** - 开发环境使用固定OpenID
- **Mock响应** - API认证失败时自动降级到模拟数据
- **环境检测** - 自动识别开发者工具vs真机环境

### 数据一致性保证
- **字段名兼容** - 保持talkai_py原始命名(isMastered, wrong_use_count等)
- **掌握度算法** - 完全复制原版逻辑
- **词汇过滤** - 排除简单词汇和中文内容
- **统计实时性** - 词汇操作后立即更新统计

### 错误处理策略
- **网络错误** - 自动降级到本地缓存
- **认证失败** - 自动重新登录或使用mock数据  
- **API超时** - 30秒超时+重试机制
- **数据冲突** - 服务器数据优先原则

## 📈 性能优化

- **Redis缓存** - 热点数据缓存，减少数据库查询
- **本地存储** - 关键数据离线可用
- **分页加载** - 大量词汇数据分页展示
- **异步处理** - 词汇统计和分析异步计算

## 🔒 安全机制

- **JWT认证** - 所有API调用需要有效token
- **用户隔离** - 基于user_id的严格数据隔离
- **输入验证** - API参数校验和SQL注入防护
- **CORS保护** - 限制跨域访问来源

---

**从talkai_py桌面版移植而来，保持原有功能完整性的同时适配微信小程序生态** 🚀