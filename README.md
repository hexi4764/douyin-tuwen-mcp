# 抖音创作者平台 MCP Server

通过 MCP 协议自动化操作抖音创作者平台，实现图文发布、登录状态检查与 Cookie 管理。

## 功能特性

- ✅ **图文发布**：自动填写标题、正文、上传头图、选择配乐
- ✅ **登录检查**：验证 Cookie 有效性，确认登录状态
- ✅ **Cookie 管理**：自动保存登录状态，支持切换账号
- ✅ **扫码登录**：首次使用扫码登录，后续自动保持登录

## 环境要求

- Python 3.8+
- Playwright

## 安装部署

```bash
# 安装依赖
pip install -r requirements.txt

# 安装浏览器
playwright install chromium

# 启动服务
python main.py
```

服务启动后：
- MCP 端点：`http://127.0.0.1:18061/mcp`
- 健康检查：`http://127.0.0.1:18061/health`

## 工具列表

### 1. check_douyin_login_status

检查抖音创作者平台的登录状态。

**参数**：无

**返回**：
- `logged_in`：是否已登录
- `current_url`：当前页面 URL
- `cookie_count`：Cookie 数量

### 2. publish_douyin_article

发布图文文章到抖音创作者平台。

**参数**：
- `title`：文章标题（建议 10-30 字）
- `content`：文章正文（必须 ≥100 字）
- `image`：头图路径（支持绝对路径和相对路径）

### 3. clear_douyin_cookies

清除本地保存的抖音登录 Cookie，用于切换账号。

## 使用流程

### 首次使用

1. 调用 `check_douyin_login_status` 检查登录状态
2. 如未登录，调用 `publish_douyin_article` 触发扫码登录
3. 用抖音 APP 扫码完成登录
4. Cookie 自动保存，后续无需再扫码

### 日常发布

1. 调用 `check_douyin_login_status` 确认登录状态
2. 调用 `publish_douyin_article` 发布文章

## 注意事项

- 文章内容必须 ≥100 字
- 首次使用需要图形界面环境（弹出浏览器扫码）
- 头图文件必须存在
- 合理控制发布频率

## 文件结构

```
douyin-mcp-server/
├── skill.md          # 技能说明
├── main.py           # MCP 服务主程序
├── requirements.txt  # Python 依赖
├── README.md         # 本文件
└── image/            # 图片资源
    └── 2.jpg
```

## 许可证

MIT License
