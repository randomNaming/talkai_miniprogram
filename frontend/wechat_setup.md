# 微信小程序服务器配置完成

## 🎉 配置完成状态

### ✅ 已完成配置：
1. **域名解析**: `api.jimingge.net` 已指向服务器
2. **SSL证书**: Let's Encrypt 免费证书已配置，有效期至 2025-11-16
3. **Nginx反向代理**: HTTPS 访问已启用，HTTP 自动重定向到 HTTPS
4. **CORS跨域配置**: 已配置支持微信小程序域名 `https://servicewechat.com`
5. **API接口**: 所有 API 端点均通过 HTTPS 可访问

### 🔗 服务地址：
- **API基础地址**: `https://api.jimingge.net/api/v1`
- **健康检查**: `https://api.jimingge.net/health`
- **示例API**: `https://api.jimingge.net/api/v1/dict/query?word=hello`

## 📱 微信小程序配置

### 1. 服务器域名配置
在微信公众平台 → 开发 → 开发设置 → 服务器域名中添加：

**request合法域名（重要）:**
```
https://api.jimingge.net
```

**其他域名配置:**
- uploadFile合法域名: `https://api.jimingge.net` (如果需要文件上传)
- downloadFile合法域名: `https://api.jimingge.net` (如果需要文件下载)

### 2. 小程序代码配置
已更新 `frontend/services/api.js` 中的 API 地址：
```javascript
const BASE_URL = 'https://api.jimingge.net/api/v1';
```

### 3. 微信开发者工具配置
1. 打开微信开发者工具
2. 导入项目（选择 `frontend/` 目录）
3. 在工具栏中点击"详情" → "本地设置"
4. 确保"不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书" **未勾选**（生产环境必须取消勾选）

## 🔒 安全配置

### SSL/TLS 配置
- **协议版本**: TLS 1.2, TLS 1.3
- **证书类型**: Let's Encrypt (自动续期)
- **HSTS**: 已启用，强制 HTTPS 访问

### CORS 配置
```javascript
// 允许的来源
Access-Control-Allow-Origin: https://servicewechat.com

// 允许的方法
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS

// 允许的头部
Access-Control-Allow-Headers: Authorization, Content-Type, X-Requested-With
```

### 安全头部
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=63072000`

## 🧪 API 测试验证

### 健康检查
```bash
curl https://api.jimingge.net/health
# 预期输出: {"status":"healthy","timestamp":"2024-01-01T00:00:00Z"}
```

### 词典API测试
```bash
curl "https://api.jimingge.net/api/v1/dict/query?word=hello"
# 预期输出: {"word":"hello","phonetic":"hә'lәu","definition":"interj. 喂, 嘿","translation":"","pos":"","collins":0,"oxford":0,"tag":"","exchange":""}
```

### 微信登录API测试
```bash
curl -X POST https://api.jimingge.net/api/v1/auth/wechat/login \
  -H "Content-Type: application/json" \
  -d '{"js_code":"test_code"}'
```

## 📋 部署后检查清单

### 服务器检查
- [ ] 后端服务运行正常 (端口 8000)
- [ ] Nginx 反向代理正常 (端口 443)
- [ ] SSL 证书有效且未过期
- [ ] Redis 缓存服务正常 (端口 6380)
- [ ] 防火墙允许 80/443 端口访问

### 微信小程序检查
- [ ] 微信公众平台服务器域名已配置
- [ ] 小程序代码 API 地址已更新
- [ ] 开发者工具中取消"不校验合法域名"选项
- [ ] 小程序可以正常调用后端 API

### 功能验证
- [ ] 用户登录功能正常
- [ ] API 调用响应正常
- [ ] CORS 跨域请求无报错
- [ ] HTTPS 安全连接正常

## 🔧 维护信息

### SSL 证书自动续期
Let's Encrypt 证书有效期为 90 天，可设置自动续期：

```bash
# 添加到 crontab (每月15日检查续期)
0 0 15 * * /usr/local/bin/certbot renew --quiet && /www/server/nginx/sbin/nginx -s reload
```

### 日志文件位置
- **API访问日志**: `/www/wwwlogs/api.jimingge.net_access.log`
- **API错误日志**: `/www/wwwlogs/api.jimingge.net_error.log`
- **后端应用日志**: `/www/wwwroot/talkai_miniprogram/backend/logs/app.log`

### 监控建议
1. 定期检查 SSL 证书有效期
2. 监控 API 响应时间和错误率
3. 检查服务器资源使用情况
4. 备份数据库文件

## 📞 故障排查

### 常见问题
1. **小程序无法连接**: 检查服务器域名配置
2. **CORS 错误**: 验证域名是否在 CORS 允许列表中
3. **SSL 证书错误**: 检查证书有效性和配置
4. **API 响应慢**: 检查后端服务和数据库性能

### 技术支持
- 后端服务端口: 8000
- Nginx 配置: `/www/server/panel/vhost/nginx/api.jimingge.net.conf`
- SSL 证书: `/etc/letsencrypt/live/api.jimingge.net/`

---
**配置完成时间**: 2025-08-18
**下次证书续期**: 2025-11-16 之前