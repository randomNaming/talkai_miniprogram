服务器部署操作步骤

  1. 环境准备

  # 更新系统包
  sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
  # 或
  sudo yum update -y  # CentOS/RHEL

  # 安装基础依赖
  sudo apt install -y python3 python3-pip python3-venv git redis-server sqlite3  # Ubuntu/Debian
  # 或  
  sudo yum install -y python3 python3-pip git redis epel-release && sudo yum install -y sqlite  # CentOS/RHEL

  2. 创建项目目录和用户

  # 创建项目目录
  sudo mkdir -p /opt/talkai_mini
  sudo chown $USER:$USER /opt/talkai_mini
  cd /opt/talkai_mini

  # 上传项目文件（使用scp、rsync或git clone）
  # 方法1: 使用git
  git clone <your-repo-url> .

  # 方法2: 手动上传backend目录到 /opt/talkai_mini/backend

  3. 创建Python虚拟环境

  cd /opt/talkai_mini/backend

  # 创建虚拟环境
  python3 -m venv venv

  # 激活虚拟环境
  source venv/bin/activate

  # 升级pip
  pip install --upgrade pip

  4. 安装Python依赖

  # 安装项目依赖
  pip install -r requirements_server.txt

  # 验证安装
  pip list | grep fastapi
  pip list | grep uvicorn

  5. 配置环境变量

  cd /opt/talkai_mini/backend

  # 创建环境配置文件
  cat > .env << 'EOF'
  # Database
  DATABASE_URL=sqlite:///./data/db/talkai.db

  # Redis
  REDIS_URL=redis://localhost:6379/0

  # AI Service Keys (至少配置一个)
  MOONSHOT_API_KEY=your_moonshot_api_key_here
  # OPENAI_API_KEY=your_openai_api_key_here

  # WeChat Mini Program (可选)
  WECHAT_APP_ID=your_wechat_app_id
  WECHAT_APP_SECRET=your_wechat_app_secret

  # Security
  SECRET_KEY=your-secure-secret-key-must-be-at-least-32-characters-long

  # App Settings
  DEBUG=false
  HOST=0.0.0.0
  PORT=8000
  LOG_LEVEL=INFO

  # Model Settings
  MODEL_PROVIDER=moonshot
  MOONSHOT_MODEL=moonshot-v1-8k
  EOF

  # 设置文件权限
  chmod 600 .env

  6. 创建数据目录

  # 创建必要的目录
  mkdir -p data/db
  mkdir -p data/uploads
  mkdir -p logs

  # 确保字典数据库存在（如果有的话）
  # 将 dictionary400k.db 复制到 data/db/ 目录

  7. 启动Redis服务

  # 启动Redis服务
  sudo systemctl enable redis-server  # Ubuntu/Debian
  sudo systemctl start redis-server

  # 或
  sudo systemctl enable redis  # CentOS/RHEL  
  sudo systemctl start redis

  # 验证Redis运行
  redis-cli ping  # 应该返回 PONG

  8. 测试应用启动

  cd /opt/talkai_mini/backend
  source venv/bin/activate

  # 测试启动
  uvicorn main:app --reload --host 0.0.0.0 --port 8000

  # 在另一个终端测试
  curl http://localhost:8000/health
  # 应该返回: {"status":"healthy","timestamp":"..."}

  9. 创建系统服务（推荐）

  # 创建systemd服务文件
  sudo tee /etc/systemd/system/talkai-backend.service > /dev/null << 'EOF'
  [Unit]
  Description=TalkAI Backend Service
  After=network.target redis.service
  Requires=redis.service

  [Service]
  Type=exec
  User=YOUR_USERNAME
  Group=YOUR_GROUP
  WorkingDirectory=/opt/talkai_mini/backend
  Environment=PATH=/opt/talkai_mini/backend/venv/bin
  ExecStart=/opt/talkai_mini/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
  Restart=always
  RestartSec=3
  StandardOutput=journal
  StandardError=journal

  [Install]
  WantedBy=multi-user.target
  EOF

  # 替换YOUR_USERNAME和YOUR_GROUP为实际用户
  sudo sed -i "s/YOUR_USERNAME/$USER/g" /etc/systemd/system/talkai-backend.service
  sudo sed -i "s/YOUR_GROUP/$USER/g" /etc/systemd/system/talkai-backend.service

  # 重载systemd并启动服务
  sudo systemctl daemon-reload
  sudo systemctl enable talkai-backend
  sudo systemctl start talkai-backend

  # 检查服务状态
  sudo systemctl status talkai-backend

  10. 配置防火墙（如需要）

  # Ubuntu/Debian (ufw)
  sudo ufw allow 8000/tcp

  # CentOS/RHEL (firewalld)
  sudo firewall-cmd --permanent --add-port=8000/tcp
  sudo firewall-cmd --reload

  11. 验证部署

  # 检查服务状态
  sudo systemctl status talkai-backend

  # 查看日志
  sudo journalctl -u talkai-backend -f

  # 测试API
  curl http://your-server-ip:8000/
  curl http://your-server-ip:8000/health

  12. 日常运维命令

  # 重启服务
  sudo systemctl restart talkai-backend

  # 停止服务
  sudo systemctl stop talkai-backend

  # 查看日志
  sudo journalctl -u talkai-backend -n 100

  # 更新代码后重启
  cd /opt/talkai_mini/backend
  source venv/bin/activate
  git pull  # 如果使用git
  sudo systemctl restart talkai-backend

  环境变量配置说明

  - MOONSHOT_API_KEY: 月之暗面API密钥（推荐）
  - OPENAI_API_KEY: OpenAI API密钥（备选）
  - WECHAT_APP_ID/SECRET: 微信小程序配置
  - SECRET_KEY: JWT签名密钥，必须32+字符
  - DATABASE_URL: SQLite数据库路径
  - REDIS_URL: Redis连接字符串

⏺ Update Todos
  ⎿  ☒ 分析backend目录结构和依赖
     ☒ 生成requirements.txt文件
     ☒ 编写服务器部署操作步骤

⏺ 已为你准备好服务器部署的完整操作步骤。主要包括：

  1. requirements_server.txt - 服务器专用的依赖包列表
  2. 详细部署步骤 - 从环境准备到服务启动的完整流程

  核心依赖包：
  - FastAPI + Uvicorn (Web框架)
  - SQLAlchemy (数据库ORM)
  - Redis (缓存)
  - sentence-transformers (AI功能)
  - 认证和安全相关包

  部署要点：
  - Python 3.8+虚拟环境
  - Redis服务器
  - 环境变量配置(.env文件)
  - systemd服务管理
  - 防火墙端口开放(8000)

  启动命令：uvicorn main:app --reload --host 0.0.0.0 --port 8000

