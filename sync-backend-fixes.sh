#!/bin/bash

# 同步后端修复到服务器的脚本
# 修复了rsync嵌套问题后的完整同步

echo "=== TalkAI Backend 修复同步脚本 ==="
echo "准备同步以下修复到服务器:"
echo "1. AI聊天端点 (/dict/ai-chat) - 无需认证"
echo "2. WeChat认证临时修复"
echo "3. WeChat代理问题修复"
echo ""

# 检查必要文件
FILES_TO_SYNC=(
    "app/api/v1/dict.py"
    "app/api/v1/auth.py" 
    "app/services/wechat.py"
)

echo "检查本地文件..."
for file in "${FILES_TO_SYNC[@]}"; do
    if [ -f "backend/$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - 文件不存在!"
        exit 1
    fi
done

echo ""
echo "请确认服务器信息并执行以下命令:"
echo ""

# 生成同步命令 (用户需要替换SERVER_USER和SERVER_HOST)
echo "# 替换 USER@SERVER 为你的服务器信息"
echo "SERVER_USER_HOST=\"user@your-server\""
echo "SERVER_PATH=\"/path/to/your/backend\""
echo ""

for file in "${FILES_TO_SYNC[@]}"; do
    echo "scp backend/$file \$SERVER_USER_HOST:\$SERVER_PATH/$file"
done

echo ""
echo "# 在服务器上重启服务"
echo "ssh \$SERVER_USER_HOST 'cd /path/to/your/backend && docker-compose restart talkai-backend'"
echo ""

echo "# 测试AI聊天端点"
echo "curl -X POST https://api.jimingge.net/api/v1/dict/ai-chat -H 'Content-Type: application/json' -d '{\"message\": \"Hello\"}'"

echo ""
echo "=== 修复说明 ==="
echo "✅ dict.py: 添加了 /dict/ai-chat 端点，无需认证即可使用AI聊天"
echo "✅ auth.py: 添加了WeChat认证失败时的临时修复" 
echo "✅ wechat.py: 修复了SOCKS代理问题"
echo ""
echo "修复完成后，小程序应该能够:"
echo "- 发送消息获得真实AI回复"
echo "- 无需认证即可聊天"
echo "- 如果需要认证功能，WeChat登录也会有临时修复"