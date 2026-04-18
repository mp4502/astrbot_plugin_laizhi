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
    """图片数据库管理类"""

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

    def _get_laizhi_folder(self, laizhi_name: str) -> Path:
        """获取来只的图片文件夹路径"""
        # 清理文件名，移除不安全的字符
        safe_name = "".join(c if c.isalnum() or c in ('-', '_', ' ') else '_' for c in laizhi_name)
        folder_path = self.base_path / safe_name
        return folder_path

    async def download_image(self, laizhi_name: str, image_url: str) -> Optional[str]:
        """
        下载图片到本地
        :param laizhi_name: 来只名称
        :param image_url: 图片URL
        :return: 下载成功返回本地文件路径，失败返回None
        """
        try:
            # 创建来只文件夹
            folder_path = self._get_laizhi_folder(laizhi_name)
            folder_path.mkdir(parents=True, exist_ok=True)

            # 从URL中提取文件名
            parsed_url = urlparse(image_url)
            filename = os.path.basename(parsed_url.path)

            # 如果URL没有文件名，生成一个
            if not filename or '.' not in filename:
                import time
                filename = f"image_{int(time.time())}.jpg"

            local_path = folder_path / filename

            # 如果文件已存在，添加序号
            if local_path.exists():
                base_name = local_path.stem
                extension = local_path.suffix
                counter = 1
                while local_path.exists():
                    local_path = folder_path / f"{base_name}_{counter}{extension}"
                    counter += 1

            # 下载图片
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        content = await response.read()

                        # 保存到本地
                        async with aiofiles.open(local_path, 'wb') as f:
                            await f.write(content)

                        logger.info(f"图片下载成功: {local_path}")
                        return str(local_path)
                    else:
                        logger.error(f"图片下载失败，HTTP状态码: {response.status}")
                        return None

        except Exception as e:
            logger.error(f"图片下载异常: {e}")
            return None

    async def add_local_image(self, laizhi_name: str, local_image_path: str) -> Optional[str]:
        """
        添加本地图片到数据库（复制）
        :param laizhi_name: 来只名称
        :param local_image_path: 本地图片路径
        :return: 成功返回新文件路径，失败返回None
        """
        try:
            # 创建来只文件夹
            folder_path = self._get_laizhi_folder(laizhi_name)
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

    async def get_random_image(self, laizhi_name: str) -> Optional[str]:
        """
        随机获取一张图片路径
        :param laizhi_name: 来只名称
        :return: 图片路径，如果没有图片返回None
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name)

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

    async def get_all_images(self, laizhi_name: str) -> List[str]:
        """
        获取来只的所有图片路径
        :param laizhi_name: 来只名称
        :return: 图片路径列表
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name)

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

    async def delete_image(self, laizhi_name: str, image_filename: str) -> bool:
        """
        删除指定图片
        :param laizhi_name: 来只名称
        :param image_filename: 图片文件名
        :return: 删除成功返回True，失败返回False
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name)

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

    async def delete_image_by_url(self, laizhi_name: str, image_url: str) -> bool:
        """
        根据图片URL删除对应的本地文件
        :param laizhi_name: 来只名称
        :param image_url: 图片URL或本地路径
        :return: 删除成功返回True，失败返回False
        """
        try:
            from urllib.parse import urlparse

            folder_path = self._get_laizhi_folder(laizhi_name)

            if not folder_path.exists():
                logger.warning(f"来只 '{laizhi_name}' 的图片文件夹不存在")
                return False

            image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

            # 检查是否是本地路径
            if image_url.startswith(('file://', '/', '\\')) or 'plugin_data' in image_url or 'images' in image_url:
                # 是本地路径
                # 清理路径前缀
                clean_path = image_url.replace('file://', '').replace('\\', '/')

                # 提取文件名
                filename = Path(clean_path).name

                # 尝试删除该文件
                image_path = folder_path / filename
                if image_path.exists():
                    image_path.unlink()
                    logger.info(f"根据本地路径删除图片成功: {image_path}")
                    return True
                else:
                    logger.warning(f"文件不存在: {image_path}")
                    return False
            else:
                # 是网络URL，尝试匹配文件名
                parsed_url = urlparse(image_url)
                url_filename = Path(parsed_url.path).name

                # 如果URL有有效的文件名，尝试匹配
                if url_filename and '.' in url_filename:
                    test_path = folder_path / url_filename
                    if test_path.exists():
                        test_path.unlink()
                        logger.info(f"根据URL删除图片成功: {test_path}")
                        return True

                # 如果无法匹配，删除最近的一张图片
                image_files = [
                    f for f in folder_path.iterdir()
                    if f.is_file() and f.suffix.lower() in image_extensions
                ]

                if image_files:
                    # 按修改时间排序，删除最新的
                    image_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    latest_image = image_files[0]
                    latest_image.unlink()
                    logger.info(f"删除最近的图片: {latest_image}")
                    return True
                else:
                    logger.warning(f"没有找到可删除的图片")
                    return False

        except Exception as e:
            logger.error(f"根据URL删除图片异常: {e}")
            return False

    async def delete_all_images(self, laizhi_name: str) -> int:
        """
        删除来只的所有图片
        :param laizhi_name: 来只名称
        :return: 删除的图片数量
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name)

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

    async def get_image_count(self, laizhi_name: str) -> int:
        """
        获取来只的图片数量
        :param laizhi_name: 来只名称
        :return: 图片数量
        """
        images = await self.get_all_images(laizhi_name)
        return len(images)

    async def delete_laizhi_folder(self, laizhi_name: str) -> bool:
        """
        删除来只的整个文件夹（包括所有图片）
        :param laizhi_name: 来只名称
        :return: 删除成功返回True
        """
        try:
            folder_path = self._get_laizhi_folder(laizhi_name)

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