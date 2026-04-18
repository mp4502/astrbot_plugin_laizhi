from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
from core.db import LaizhiDB

@register("laizhi", "mp4502", "AstrBot 来只图库插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.db = LaizhiDB()

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self.db.initialize()
        logger.info("来只插件数据库初始化完成")

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息
        Comp.Image.fromFileSystem("path/to/image.jpg").send(event) # 发送一条图片消息

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    @filter.regex(r"^新建(\S+)$")
    async def handle_new(self, event: AstrMessageEvent):
        """处理新建命令"""
        name = event.message_str.removeprefix("新建")
        success = await self.db.add_laizhi(name)
        if success:
            yield event.plain_result(f"✅ 新建来只 '{name}' 成功！")
        else:
            yield event.plain_result(f"❌ 来只 '{name}' 已存在！")

    @filter.regex(r"^来只(\S+)$")
    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令"""
        name = event.message_str.removeprefix("来只")
        laizhi_info = await self.db.get_laizhi(name)
        if laizhi_info:
            # 更新最后使用时间
            await self.db.update_laizhi(name, last_used=True)
            yield event.plain_result(
                f"📸 来只 '{name}' 信息：\n"
                f"创建时间: {laizhi_info.created_at}\n"
                f"图片数量: {laizhi_info.image_count}\n"
                f"最后使用: {laizhi_info.last_used}\n"
                f"描述: {laizhi_info.description or '无'}"
            )
        else:
            yield event.plain_result(f"❌ 未找到来只 '{name}'，请先使用 '新建{name}' 创建！")

    @filter.regex(r"^添加(\S+)$")
    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令"""
        name = event.message_str.removeprefix("添加")
        laizhi_info = await self.db.get_laizhi(name)
        if laizhi_info:
            # 增加图片计数
            new_count = laizhi_info.image_count + 1
            await self.db.update_laizhi(name, image_count=new_count)
            yield event.plain_result(f"✅ 为 '{name}' 添加图片成功！当前总数: {new_count}")
        else:
            yield event.plain_result(f"❌ 来只 '{name}' 不存在，请先使用 '新建{name}' 创建！")

    @filter.regex(r"^删除(\S+)$")
    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令"""
        name = event.message_str.removeprefix("删除")
        success = await self.db.delete_laizhi(name)
        if success:
            yield event.plain_result(f"✅ 删除来只 '{name}' 成功！")
        else:
            yield event.plain_result(f"❌ 来只 '{name}' 不存在！")

    @filter.regex(r"^查询(\S+)$")
    async def handle_query(self, event: AstrMessageEvent):
        """处理查询命令"""
        name = event.message_str.removeprefix("查询")
        laizhi_info = await self.db.get_laizhi(name)
        if laizhi_info:
            yield event.plain_result(
                f"📋 查询结果 - '{name}'：\n"
                f"创建时间: {laizhi_info.created_at}\n"
                f"图片数量: {laizhi_info.image_count}\n"
                f"最后使用: {laizhi_info.last_used}\n"
                f"描述: {laizhi_info.description or '无'}"
            )
        else:
            yield event.plain_result(f"❌ 未找到来只 '{name}'")

    @filter.command("列表")
    async def handle_list(self, event: AstrMessageEvent):
        """处理列表命令 - 显示所有来只"""
        all_laizhi = await self.db.list_all_laizhi()
        stats = await self.db.get_statistics()

        if not all_laizhi:
            yield event.plain_result("📋 当前还没有任何来只，使用 '新建<名称>' 来创建一个！")
        else:
            response = f"📋 来只列表 (共 {stats['total_laizhi']} 个，总计 {stats['total_images']} 张图片):\n\n"
            for laizhi in all_laizhi:
                response += f"• {laizhi.name} - {laizhi.image_count}张图片\n"
            response += f"\n💡 使用 '查询<名称>' 查看详细信息"
            yield event.plain_result(response)
    

        