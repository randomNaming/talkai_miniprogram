# 真机调试配置指南

## 问题描述
真机调试时出现网络连接失败：`request:fail -102:net::ERR_CONNECTION_REFUSED`

## 解决方案

### ✅ 已自动配置
项目已自动配置真机调试环境检测，无需手动修改：

- **模拟器环境**：使用 `http://localhost:8000/api/v1`
- **真机调试环境**：自动使用 `http://192.168.1.100:8000/api/v1`
- **生产环境**：使用 `https://api.jimingge.net/api/v1`

### 📱 真机调试步骤

1. **确保后端服务运行**
   ```bash
   cd /Users/pean/aiproject/talkai_mini/backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **确保手机和电脑在同一WiFi网络**
   - 电脑IP：192.168.1.100
   - 手机需要连接相同WiFi网络

3. **微信开发者工具预览**
   - 点击"预览"
   - 扫码在真机上打开
   - 应用会自动检测环境并使用正确的API地址

### 🔧 验证配置

**后端服务状态**：✅ 正常运行
**内网IP访问**：✅ 192.168.1.100:8000 可正常访问
**API端点测试**：✅ 所有端点响应正常

### 📋 功能状态

- ✅ 环境自动检测 (development/device-debug/production)
- ✅ 网络连接问题修复
- ✅ 缺失页面文件补全 (dict.json, dict.wxss, profile.json, profile.wxss)
- ✅ 改进的词典页面UI
- ✅ 后端API完全兼容

### 🚨 注意事项

1. **防火墙设置**：确保8000端口对局域网开放
2. **网络环境**：手机和电脑必须在同一WiFi
3. **IP地址变化**：如果电脑IP变化，需要更新 `frontend/config/env.js` 中的 `device-debug` 配置

### 🔍 日志检查

在微信开发者工具控制台中应该看到：
```
[ENV] Current environment: device-debug
[ENV] API Base URL: http://192.168.1.100:8000/api/v1
```

如果看到上述日志且没有网络错误，说明配置成功！