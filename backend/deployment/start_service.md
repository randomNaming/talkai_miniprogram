 根据你的docker-compose.yml配置，后端服务使用Docker容器运行。重启后端服务有几种方式：

  重启Docker容器服务

  # 进入后端目录
  cd /www/wwwroot/talkai_miniprogram/backend

  # 重启整个服务栈
  docker-compose restart

  # 或者只重启后端应用容器
  docker-compose restart talkai-backend

  # 重启Redis缓存服务
  docker-compose restart talkai-redis

  查看服务状态

  # 查看服务状态
  docker-compose ps

  # 查看实时日志
  docker-compose logs -f talkai-backend

  # 检查健康状态
  curl http://localhost:8001/health

  完全重建服务（如有代码更新）

  # 停止服务
  docker-compose down

  # 重新构建并启动
  docker-compose up -d --build

  最常用的命令是 docker-compose restart talkai-backend，这会重启你的后端API服务。

