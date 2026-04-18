"""
来只插件命令处理器
包含命令处理的业务逻辑
"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
import astrbot.api.message_components as Comp
from .image_context import get_image_context_manager


class LaizhiHandlers:
    """来只插件命令处理器"""

    def __init__(self, db, photo_db=None, image_context_manager=None):
        """
        初始化命令处理器
        :param db: LaizhiDB 数据库实例
        :param photo_db: PhotoDatabase 图片数据库实例
        :param image_context_manager: 图片上下文管理器实例
        """
        self.db = db
        self.photo_db = photo_db
        self.image_context_manager = image_context_manager

    async def handle_new(self, event: AstrMessageEvent):
        """处理新建命令的业务逻辑"""
        name = event.message_str.removeprefix("新建")
        real_name = await self.db.resolve_name(name)
        if real_name:
            return event.plain_result(f"来只 '{name}' 已存在！")

        success = await self.db.add_laizhi(name)
        if success:
            return event.plain_result(f"新建来只 '{name}' 成功！")
        else:
            return event.plain_result(f"新建 '{name}' 失败！")

    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令的业务逻辑 - 随机发送图片"""
        name = event.message_str.removeprefix("来只")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"未找到来只 '{name}'，请先使用 '新建{name}' 创建！")

        # 更新最后使用时间
        await self.db.update_laizhi(real_name, last_used=True)

        # 如果有图片数据库，尝试获取随机图片
        if self.photo_db:
            image_path = await self.photo_db.get_random_image(real_name)
            if image_path:
                # 发送图片
                try:
                    return event.image_result(image_path)
                except Exception as e:
                    logger.error(f"发送图片失败: {e}")
                    return event.plain_result(f"发送图片失败: {str(e)}")
            else:
                laizhi_info = await self.db.get_laizhi(real_name)
                aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
                return event.plain_result(
                    f"来只 '{real_name}' 信息：\n"
                    f"创建时间: {laizhi_info.created_at}\n"
                    f"图片数量: {laizhi_info.image_count}\n"
                    f"最后使用: {laizhi_info.last_used}\n"
                    f"别名: {aliases_str}\n"
                    f"描述: {laizhi_info.description or '无'}\n\n"
                    f"提示: 该来只暂无图片，使用 '添加{real_name}' 来添加图片"
                )
        else:
            # 没有图片数据库时的逻辑
            laizhi_info = await self.db.get_laizhi(real_name)
            aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
            return event.plain_result(
                f"来只 '{real_name}' 信息：\n"
                f"创建时间: {laizhi_info.created_at}\n"
                f"图片数量: {laizhi_info.image_count}\n"
                f"最后使用: {laizhi_info.last_used}\n"
                f"别名: {aliases_str}\n"
                f"描述: {laizhi_info.description or '无'}"
            )

    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令的业务逻辑 - 从聊天记录中获取图片"""
        name = event.message_str.removeprefix("添加")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"来只 '{name}' 不存在，请先使用 '新建{name}' 创建！")

        # 检查图片数据库是否可用
        if not self.photo_db:
            return event.plain_result(f"图片数据库未初始化，无法添加图片")

        # 尝试从图片上下文管理器获取最近的图片
        image_url = None
        session_info = ""

        if self.image_context_manager:
            try:
                # 获取最近的图片URL
                image_url = self.image_context_manager.get_recent_image(event)

                if image_url:
                    # 获取图片上下文信息
                    context_info = self.image_context_manager.get_image_context_info(event)
                    if context_info.get("has_images"):
                        session_info = f"\n会话图片数: {context_info['count']}"

                logger.info(f"从图片上下文获取到图片: {image_url}")
            except Exception as e:
                logger.warning(f"从图片上下文获取图片失败: {e}")

        # 如果上下文管理器中没有图片，尝试直接从消息中获取
        if not image_url:
            messages = event.get_messages()
            for comp in messages:
                # 检查是否是图片组件
                if hasattr(comp, 'url') and comp.url:
                    image_url = comp.url
                    break
                # 检查是否有 file 属性
                if hasattr(comp, 'file') and comp.file:
                    image_url = comp.file
                    break

        if not image_url:
            return event.plain_result(f"未找到图片，请发送图片后使用 '添加{name}' 命令{session_info}")

        # 下载并保存图片
        local_path = await self.photo_db.download_image(real_name, image_url)
        if local_path:
            # 更新数据库中的图片计数
            laizhi_info = await self.db.get_laizhi(real_name)
            new_count = laizhi_info.image_count + 1
            await self.db.update_laizhi(real_name, image_count=new_count)

            # 获取会话标识信息
            session_key = ""
            if self.image_context_manager:
                try:
                    session_key_info = self.image_context_manager._get_session_key(event)
                    session_key = f"\n会话: {session_key_info}"
                except:
                    pass

            return event.plain_result(f"为 '{real_name}' 添加图片成功！{session_key}\n已保存到: {local_path}\n当前总数: {new_count}{session_info}")
        else:
            return event.plain_result(f"图片下载失败: {image_url}")

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
            return event.plain_result(f"来只 '{name}' 不存在！")

        laizhi_info = await self.db.get_laizhi(real_name)

        if alias:
            # 检查是否是删除操作（以 - 开头）
            if alias.startswith("-"):
                alias_to_delete = alias[1:]  # 去掉 - 前缀
                if not alias_to_delete:
                    return event.plain_result(f"删除别名失败！请指定要删除的别名")

                # 检查要删除的名称是否存在
                all_names = [real_name] + laizhi_info.aliases
                if alias_to_delete not in all_names:
                    return event.plain_result(f"删除别名失败！别名 '{alias_to_delete}' 不存在")

                # 检查是否只剩一个名称
                if len(all_names) == 1:
                    return event.plain_result(f"删除别名失败！'{real_name}' 是最后一个名称，不能删除")

                # 执行删除前保存原主名称
                old_primary = real_name
                # 获取删除后会剩下的名称
                remaining_names = [n for n in all_names if n != alias_to_delete]

                # 执行删除
                success = await self.db.delete_alias(name, alias_to_delete)
                if success:
                    # 获取删除后的主名称
                    if alias_to_delete == old_primary:
                        # 删除的是主名称，第一个剩余的名称成为新的主名称
                        new_primary = remaining_names[0]
                        return event.plain_result(f"已删除主名称 '{alias_to_delete}'，'{new_primary}' 成为主名称")
                    else:
                        # 删除的是别名，主名称不变
                        return event.plain_result(f"删除别名 '{alias_to_delete}' 成功！")
                else:
                    return event.plain_result(f"删除别名失败！")
            else:
                # 添加别名
                success = await self.db.add_alias(real_name, alias)
                if success:
                    return event.plain_result(f"为 '{real_name}' 添加别名 '{alias}' 成功！")
                else:
                    return event.plain_result(f"添加别名失败！别名 '{alias}' 可能已存在")
        else:
            # 查询别名列表
            aliases = await self.db.get_aliases(real_name)
            if aliases:
                alias_list = "\n".join(f"- {alias}" for alias in aliases)
                return event.plain_result(f"'{real_name}' 的别名列表：\n{alias_list}")
            else:
                return event.plain_result(f"'{real_name}' 暂无别名")

    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令的业务逻辑"""
        name = event.message_str.removeprefix("删除")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"来只 '{name}' 不存在！")

        # 删除图片文件夹
        if self.photo_db:
            await self.photo_db.delete_laizhi_folder(real_name)

        success = await self.db.delete_laizhi(real_name)
        if success:
            return event.plain_result(f"删除来只 '{real_name}' 成功！（包括所有图片）")
        else:
            return event.plain_result(f"删除失败！")

    async def handle_query(self, event: AstrMessageEvent):
        """处理查询命令的业务逻辑"""
        name = event.message_str.removeprefix("查询")
        real_name = await self.db.resolve_name(name)
        if not real_name:
            return event.plain_result(f"未找到来只 '{name}'")

        laizhi_info = await self.db.get_laizhi(real_name)
        aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
        original_name = f" (原名: {real_name})" if real_name != name else ""

        # 获取实际图片数量
        actual_image_count = 0
        if self.photo_db:
            actual_image_count = await self.photo_db.get_image_count(real_name)

        return event.plain_result(
            f"查询结果 - '{name}'{original_name}：\n"
            f"创建时间: {laizhi_info.created_at}\n"
            f"图片数量: {laizhi_info.image_count} (实际文件: {actual_image_count})\n"
            f"最后使用: {laizhi_info.last_used}\n"
            f"别名: {aliases_str}\n"
            f"描述: {laizhi_info.description or '无'}"
        )

    async def handle_list(self, event: AstrMessageEvent):
        """处理列表命令的业务逻辑"""
        all_laizhi = await self.db.list_all_laizhi()
        stats = await self.db.get_statistics()

        if not all_laizhi:
            return event.plain_result("当前还没有该图库，使用 '新建<名称>' 来创建一个！")
        else:
            response = f"来只列表 (共 {stats['total_laizhi']} 个):\n\n"
            for laizhi in all_laizhi:
                # 获取实际图片数量
                actual_count = 0
                if self.photo_db:
                    actual_count = await self.photo_db.get_image_count(laizhi.name)

                response += f"- {laizhi.name} - 计数: {laizhi.image_count}, 实际文件: {actual_count}\n"
            response += f"\n使用 '查询<名称>' 查看详细信息，'来只<名称>' 随机获取图片"
            return event.plain_result(response)