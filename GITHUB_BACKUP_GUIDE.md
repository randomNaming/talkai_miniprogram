# GitHub 备份与分支管理指南

## 项目概述

TalkAI项目采用前后端分离架构，前端在本地开发，后端主要在服务器开发。本指南提供GitHub备份和分支管理的最佳实践。

## 分支策略

### 主要分支
- `main` - 生产稳定版本
- `dev` - 开发集成分支
- `dev-frontend` - 前端专用开发分支
- `dev-backend` - 后端专用开发分支

### 功能分支命名规范
- `feature/frontend-功能名` - 前端新功能
- `feature/backend-功能名` - 后端新功能
- `hotfix/问题描述` - 紧急修复
- `docs/文档更新` - 文档更新

## 开发工作流

### 1. 前端开发（本地环境）

```bash
# 克隆仓库
git clone <仓库地址>
cd talkai_miniprogram

# 创建前端功能分支
git checkout -b feature/frontend-chat-ui

# 开发过程中定期提交
git add frontend/
git commit -m "feat: 添加聊天界面组件"

# 推送到远程
git push origin feature/frontend-chat-ui
```

### 2. 后端开发（服务器环境）

```bash
# 在服务器上克隆或更新
git clone <仓库地址>
cd talkai_miniprogram

# 创建后端功能分支
git checkout -b feature/backend-api-optimization

# 开发完成后提交
git add backend/
git commit -m "feat: 优化API响应性能"

# 推送到远程
git push origin feature/backend-api-optimization
```

## 分支合并流程

### 方法一：命令行合并

#### 合并到dev分支（测试集成）

```bash
# 切换到dev分支
git checkout dev

# 拉取最新代码
git pull origin dev

# 合并功能分支
git merge feature/frontend-chat-ui
# 或
git merge feature/backend-api-optimization

# 推送到远程
git push origin dev
```

#### 合并到main分支（发布版本）

```bash
# 切换到main分支
git checkout main

# 拉取最新代码
git pull origin main

# 合并dev分支
git merge dev

# 推送到远程
git push origin main

# 创建版本标签
git tag -a v1.0.0 -m "版本1.0.0发布"
git push origin v1.0.0
```

### 方法二：Pull Request（推荐）

1. **创建Pull Request**
   - 在GitHub网页上点击"New Pull Request"
   - 选择源分支和目标分支：
     - `feature/xxx` → `dev` (功能测试)
     - `dev` → `main` (版本发布)

2. **合并选项**
   - **Merge commit** - 保留完整分支历史
   - **Squash and merge** - 压缩为单个提交（推荐用于功能分支）
   - **Rebase and merge** - 创建线性历史

3. **代码审查**
   - 团队成员审查代码变更
   - 自动化测试通过
   - 解决所有评论后合并

## 冲突解决

### 合并冲突处理

```bash
# 出现冲突时
git merge feature/xxx
# 显示：CONFLICT (content): Merge conflict in file.js

# 手动编辑冲突文件
# 查找 <<<<<<< HEAD 和 >>>>>>> 标记
# 选择保留的代码，删除冲突标记

# 标记冲突已解决
git add .
git commit -m "resolve: 解决合并冲突"

# 推送更新
git push origin dev
```

### 预防冲突策略
- 经常同步远程分支：`git pull origin dev`
- 小步骤频繁提交
- 及时合并到dev分支进行集成

## 同一仓库在不同环境的使用方法

### 1. 初始设置

**本地环境（前端开发）：**
```bash
# 克隆完整仓库
git clone https://github.com/username/talkai_miniprogram.git
cd talkai_miniprogram

# 主要工作在frontend目录
cd frontend/
# 前端开发...
```

**服务器环境（后端开发）：**
```bash
# 同样克隆完整仓库
git clone https://github.com/username/talkai_miniprogram.git
cd talkai_miniprogram

# 主要工作在backend目录
cd backend/
# 后端开发...
```

### 2. 分目录提交策略

**前端开发提交：**
```bash
# 只提交前端相关文件
git add frontend/
git add frontend/pages/chat/
git commit -m "feat(frontend): 添加聊天功能"
git push origin feature/frontend-chat
```

**后端开发提交：**
```bash
# 只提交后端相关文件
git add backend/
git add backend/app/api/
git commit -m "feat(backend): 新增聊天API接口"
git push origin feature/backend-chat-api
```

### 3. 工作流程最佳实践

#### 方案A：按功能分工
```bash
# 本地 - 前端开发者
git checkout -b feature/chat-frontend
# 只修改 frontend/ 目录
git add frontend/
git commit -m "feat(frontend): 聊天界面"

# 服务器 - 后端开发者  
git checkout -b feature/chat-backend
# 只修改 backend/ 目录
git add backend/
git commit -m "feat(backend): 聊天API"
```

#### 方案B：协同开发同一功能
```bash
# 1. 后端先开发API
git checkout -b feature/chat-system
git add backend/app/api/chat.py
git commit -m "feat(backend): 聊天API接口"
git push origin feature/chat-system

# 2. 前端基于API开发界面
git pull origin feature/chat-system
git add frontend/pages/chat/
git commit -m "feat(frontend): 基于新API的聊天界面"
git push origin feature/chat-system
```

### 4. 同步策略

