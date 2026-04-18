from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp

@register("laizhi", "mp4502", "AstrBot 来只图库插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

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
        name = event.message_str[2:]  # 去掉前缀 "新建"
        yield event.plain_result(f"新建 {name} 成功！")

    @filter.regex(r"^来只(\S+)$")
    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令"""
        name = event.message_str.removeprefix("来只")  # 去掉前缀 "来只"
        yield event.plain_result(f"来只 {name} 成功！")

    @filter.regex(r"^添加(\S+)$")
    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令"""
        name = event.message_str.removeprefix("添加")  # 去掉前缀 "添加"
        yield event.plain_result(f"添加 {name} 成功！")

    @filter.regex(r"^删除(\S+)$")
    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令"""
        name = event.message_str.removeprefix("删除")  # 去掉前缀 "删除"
        yield event.plain_result(f"删除 {name} 成功！")

    @filter.regex(r"^查询(\S+)$")
    async def handle_query(self, event: AstrMessageEvent):
        """处理查询命令"""
        name = event.message_str.removeprefix("查询")  # 去掉前缀 "查询"
        yield event.plain_result(f"查询 {name} 成功！")
    

        