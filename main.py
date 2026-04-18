"""
来只插件主文件
AstrBot 来只图库插件 - 支持图片管理和随机分享
"""
from pathlib import Path

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from astrbot.core.message.components import Image

from .core import (
    LaizhiDB,
    LaizhiHandlers,
    PhotoDatabase
)
from .core.image_context import init_image_context_manager, get_image_context_manager


@register("laizhi", "mp4502", "AstrBot 来只图库插件 - 支持图片管理", "2.0.0")
class MyPlugin(Star):
    """来只图库插件主类"""

    def __init__(self, context: Context):
        super().__init__(context)
        # 获取插件数据目录
        plugin_data_path = self._get_plugin_data_path()
        # 初始化数据库，使用规范的数据目录
        self.db = LaizhiDB(db_path=plugin_data_path / "laizhi_db.json")
        # 初始化图片数据库，使用规范的数据目录
        self.photo_db = PhotoDatabase(base_path=plugin_data_path / "images")
        # 初始化图片上下文管理器
        self.image_context_manager = init_image_context_manager()
        # 初始化命令处理器
        self.handlers = None  # 将在 initialize 中 设置

    def _get_plugin_data_path(self) -> Path:
        """获取插件数据目录，遵循 AstrBot 大文件存储规范"""
        try:
            # 尝试使用 AstrBot 规范路径
            import importlib
            path_module = importlib.import_module('astrbot.core.utils.astrbot_path')
            get_astrbot_data_path = getattr(path_module, 'get_astrbot_data_path', None)

            if get_astrbot_data_path:
                return Path(get_astrbot_data_path()) / "plugin_data" / "laizhi"
        except (ImportError, AttributeError):
            pass

        # 回退到插件目录下的 data/plugin_data 文件夹
        return Path(__file__).parent.parent / "data" / "plugin_data"

    async def initialize(self):
        """插件初始化方法"""
        # 数据库会在首次访问时自动初始化（惰性初始化）
        await self.photo_db.initialize()
        # 创建命令处理器实例，传递数据库实例
        self.handlers = LaizhiHandlers(self.db, self.photo_db, self.image_context_manager)
        logger.info("来只插件数据库初始化完成")

    async def terminate(self):
        """插件销毁方法"""
        logger.info("来只插件已停止")

    # ==================================================================
    # 消息监听器 - 捕获图片到上下文
    # ==================================================================

    @filter.platform_adapter_type(filter.PlatformAdapterType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，捕获图片到上下文."""
        messages = event.get_messages()
        image_ctx = get_image_context_manager()

        for comp in messages:
            if isinstance(comp, Image):
                # 获取图片 URL
                url = comp.url or comp.file
                if url and url.startswith(("http://", "https://")):
                    image_ctx.add_image(
                        event,
                        url,
                        message_id=str(getattr(event, "message_id", "")),
                        sender_id=str(getattr(event, "user_id", "")),
                    )
                    logger.debug(f"[ImgExploration] 捕获图片到上下文: {url[:50]}...")


    # ==================== 核心命令 ====================

    @filter.regex(r"^新建(\S+)$")
    async def handle_new(self, event: AstrMessageEvent):
        """处理新建命令"""
        result = await self.handlers.handle_new(event)
        if result:
            yield result

    @filter.regex(r"^来只(\S+)$")
    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令 - 随机发送图片"""
        result = await self.handlers.handle_laizhi(event)
        if result:
            yield result

    @filter.regex(r"^添加(\S+)$")
    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令 - 支持URL下载图片"""
        result = await self.handlers.handle_add(event)
        if result:
            yield result

    @filter.regex(r"^别名(\S+)(?:\s+(.+))?$")
    async def handle_alias(self, event: AstrMessageEvent):
        """处理别名命令"""
        result = await self.handlers.handle_alias(event)
        if result:
            yield result

    @filter.command("删除")
    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令 - 回复机器人发送的图片即可删除"""
        result = await self.handlers.handle_delete(event)
        if result:
            yield result

    @filter.regex(r"^查询(\S+)$")
    async def handle_query(self, event: AstrMessageEvent):
        """处理查询命令"""
        result = await self.handlers.handle_query(event)
        if result:
            yield result

    @filter.command("列表")
    async def handle_list(self, event: AstrMessageEvent):
        """处理列表命令"""
        result = await self.handlers.handle_list(event)
        if result:
            yield result
