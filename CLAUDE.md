# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AstrBot 图库管理插件（"来只插件"），允许聊天群组中的用户创建图片集合、添加/随机获取图片、管理别名。运行在 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 平台内，不能独立运行。Python 3.10+（使用了 `match/case`、`X | None` 类型语法）。

## 开发环境

无构建系统、无测试、无 linting 配置。插件通过 AstrBot 的插件管理器安装加载。

依赖（声明在 `metadata.yaml`）：`aiohttp>=3.9.0`、`aiofiles>=23.0.0`

运行时依赖 `astrbot.api` 和 `astrbot.core`，必须在 AstrBot 环境中运行。

## 架构

三层分离：

1. **路由层** (`main.py`) — `MyPlugin(Star)` 类，用 `@filter.regex()` / `@filter.command()` 绑定中文聊天命令到 handler 方法。所有用户命令是中文（如 `新建猫咪`、`来只猫咪`）。
2. **业务逻辑层** (`core/handlers.py`) — `LaizhiHandlers` 处理命令逻辑，协调元数据 DB 和图片存储。
3. **数据层**：
   - `core/database.py` — JSON 文件元数据存储（`LaizhiDB`），每个会话一个 `{session_id}_db.json`。存储集合名、图片计数、别名、每张图片的元数据（添加者、时间、哈希）。方法标记 `async` 但内部使用同步文件 I/O。
   - `core/photo_database.py` — 文件系统图片存储（`PhotoDatabase`），通过 `aiohttp` 下载图片，保存为 `{hash前8位}{扩展名}`，路径结构 `session_id/laizhi_name/`。
   - `core/image_context.py` — 内存图片上下文追踪器（`ImageContextManager`），使用 `OrderedDict` + LRU 淘汰，追踪会话中的最近图片供"添加"和"删除"命令引用。线程安全（`threading.RLock`）。

## 关键约定

- **会话隔离**：所有数据操作接收 `session_id`（来自 `event.session_id`），每个群/聊天独立数据库和图片目录。
- **图片哈希**：SHA-256 全文哈希用于去重和身份标识，文件名取前 8 位十六进制字符。
- **AstrBot 插件 API**：`Star` 基类、`@register()` 装饰器注册插件、`@filter.regex()`/`@filter.command()` 路由、`@filter.permission_type(ADMIN)` 权限控制、`event.plain_result()`/`event.image_result()` 返回响应。
- **命令匹配**：`main.py` 中的 regex 模式提取命令参数（如 `^新建(\S+)$` 提取图库名），handler 通过 `event.message_str.removeprefix()` 获取名称。
- **别名系统**：图库可有多个别名，通过 `db.resolve_name()` 将别名解析回真实名称。支持主名称和别名互换。
