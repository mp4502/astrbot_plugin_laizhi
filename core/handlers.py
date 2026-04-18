"""
来只插件命令处理器
包含命令处理的业务逻辑（不包含装饰器）
"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger


class LaizhiHandlers:
    """来只插件命令处理器"""

    def __init__(self, db):
        """
        初始化命令处理器
        :param db: LaizhiDB 数据库实例
        """
        self.db = db

    async def handle_new(self, event: AstrMessageEvent):
        """处理新建命令的业务逻辑"""
        name = event.message_str.removeprefix("新建")
        real_name = await self.db.resolve_name(name)
        if real_name:
            return event.plain_result(f"❌ 来只 '{name}' 已存在！")

        success = await self.db.add_laizhi(name)
        if success:
            return event.plain_result(f"✅ 新建来只 '{name}' 成功！")
        else:
            return event.plain_result(f"❌ 新建 '{name}' 失败！")

    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令的业务逻辑"""
        name = event.message_str.removeprefix("来只")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"❌ 未找到来只 '{name}'，请先使用 '新建{name}' 创建！")

        laizhi_info = await self.db.get_laizhi(real_name)
        await self.db.update_laizhi(real_name, last_used=True)
        aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
        return event.plain_result(
            f"📸 来只 '{real_name}' 信息：\n"
            f"创建时间: {laizhi_info.created_at}\n"
            f"图片数量: {laizhi_info.image_count}\n"
            f"最后使用: {laizhi_info.last_used}\n"
            f"别名: {aliases_str}\n"
            f"描述: {laizhi_info.description or '无'}"
        )

    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令的业务逻辑"""
        name = event.message_str.removeprefix("添加")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"❌ 来只 '{name}' 不存在，请先使用 '新建{name}' 创建！")

        laizhi_info = await self.db.get_laizhi(real_name)
        new_count = laizhi_info.image_count + 1
        await self.db.update_laizhi(real_name, image_count=new_count)
        return event.plain_result(f"✅ 为 '{real_name}' 添加图片成功！当前总数: {new_count}")

    async def handle_alias(self, event: AstrMessageEvent):
        """处理别名命令的业务逻辑"""
        import re
        match = re.match(r"^别名(\S+)(?:\s+(.+))?$", event.message_str)
        if not match:
            return None

        name = match.group(1)
        alias = match.group(2) if match.group(2) else None

        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"❌ 来只 '{name}' 不存在！")

        laizhi_info = await self.db.get_laizhi(real_name)

        if alias:
            success = await self.db.add_alias(real_name, alias)
            if success:
                return event.plain_result(f"✅ 为 '{real_name}' 添加别名 '{alias}' 成功！")
            else:
                return event.plain_result(f"❌ 添加别名失败！别名 '{alias}' 可能已存在")
        else:
            aliases = await self.db.get_aliases(real_name)
            if aliases:
                alias_list = "\n".join(f"• {alias}" for alias in aliases)
                return event.plain_result(f"📋 '{real_name}' 的别名列表：\n{alias_list}")
            else:
                return event.plain_result(f"📋 '{real_name}' 暂无别名")

    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令的业务逻辑"""
        name = event.message_str.removeprefix("删除")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"❌ 来只 '{name}' 不存在！")

        success = await self.db.delete_laizhi(real_name)
        if success:
            return event.plain_result(f"✅ 删除来只 '{real_name}' 成功！")
        else:
            return event.plain_result(f"❌ 删除失败！")

    async def handle_query(self, event: AstrMessageEvent):
        """处理查询命令的业务逻辑"""
        name = event.message_str.removeprefix("查询")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"❌ 未找到来只 '{name}'")

        laizhi_info = await self.db.get_laizhi(real_name)
        aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
        original_name = f" (原名: {real_name})" if real_name != name else ""
        return event.plain_result(
            f"📋 查询结果 - '{name}'{original_name}：\n"
            f"创建时间: {laizhi_info.created_at}\n"
            f"图片数量: {laizhi_info.image_count}\n"
            f"最后使用: {laizhi_info.last_used}\n"
            f"别名: {aliases_str}\n"
            f"描述: {laizhi_info.description or '无'}"
        )

    async def handle_list(self, event: AstrMessageEvent):
        """处理列表命令的业务逻辑"""
        all_laizhi = await self.db.list_all_laizhi()
        stats = await self.db.get_statistics()

        if not all_laizhi:
            return event.plain_result("📋 当前还没有任何来只，使用 '新建<名称>' 来创建一个！")
        else:
            response = f"📋 来只列表 (共 {stats['total_laizhi']} 个，总计 {stats['total_images']} 张图片):\n\n"
            for laizhi in all_laizhi:
                response += f"• {laizhi.name} - {laizhi.image_count}张图片\n"
            response += f"\n💡 使用 '查询<名称>' 查看详细信息"
            return event.plain_result(response)