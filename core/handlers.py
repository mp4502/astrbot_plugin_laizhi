"""
来只插件命令处理器
包含命令处理的业务逻辑
"""
from astrbot.api.event import AstrMessageEvent
from astrbot.api import logger
from .image_context import get_image_context_manager
from .database import ImageInfo


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
        session_id = event.session_id
        name = event.message_str.removeprefix("新建")
        real_name = await self.db.resolve_name(name, session_id)
        if real_name:
            return event.plain_result(f"图库 '{name}' 已存在！")

        success = await self.db.add_laizhi(name, session_id)
        if success:
            return event.plain_result(f"新建 '{name}' 成功！")
        else:
            return event.plain_result(f"新建 '{name}' 失败！")

    async def handle_laizhi(self, event: AstrMessageEvent):
        """处理来只命令的业务逻辑 - 随机发送图片"""
        session_id = event.session_id
        name = event.message_str.removeprefix("来只")
        real_name = await self.db.resolve_name(name, session_id)
        if not real_name:
            return event.plain_result(f"未找到 '{name}'，请先使用 '新建{name}' 创建！")

        # 更新最后使用时间
        await self.db.update_laizhi(real_name, session_id, last_used=True)

        # 如果有图片数据库，尝试获取随机图片
        if self.photo_db:
            image_path = await self.photo_db.get_random_image(real_name, session_id)
            if image_path:
                # 获取图片信息用于记录
                laizhi_info = await self.db.get_laizhi(real_name, session_id)

                # 计算图片哈希
                import hashlib
                with open(image_path, 'rb') as f:
                    image_hash = hashlib.sha256(f.read()).hexdigest()

                # 记录发送的图片信息：图片路径 -> 图库名映射
                if self.image_context_manager:
                    try:
                        # 记录映射：图片哈希 -> (session_id, laizhi_name)
                        self.image_context_manager.add_sent_image(
                            event,
                            image_hash,
                            real_name,
                            image_path
                        )
                        logger.info(f"记录发送图片: 哈希={image_hash[:8]}, 图库={real_name}")
                    except Exception as e:
                        logger.warning(f"记录图片映射失败: {e}")

                # 发送图片
                try:
                    return event.image_result(image_path)
                except Exception as e:
                    logger.error(f"发送图片失败: {e}")
                    return event.plain_result(f"发送图片失败: {str(e)}")
            else:
                laizhi_info = await self.db.get_laizhi(real_name, session_id)
                aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
                return event.plain_result(
                    f"提示: 该图库暂无图片，使用 '添加{real_name}' 来添加图片"
                )
        else:
            # 没有图片数据库时的逻辑
            laizhi_info = await self.db.get_laizhi(real_name, session_id)
            aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
            return event.plain_result(
                f"图库 '{real_name}' 未创建"
            )

    async def handle_add(self, event: AstrMessageEvent):
        """处理添加命令的业务逻辑 - 从聊天记录中获取图片"""
        session_id = event.session_id
        name = event.message_str.removeprefix("添加")
        real_name = await self.db.resolve_name(name, session_id)
        if not real_name:
            return event.plain_result(f"'{name}' 不存在，请先使用 '新建{name}' 创建！")

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
        download_result = await self.photo_db.download_image(real_name, image_url, session_id)
        if download_result:
            local_path, image_hash = download_result

            # 检查图片是否已存在（通过哈希值）
            laizhi_info = await self.db.get_laizhi(real_name, session_id)
            if image_hash in laizhi_info.image_hashes:
                return event.plain_result(f"该图片已存在！图库 '{real_name}' 当前总数: {laizhi_info.image_count}")

            # 获取添加者信息
            from datetime import datetime
            adder_name = getattr(event, 'sender_name', '') or getattr(event, 'nickname', '') or ''
            adder_qq = str(getattr(event, 'user_id', ''))

            # 创建图片信息
            from .database import ImageInfo
            image_info = ImageInfo(
                hash=image_hash,
                adder_name=adder_name,
                adder_qq=adder_qq,
                add_time=datetime.now().isoformat(),
                file_path=local_path
            )

            # 更新数据库中的图片计数、哈希列表和图片信息
            new_count = laizhi_info.image_count + 1
            new_hashes = laizhi_info.image_hashes + [image_hash]
            new_image_infos = laizhi_info.image_infos + [image_info]
            await self.db.update_laizhi(real_name, session_id, image_count=new_count)
            await self.db._update_hashes(real_name, new_hashes, session_id)
            await self.db._update_image_infos(real_name, new_image_infos, session_id)

            logger.info(f"成功添加图片到 '{real_name}', 添加者: {adder_name}({adder_qq}), 哈希: {image_hash[:8]}, 当前总数: {new_count}")
            return event.plain_result(f"添加图片成功！\n当前总数: {new_count}{session_info}")
        else:
            return event.plain_result(f"图片下载失败: {image_url}")

    async def handle_alias(self, event: AstrMessageEvent):
        """处理别名命令的业务逻辑"""
        session_id = event.session_id
        import re
        match = re.match(r"^别名(\S+)(?:\s+(.+))?$", event.message_str)
        if not match:
            return None

        name = match.group(1)
        alias = match.group(2) if match.group(2) else None

        real_name = await self.db.resolve_name(name, session_id)
        if not real_name:
            return event.plain_result(f"'{name}' 不存在！")

        laizhi_info = await self.db.get_laizhi(real_name, session_id)

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
                success = await self.db.delete_alias(name, alias_to_delete, session_id)
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
                success = await self.db.add_alias(real_name, alias, session_id)
                if success:
                    return event.plain_result(f"为 '{real_name}' 添加别名 '{alias}' 成功！")
                else:
                    return event.plain_result(f"添加别名失败！别名 '{alias}' 可能已存在")
        else:
            # 查询别名列表
            aliases = await self.db.get_aliases(real_name, session_id)
            if aliases:
                alias_list = "\n".join(f"- {alias}" for alias in aliases)
                return event.plain_result(f"'{real_name}' 的别名列表：\n{alias_list}")
            else:
                return event.plain_result(f"'{real_name}' 暂无别名")

    async def handle_delete(self, event: AstrMessageEvent):
        """处理删除命令的业务逻辑 - 回复机器人发送的图片即可删除"""
        import hashlib

        # 尝试获取图片URL或路径
        image_url = None
        image_file = None

        # 1. 优先从图片上下文管理器获取
        if self.image_context_manager:
            try:
                image_url = self.image_context_manager.get_recent_image(event)
            except:
                pass

        # 2. 如果上下文管理器没有，尝试从消息中获取
        if not image_url:
            messages = event.get_messages()
            for comp in messages:
                if hasattr(comp, 'file') and comp.file:
                    image_file = comp.file
                    break
                if hasattr(comp, 'url') and comp.url:
                    image_url = comp.url
                    break

        if not image_url and not image_file:
            return event.plain_result(f"使用方法：\n回复机器人发送的图片后发送 '删除' 即可删除")

        # 计算图片哈希
        target_path = image_file if image_file else image_url

        # 如果是本地路径，直接计算哈希
        if target_path and ('images' in target_path or 'plugin_data' in target_path or target_path.startswith('/')):
            try:
                with open(target_path, 'rb') as f:
                    image_hash = hashlib.sha256(f.read()).hexdigest()

                # 查询机器人发送的图片记录
                if self.image_context_manager:
                    sent_info = self.image_context_manager.get_sent_image_info(image_hash)
                    if sent_info:
                        session_id, laizhi_name, _ = sent_info
                        real_name = await self.db.resolve_name(laizhi_name, session_id)

                        if real_name:
                            # 删除图片
                            deleted_hash = await self.photo_db.delete_image_by_url(real_name, target_path, session_id)
                            if deleted_hash:
                                # 更新计数、哈希列表和图片信息
                                laizhi_info = await self.db.get_laizhi(real_name, session_id)
                                new_count = max(0, laizhi_info.image_count - 1)
                                new_hashes = [h for h in laizhi_info.image_hashes if h != deleted_hash]
                                new_image_infos = [info for info in laizhi_info.image_infos if info.hash != deleted_hash]
                                await self.db.update_laizhi(real_name, session_id, image_count=new_count)
                                await self.db._update_hashes(real_name, new_hashes, session_id)
                                await self.db._update_image_infos(real_name, new_image_infos, session_id)

                                # 获取删除的图片添加者信息
                                deleted_info = next((info for info in laizhi_info.image_infos if info.hash == deleted_hash), None)
                                adder_msg = ""
                                if deleted_info:
                                    adder_name = deleted_info.adder_name or "未知"
                                    adder_msg = f"（添加者: {adder_name}）"

                                return event.plain_result(f"删除图片成功{adder_msg}！图库 '{real_name}' 剩余 {new_count} 张图片")

                return event.plain_result(f"删除图片失败！未找到该图片的发送记录，只能删除机器人发送的图片")
            except Exception as e:
                logger.error(f"删除图片异常: {e}")
                return event.plain_result(f"删除图片失败！{str(e)}")
        else:
            return event.plain_result(f"删除图片失败！只支持删除机器人发送的图片")


    async def handle_query(self, event: AstrMessageEvent):
        """处理查询命令的业务逻辑"""
        session_id = event.session_id
        name = event.message_str.removeprefix("查询")
        real_name = await self.db.resolve_name(name, session_id)
        if not real_name:
            return event.plain_result(f"未找到 '{name}'")

        laizhi_info = await self.db.get_laizhi(real_name, session_id)
        aliases_str = ", ".join(laizhi_info.aliases) if laizhi_info.aliases else "无"
        original_name = f" (原名: {real_name})" if real_name != name else ""

        # 获取实际图片数量
        actual_image_count = 0
        if self.photo_db:
            actual_image_count = await self.photo_db.get_image_count(real_name, session_id)

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
        session_id = event.session_id
        all_laizhi = await self.db.list_all_laizhi(session_id)
        stats = await self.db.get_statistics(session_id)

        if not all_laizhi:
            return event.plain_result("当前还没有该图库，使用 '新建<名称>' 来创建一个！")
        else:
            response = f"列表 (共 {stats['total_laizhi']} 个):\n\n"
            for laizhi in all_laizhi:
                # 获取实际图片数量
                actual_count = 0
                if self.photo_db:
                    actual_count = await self.photo_db.get_image_count(laizhi.name, session_id)

                response += f"- {laizhi.name} - 计数: {laizhi.image_count}, 实际文件: {actual_count}\n"
            response += f"\n使用 '查询<名称>' 查看详细信息，'来只<名称>' 随机获取图片"
            return event.plain_result(response)

    async def handle_who_added(self, event: AstrMessageEvent):
        """处理'谁添加的'命令 - 查询图片添加者信息"""
        import hashlib

        # 尝试获取图片URL或路径
        image_url = None
        image_file = None

        # 1. 优先从图片上下文管理器获取
        if self.image_context_manager:
            try:
                image_url = self.image_context_manager.get_recent_image(event)
            except:
                pass

        # 2. 如果上下文管理器没有，尝试从消息中获取
        if not image_url:
            messages = event.get_messages()
            for comp in messages:
                if hasattr(comp, 'file') and comp.file:
                    image_file = comp.file
                    break
                if hasattr(comp, 'url') and comp.url:
                    image_url = comp.url
                    break

        if not image_url and not image_file:
            return event.plain_result(f"使用方法：\n回复机器人发送的图片后发送 '谁添加的' 查询添加者信息")

        # 计算图片哈希
        target_path = image_file if image_file else image_url

        # 如果是本地路径，直接计算哈希
        if target_path and ('images' in target_path or 'plugin_data' in target_path or target_path.startswith('/')):
            try:
                with open(target_path, 'rb') as f:
                    image_hash = hashlib.sha256(f.read()).hexdigest()

                # 查询机器人发送的图片记录
                if self.image_context_manager:
                    sent_info = self.image_context_manager.get_sent_image_info(image_hash)
                    if sent_info:
                        session_id, laizhi_name, _ = sent_info
                        real_name = await self.db.resolve_name(laizhi_name, session_id)

                        if real_name:
                            # 查找添加者信息
                            laizhi_info = await self.db.get_laizhi(real_name, session_id)
                            for img_info in laizhi_info.image_infos:
                                if img_info.hash == image_hash:
                                    adder_name = img_info.adder_name or "未知"
                                    adder_qq = img_info.adder_qq or "未知"
                                    add_time = img_info.add_time or "未知"

                                    # 格式化时间显示
                                    try:
                                        from datetime import datetime
                                        dt = datetime.fromisoformat(add_time)
                                        time_str = dt.strftime("%Y-%m-%d %H:%M")
                                    except:
                                        time_str = add_time

                                    return event.plain_result(
                                        f"图片信息：\n"
                                        f"图库: {real_name}\n"
                                        f"添加者: {adder_name}\n"
                                        f"QQ号: {adder_qq}\n"
                                        f"添加时间: {time_str}"
                                    )

                return event.plain_result(f"未找到该图片的添加记录，只能查询机器人发送的图片")
            except Exception as e:
                logger.error(f"查询添加者异常: {e}")
                return event.plain_result(f"查询失败！{str(e)}")
        else:
            return event.plain_result(f"查询失败！只支持查询机器人发送的图片")