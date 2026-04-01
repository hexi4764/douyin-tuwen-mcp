---
name: douyin-mcp-server
description: |
  抖音创作者平台自动化助手。提供图文发布、登录状态检查、Cookie管理功能。当用户提到抖音发布、DY发布、抖音图文、创作者平台等操作时使用此skill。支持自动填写标题正文、上传头图、选择配乐，首次使用需扫码登录，后续自动保持登录状态。
---

# 抖音自动发布技能 (douyin_auto_publish)

## 技能概述

- **名称**: `douyin_auto_publish`
- **版本**: 1.1.0
- **协议**: MCP HTTP (JSON-RPC 2.0)
- **服务端点**: `http://127.0.0.1:18061/mcp`
- **健康检查**: `http://127.0.0.1:18061/health`

通过MCP协议自动化操作抖音创作者平台，实现文章发布、登录状态检查与Cookie管理。

## 环境部署

```bash
pip install -r requirements.txt
playwright install chromium
python main.py
```

## 工具列表

### 1. check_douyin_login_status

检查抖音创作者平台的登录状态，验证Cookie有效性。

**参数**: 无

**返回**:
- `success` (bool): 是否成功检查
- `logged_in` (bool): 是否已登录
- `current_url` (str): 当前页面URL
- `page_title` (str): 页面标题
- `cookie_count` (int): Cookie数量
- `message` (str): 状态描述

**调用示例**:
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "check_douyin_login_status",
    "arguments": {}
  }
}
```

**使用指导**: 每次发布文章前必须先调用此工具检查登录状态。

---

### 2. publish_douyin_article

发布文章到抖音创作者平台，自动填写标题、内容、上传头图和选择配乐。

**参数**:
- `title` (string, 必填): 文章标题
- `content` (string, 必填): 正文内容，至少100字
- `image` (string, 必填): 头图路径，相对于项目根目录，如 `image/cover.jpg`

**返回**:
- `success` (bool): 是否发布成功
- `message` (str): 操作结果消息
- `title` (str): 文章标题
- `content_length` (int): 内容长度
- `has_image` (bool): 是否包含头图

**调用示例**:
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "publish_douyin_article",
    "arguments": {
      "title": "文章标题",
      "content": "文章正文内容（至少100字）...",
      "image": "image/cover.jpg"
    }
  }
}
```

**约束条件**:
- 文章内容必须≥100字
- 首次使用需抖音APP扫码登录
- 头图文件必须存在于指定路径
- 需要图形界面环境

---

### 3. clear_douyin_cookies

清除本地保存的抖音登录Cookie，强制下次操作重新登录。

**参数**: 无

**返回**:
- `success` (bool): 是否成功清除
- `message` (str): 操作结果消息

**调用示例**:
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "tools/call",
  "params": {
    "name": "clear_douyin_cookies",
    "arguments": {}
  }
}
```

**使用场景**: 切换抖音账号时使用。

## AI工作流程

### 首次使用
1. 调用 `check_douyin_login_status` 检查登录状态
2. 如未登录，调用 `publish_douyin_article` 触发扫码登录
3. 用户用抖音APP扫码完成登录，Cookie自动保存
4. 再次调用 `publish_douyin_article` 发布文章

### 日常发布
1. 调用 `check_douyin_login_status` 确认登录状态
2. 验证文章内容≥100字
3. 调用 `publish_douyin_article` 发布文章
4. 向用户报告发布结果

### 账号切换
1. 调用 `clear_douyin_cookies` 清除当前登录状态
2. 调用 `check_douyin_login_status` 确认已退出
3. 调用 `publish_douyin_article` 使用新账号扫码登录并发布

## 错误处理

- **内容过短**: 提醒用户补充内容至100字以上
- **登录失效**: 引导用户重新扫码登录
- **图片不存在**: 检查图片路径是否正确
- **网络错误**: 建议稍后重试

## 注意事项

- 发布前务必检查登录状态
- 文章内容应保持原创性
- 合理控制发布频率
- 头图应与文章内容相关