**每日同步工作流：**
```bash
# 开始工作前（两个环境都要执行）
git checkout dev
git pull origin dev

# 创建今日工作分支
git checkout -b feature/today-work

# 工作结束后
git add [相应目录]/
git commit -m "描述今日工作"
git push origin feature/today-work
```

### 5. 避免冲突的规则

**文件修改边界：**
- 本地环境：主要修改 `frontend/` 目录
- 服务器环境：主要修改 `backend/` 目录
- 共同文件：`README.md`, `docs/` 需要协调修改

**Git配置建议：**
```bash
# 设置不同的用户信息区分提交来源
# 本地环境
git config user.name "Your Name (Local)"
git config user.email "you+local@example.com"

# 服务器环境  
git config user.name "Your Name (Server)"
git config user.email "you+server@example.com"
```

### 6. 实际操作示例

**场景：开发新的词汇管理功能**

```bash
# === 本地环境操作 ===
cd talkai_miniprogram
git checkout dev
git pull origin dev
git checkout -b feature/vocab-frontend

# 开发前端词汇页面
cd frontend/pages/vocab/
# 编辑 vocab.js, vocab.wxml, vocab.wxss

git add frontend/pages/vocab/
git commit -m "feat(frontend): 词汇管理页面UI"
git push origin feature/vocab-frontend

# === 服务器环境操作 ===
cd talkai_miniprogram  
git checkout dev
git pull origin dev
git checkout -b feature/vocab-backend

# 开发后端词汇API
cd backend/app/api/v1/
# 编辑 vocab.py

git add backend/app/api/v1/vocab.py
git commit -m "feat(backend): 词汇管理API接口"
git push origin feature/vocab-backend

# === 合并阶段 ===
# 可以先合并其中一个，再合并另一个
git checkout dev
git merge feature/vocab-backend
git merge feature/vocab-frontend
git push origin dev
```

### 7. 部署时的协调

```bash
# 准备发布时，确保前后端都合并到dev
git checkout dev
git pull origin dev

# 检查前后端文件都已更新
ls frontend/pages/  # 检查前端更新
ls backend/app/api/  # 检查后端更新

# 合并到main发布
git checkout main
git merge dev
git push origin main
```

## 完整工作流示例

### 开发新功能完整流程

```bash
# 1. 创建功能分支
git checkout dev
git pull origin dev
git checkout -b feature/frontend-vocabulary

# 2. 开发过程
# 编辑代码...
git add frontend/pages/vocab/
git commit -m "feat: 添加词汇管理页面"
git push origin feature/frontend-vocabulary

# 3. 合并到dev进行测试
git checkout dev
git pull origin dev
git merge feature/frontend-vocabulary
git push origin dev

# 4. 测试通过，合并到main发布
git checkout main
git pull origin main
git merge dev
git push origin main

# 5. 清理分支
git branch -d feature/frontend-vocabulary
git push origin --delete feature/frontend-vocabulary
```

## 日常维护

### 定期同步
```bash
# 每日开始工作前同步
git checkout dev
git pull origin dev

# 切换到工作分支
git checkout feature/current-work
git merge dev  # 保持分支最新
```

### 分支清理
```bash
# 查看所有分支
git branch -a

# 删除本地已合并分支
git branch -d feature/completed-feature

# 删除远程分支
git push origin --delete feature/completed-feature
```

## 备份策略

### 1. 代码备份
- 每日至少推送一次到远程仓库
- 重要功能完成立即推送
- 使用多个远程仓库（GitHub + GitLab/Gitee）

### 2. 数据库备份
- 数据库文件不提交到Git
- 定期导出数据库结构和重要数据
- 服务器端单独备份数据文件

### 3. 配置文件管理
- `.env` 文件不提交，提供 `.env.example` 模板
- 敏感配置使用环境变量
- 部署脚本和配置分别管理

## Git提交规范

### 提交信息格式
```
<类型>(<作用域>): <简短描述>

<详细描述>

<相关问题链接>
```

### 类型说明
- `feat` - 新功能
- `fix` - Bug修复
- `docs` - 文档更新
- `style` - 代码格式调整
- `refactor` - 代码重构
- `test` - 测试相关
- `chore` - 构建/工具链更新

### 示例
```bash
git commit -m "feat(frontend): 添加用户登录页面

- 实现微信授权登录
- 添加用户信息缓存
- 更新API调用接口

Closes #123"
```

## 紧急情况处理

### Hotfix流程
```bash
# 从main分支创建hotfix
git checkout main
git checkout -b hotfix/critical-bug-fix

# 修复问题
git add .
git commit -m "fix: 修复用户登录异常"

# 合并到main和dev
git checkout main
git merge hotfix/critical-bug-fix
git push origin main

git checkout dev
git merge hotfix/critical-bug-fix
git push origin dev

# 删除hotfix分支
git branch -d hotfix/critical-bug-fix
```

### 回滚操作
```bash
# 回滚最后一次提交
git revert HEAD

# 回滚到指定提交
git revert <commit-hash>

# 强制回滚（谨慎使用）
git reset --hard <commit-hash>
```

## 最佳实践

1. **提交频率** - 小步骤、频繁提交
2. **分支命名** - 清晰描述功能和作用域
3. **代码审查** - 使用Pull Request进行团队协作
4. **测试集成** - dev分支充分测试后再合并main
5. **文档同步** - 代码变更时同步更新相关文档
6. **备份多样** - GitHub主仓库 + 镜像仓库双重保障

---

*最后更新：2025-08-18*