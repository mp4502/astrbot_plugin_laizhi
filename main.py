from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

from .core import (
    LaizhiDB,
    LaizhiHandlers
)

@register("laizhi", "mp4502", "AstrBot 来只图库插件", "1.0.0")
class MyPlugin(Star):
    """来只图库插件主类"""

    def __init__(self, context: Context):
        super().__init__(context)
        # 初始化数据库
        self.db = LaizhiDB()
        # 初始化命令处理器
        self.handlers = None  # 将在 initialize 中设置

    async def initialize(self):
        """插件初始化方法"""
        await self.db.initialize()
        # 创建命令处理器实例，传递数据库实例
        self.handlers = LaizhiHandlers(self.db)
        logger.info("来只插件数据库初始化完成")

    async def terminate(self):
        """插件销毁方法"""
        logger.info("来只插件已停止")

    # ==================== 示例命令 ====================

    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """示例 hello world 命令"""
        user_name = event.get_sender_name()
        message_str = event.message_str
        message_chain = event.get_messages()
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!")

    # ==================== 核心命令 ====================

    @filter.regex(r"^新建(\S+)$")
    async def handle_new(self, event: AstrMessageEvent):
        """处理新建命令"""
        result = await self.handlers.handle_new(event)
        if result:
            yield result

    @filter.regex(r"^来只(\S+)$")
    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令"""
        result = await self.handlers.handle_laizhi(event)
        if result:
            yield result

    @filter.regex(r"^添加(\S+)$")
    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令"""
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