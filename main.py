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
    @filter.regex(r"^来只(\S+)$")
    @filter.regex(r"^添加(\S+)$")
    @filter.regex(r"^删除(\S+)$")  
    @filter.regex(r"^查询(\S+)$")
    async def handle_query_keyword(self, event: AstrMessageEvent, name: str)
        if(event.message_str.startswith("删除")):
            keyword = event.message_str.split()[1]
            # 在这里处理关键词，获取相关图片等
            yield event.plain_result(f"删除 {keyword} 成功！")
        if(event.message_str.startswith("查询")):
            # 在这里处理关键词，获取相关图片等
            yield event.plain_result(f"查询 {name} 成功！")
        if(event.message_str.startswith("添加")):
            keyword = event.message_str.split()[1]
            # 在这里处理关键词，获取相关图片等
            yield event.plain_result(f"添加 {keyword} 成功！")
        if(event.message_str.startswith("来只")):
            keyword = event.message_str.split()[1]
            # 在这里处理关键词，获取相关图片等
            yield event.plain_result(f"来只 {keyword} 成功！")
        if(event.message_str.startswith("新建")):
            keyword = event.message_str.split()[1]
            # 在这里处理关键词，获取相关图片等
            yield event.plain_result(f"新建 {keyword} 成功！")
    

        