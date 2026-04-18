"""
来只插件主文件
AstrBot 来只图库插件 - 支持图片管理和随机分享
"""
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

from .core import (
    LaizhiDB,
    LaizhiHandlers,
    PhotoDatabase
)


@register("laizhi", "mp4502", "AstrBot 来只图库插件 - 支持图片管理", "2.0.0")
class MyPlugin(Star):
    """来只图库插件主类"""

    def __init__(self, context: Context):
        super().__init__(context)
        # 初始化数据库
        self.db = LaizhiDB()
        # 初始化图片数据库
        self.photo_db = PhotoDatabase()
        # 初始化命令处理器
        self.handlers = None  # 将在 initialize 中设置

    async def initialize(self):
        """插件初始化方法"""
        await self.db.initialize()
        await self.photo_db.initialize()
        # 创建命令处理器实例，传递数据库实例
        self.handlers = LaizhiHandlers(self.db, self.photo_db)
        logger.info("来只插件数据库初始化完成")

    async def terminate(self):
        """插件销毁方法"""
        logger.info("来只插件已停止")

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

    @filter.regex(r"^删除(\S+)$")
    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令"""
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
