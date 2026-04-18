"""
来只插件图片数据库模块
负责图片的下载、存储和管理
"""
import os
import random
import aiofiles
import aiohttp
from pathlib import Path
from typing import Optional, List
from urllib.parse import urlparse
from astrbot.api import logger


class PhotoDatabase:
    """图片数据库管理类，支持会话隔离"""

    def __init__(self, base_path: Path = None):
        if base_path is None:
            # 默认存储在插件 data/images 目录下
            self.base_path = Path(__file__).parent.parent / "data" / "images"
        else:
            self.base_path = base_path

    async def initialize(self):
        """初始化图片目录"""
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"图片数据库已初始化: {self.base_path}")

    def _get_laizhi_folder(self, laizhi_name: str, session_id: str = "default") -> Path:
        """获取来只的图片文件夹路径"""
        # 清理文件名，移除不安全的字符
        safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '_' for c in laizhi_name)
        # 按会话隔离：session_id/laizhi_name
        session_folder = self.base_path / session_id
        folder_path = session_folder / safe_name
        return folder_path

    def _calculate_hash(self, content: bytes) -> str:
        """计算图片内容的哈希值"""
        import hashlib
        return hashlib.sha256(content).hexdigest()

    async def download_image(self, laizhi_name: str, image_url: str, session_id: str = "default") -> Optional[tuple]:
        """
        下载图片到本地（先下载到临时位置计算哈希）
        :param laizhi_name: 来只名称
        :param image_url: 图片URL
        :param session_id: 会话ID
        :return: 下载成功返回 (本地文件路径, 哈希值)，失败返回None
        """
        import tempfile
        import os

        try:
            # 1. 先下载到临时文件
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(f"图片下载失败，HTTP状态码: {response.status}")
                        return None

                    content = await response.read()

                    # 2. 计算哈希值
                    image_hash = self._calculate_hash(content)

                    # 3. 保存到临时文件
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                        tmp_file.write(content)
                        tmp_file.flush()
                        temp_path = tmp_file.name

                    logger.info(f"图片下载到临时文件: {temp_path}, 哈希: {image_hash[:8]}")

                    # 4. 检查是否已存在（通过哈希文件名）
                    folder_path = self._get_laizhi_folder(laizhi_name, session_id)
                    folder_path.mkdir(parents=True, exist_ok=True)

                    # 尝试不同的扩展名
                    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
                    hash_file_exists = False
                    hash_path = None

                    for ext in image_extensions:
                        potential_path = folder_path / f"{image_hash[:8]}{ext}"
                        if potential_path.exists():
                            hash_path = potential_path
                            hash_file_exists = True
                            break

                    # 5. 删除临时文件
                    try:
                        os.unlink(temp_path)
                        logger.info(f"已删除临时文件: {temp_path}")
                    except Exception as e:
                        logger.warning(f"删除临时文件失败: {e}")

                    # 6. 如果已存在，返回现有路径
                    if hash_file_exists:
                        logger.info(f"图片已存在（哈希重复）: {hash_path}")
                        return str(hash_path), image_hash

                    # 7. 如果不存在，从哈希和原始文件名确定扩展名
                    # 尝试从URL获取扩展名
                    from urllib.parse import urlparse
                    parsed_url = urlparse(image_url)
                    url_filename = os.path.basename(parsed_url.path)
                    ext = os.path.splitext(url_filename)[1].lower()

                    # 如果URL没有扩展名或扩展名不支持，使用默认
                    if ext not in image_extensions:
                        # 根据内容类型判断（简单实现：默认jpg）
                        ext = '.jpg'

                    # 8. 重新下载并保存到最终位置
                    final_path = folder_path / f"{image_hash[:8]}{ext}"
                    async with aiofiles.open(final_path, 'wb') as f:
                        await f.write(content)

                    logger.info(f"图片保存成功: {final_path}, 哈希: {image_hash[:8]}")
                    return str(final_path), image_hash

        except Exception as e:
            logger.error(f"图片下载异常: {e}")
            return None

    async def add_local_image(self, laizhi_name: str, local_image_path: str, session_id: str = "default") -> Optional[str]:
        """
        添加本地图片到数据库（复制）
        :param laizhi_name: 来只名称
        :param local_image_path: 本地图片路径
        :return: 成功返回新文件路径，失败返回None
        """
        try:
            # 创建来只文件夹
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)
            folder_path.mkdir(parents=True, exist_ok=True)

            # 获取原文件名
            original_path = Path(local_image_path)
            if not original_path.exists():
                logger.error(f"源文件不存在: {local_image_path}")
                return None

            filename = original_path.name
            new_path = folder_path / filename

            # 如果文件已存在，添加序号
            if new_path.exists():
                base_name = new_path.stem
                extension = new_path.suffix
                counter = 1
                while new_path.exists():
                    new_path = folder_path / f"{base_name}_{counter}{extension}"
                    counter += 1

            # 复制文件
            async with aiofiles.open(local_image_path, 'rb') as src_file:
                content = await src_file.read()

            async with aiofiles.open(new_path, 'wb') as dst_file:
                await dst_file.write(content)

            logger.info(f"图片复制成功: {new_path}")
            return str(new_path)

        except Exception as e:
            logger.error(f"图片复制异常: {e}")
            return None

    async def get_random_image(self, laizhi_name: str, session_id: str = "default") -> Optional[str]:
        """
        随机获取一张图片路径
        :param laizhi_name: 来只名称
        :return: 图片路径，如果没有图片返回None
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)

            if not folder_path.exists():
                logger.warning(f"来只 '{laizhi_name}' 的图片文件夹不存在")
                return None

            # 获取所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
            image_files = [
                f for f in folder_path.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            if not image_files:
                logger.warning(f"来只 '{laizhi_name}' 没有图片")
                return None

            # 随机选择一张图片
            random_image = random.choice(image_files)
            logger.info(f"为 '{laizhi_name}' 随机选择图片: {random_image}")
            return str(random_image)

        except Exception as e:
            logger.error(f"获取随机图片异常: {e}")
            return None

    async def get_all_images(self, laizhi_name: str, session_id: str = "default") -> List[str]:
        """
        获取来只的所有图片路径
        :param laizhi_name: 来只名称
        :return: 图片路径列表
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)

            if not folder_path.exists():
                return []

            # 获取所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
            image_files = [
                str(f) for f in folder_path.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            return image_files

        except Exception as e:
            logger.error(f"获取图片列表异常: {e}")
            return []

    async def delete_image(self, laizhi_name: str, image_filename: str, session_id: str = "default") -> bool:
        """
        删除指定图片
        :param laizhi_name: 来只名称
        :param image_filename: 图片文件名
        :return: 删除成功返回True，失败返回False
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)

            if not folder_path.exists():
                logger.warning(f"来只 '{laizhi_name}' 的图片文件夹不存在")
                return False

            image_path = folder_path / image_filename

            if not image_path.exists():
                logger.warning(f"图片文件不存在: {image_path}")
                return False

            # 删除文件
            image_path.unlink()
            logger.info(f"图片删除成功: {image_path}")
            return True

        except Exception as e:
            logger.error(f"删除图片异常: {e}")
            return False

    async def delete_image_by_url(self, laizhi_name: str, image_url: str, session_id: str = "default") -> Optional[str]:
        """
        根据图片URL计算哈希值并删除对应的本地文件
        :param laizhi_name: 来只名称
        :param image_url: 图片URL
        :return: 删除成功返回图片哈希值，失败返回None
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)

            if not folder_path.exists():
                logger.warning(f"来只 '{laizhi_name}' 的图片文件夹不存在")
                return None

            # 1. 如果是本地路径，直接读取文件计算哈希
            if image_url.startswith(('file://', '/', '\\')) or 'plugin_data' in image_url or 'images' in image_url:
                # 清理路径前缀
                clean_path = image_url.replace('file://', '').replace('\\', '/')
                image_path = Path(clean_path)

                # 尝试读取文件内容计算哈希
                if image_path.exists():
                    # 读取文件内容计算哈希
                    async with aiofiles.open(image_path, 'rb') as f:
                        content = await f.read()
                    image_hash = self._calculate_hash(content)
                else:
                    # 文件不存在，尝试从文件名提取哈希（如果是哈希文件名）
                    filename = image_path.stem  # 获取不带扩展名的文件名
                    if len(filename) == 8 and all(c in '0123456789abcdefABCDEF' for c in filename):
                        # 这是一个哈希文件名，但需要完整的 SHA256 哈希
                        # 这种情况下无法确定完整哈希，返回特殊标记
                        logger.warning(f"文件不存在且无法从哈希文件名推断完整哈希: {image_path}")
                        return None
                    else:
                        logger.warning(f"本地文件不存在且不是哈希文件名: {image_path}")
                        return None

                # 根据哈希值查找并删除文件（尝试所有扩展名）
                image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
                deleted = False
                for ext in image_extensions:
                    hash_path = folder_path / f"{image_hash[:8]}{ext}"
                    if hash_path.exists():
                        hash_path.unlink()
                        logger.info(f"根据本地路径删除图片成功: {hash_path}")
                        deleted = True
                        break  # 找到并删除后退出循环

                # 即使文件不存在，只要能计算出哈希，就返回哈希值以便更新数据库
                if deleted:
                    return image_hash
                else:
                    logger.warning(f"未找到哈希匹配的文件，但返回哈希用于数据库更新: {image_hash[:8]}")
                    return image_hash

            # 2. 如果是网络URL，下载并计算哈希后删除
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        content = await response.read()
                        image_hash = self._calculate_hash(content)

                        # 根据哈希值查找并删除文件（尝试所有扩展名）
                        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
                        for ext in image_extensions:
                            hash_path = folder_path / f"{image_hash[:8]}{ext}"
                            if hash_path.exists():
                                hash_path.unlink()
                                logger.info(f"根据网络URL哈希删除图片成功: {hash_path}")
                                return image_hash

                        logger.warning(f"未找到哈希匹配的文件: {image_hash[:8]}")
                        return None
                    else:
                        logger.error(f"无法下载图片计算哈希，HTTP状态码: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"根据哈希删除图片异常: {e}")
            return None

    async def delete_all_images(self, laizhi_name: str, session_id: str = "default") -> int:
        """
        删除来只的所有图片
        :param laizhi_name: 来只名称
        :return: 删除的图片数量
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)

            if not folder_path.exists():
                return 0

            # 获取所有图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
            image_files = [
                f for f in folder_path.iterdir()
                if f.is_file() and f.suffix.lower() in image_extensions
            ]

            # 删除所有图片
            deleted_count = 0
            for image_file in image_files:
                try:
                    image_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"删除图片失败: {image_file}, 错误: {e}")

            logger.info(f"为 '{laizhi_name}' 删除了 {deleted_count} 张图片")
            return deleted_count

        except Exception as e:
            logger.error(f"批量删除图片异常: {e}")
            return 0

    async def get_image_count(self, laizhi_name: str, session_id: str = "default") -> int:
        """
        获取来只的图片数量
        :param laizhi_name: 来只名称
        :return: 图片数量
        """
        images = await self.get_all_images(laizhi_name)
        return len(images)

    async def delete_laizhi_folder(self, laizhi_name: str, session_id: str = "default") -> bool:
        """
        删除来只的整个文件夹（包括所有图片）
        :param laizhi_name: 来只名称
        :return: 删除成功返回True
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name, session_id)

            if not folder_path.exists():
                return True  # 文件夹不存在，视为删除成功

            # 删除整个文件夹
            import shutil
            shutil.rmtree(folder_path)
            logger.info(f"删除来只 '{laizhi_name}' 的图片文件夹: {folder_path}")
            return True

        except Exception as e:
            logger.error(f"删除文件夹异常: {e}")
            return False