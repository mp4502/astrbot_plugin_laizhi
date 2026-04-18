import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from astrbot.api import logger


class LaizhiInfo:
    """来只信息数据类"""

    def __init__(
        self,
        name: str,
        created_at: str = None,
        image_count: int = 0,
        last_used: str = None,
        description: str = "",
        aliases: list[str] = None,
    ):
        self.name = name
        self.created_at = created_at or datetime.now().isoformat()
        self.image_count = image_count
        self.last_used = last_used or datetime.now().isoformat()
        self.description = description
        self.aliases = aliases or []
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "created_at": self.created_at,
            "image_count": self.image_count,
            "last_used": self.last_used,
            "description": self.description,
            "aliases": self.aliases,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LaizhiInfo":
        """从字典创建实例"""
        return cls(
            name=data["name"],
            created_at=data.get("created_at"),
            image_count=data.get("image_count", 0),
            last_used=data.get("last_used"),
            description=data.get("description", ""),
            aliases=data.get("aliases", []),
        )


class LaizhiDB:
    """来只插件数据库 - 基于 JSON 存储"""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            # 默认存储在插件 data 目录下
            self.db_path = Path(__file__).parent.parent / "data" / "laizhi_db.json"
        else:
            self.db_path = db_path

    async def initialize(self):
        """初始化数据库文件"""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(self.db_path, "w", encoding="utf-8") as f:
                await f.write("{}")
            logger.info(f"来只数据库已初始化: {self.db_path}")
            return

        # 验证现有文件格式
        try:
            async with aiofiles.open(self.db_path, encoding="utf-8") as f:
                data = await f.read()
            parsed = json.loads(data)
            if not isinstance(parsed, dict):
                raise ValueError("数据库格式错误")
        except Exception as e:
            logger.warning(f"来只数据库文件损坏，重新初始化: {e}")
            async with aiofiles.open(self.db_path, "w", encoding="utf-8") as f:
                await f.write("{}")

    async def add_laizhi(self, name: str, description: str = "") -> bool:
        """添加新的来只"""
        data = await self._load_data()
        if name in data:
            logger.warning(f"来只 '{name}' 已存在")
            return False

        laizhi_info = LaizhiInfo(name=name, description=description)
        data[name] = laizhi_info.to_dict()
        await self._save_data(data)
        logger.info(f"成功添加来只: {name}")
        return True

    async def get_laizhi(self, name: str) -> Optional[LaizhiInfo]:
        """获取指定来只的信息"""
        data = await self._load_data()
        if name not in data:
            return None
        return LaizhiInfo.from_dict(data[name])

    async def update_laizhi(
        self,
        name: str,
        image_count: int = None,
        last_used: bool = True,
        description: str = None,
        aliases: list[str] = None,
    ) -> bool:
        """更新来只信息"""
        data = await self._load_data()
        if name not in data:
            return False

        if image_count is not None:
            data[name]["image_count"] = image_count
        if last_used:
            data[name]["last_used"] = datetime.now().isoformat()
        if description is not None:
            data[name]["description"] = description
        if aliases is not None:
            data[name]["aliases"] = aliases
        await self._save_data(data)
        return True

    async def delete_laizhi(self, name: str) -> bool:
        """删除来只"""
        data = await self._load_data()
        if name not in data:
            return False

        del data[name]
        await self._save_data(data)
        logger.info(f"成功删除来只: {name}")
        return True

    async def list_all_laizhi(self) -> list[LaizhiInfo]:
        """获取所有来只列表"""
        data = await self._load_data()
        return [LaizhiInfo.from_dict(item) for item in data.values()]

    async def get_statistics(self) -> dict:
        """获取数据库统计信息"""
        data = await self._load_data()
        total_count = len(data)
        total_images = sum(item.get("image_count", 0) for item in data.values())

        return {
            "total_laizhi": total_count,
            "total_images": total_images,
            "latest_created": (
                max((item["created_at"] for item in data.values()))
                if data
                else None
            ),
        }

    async def _load_data(self) -> dict:
        """加载数据"""
        if not self.db_path.exists():
            return {}

        try:
            async with aiofiles.open(self.db_path, encoding="utf-8") as f:
                raw = await f.read()
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return {}

    async def _save_data(self, data: dict):
        """保存数据"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(self.db_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=4, ensure_ascii=False))
