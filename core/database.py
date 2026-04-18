"""
来只插件数据库模块
包含数据模型和数据库操作类
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

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
        aliases: list = None,
        image_hashes: list = None,
    ):
        self.name = name
        self.created_at = created_at or datetime.now().isoformat()
        self.image_count = image_count
        self.last_used = last_used or datetime.now().isoformat()
        self.description = description
        self.aliases = aliases or []
        self.image_hashes = image_hashes or []

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "created_at": self.created_at,
            "image_count": self.image_count,
            "last_used": self.last_used,
            "description": self.description,
            "aliases": self.aliases,
            "image_hashes": self.image_hashes,
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
            image_hashes=data.get("image_hashes", []),
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
            with open(self.db_path, "w", encoding="utf-8") as f:
                f.write("{}")
            logger.info(f"来只数据库已初始化: {self.db_path}")
            return

        # 验证现有文件格式
        try:
            with open(self.db_path, encoding="utf-8") as f:
                data = f.read()
            parsed = json.loads(data)
            if not isinstance(parsed, dict):
                raise ValueError("数据库格式错误")
        except Exception as e:
            logger.warning(f"来只数据库文件损坏，重新初始化: {e}")
            with open(self.db_path, "w", encoding="utf-8") as f:
                f.write("{}")

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

        await self._save_data(data)
        return True

    async def _update_hashes(self, name: str, hashes: list) -> bool:
        """更新图片哈希列表"""
        data = await self._load_data()
        if name not in data:
            return False

        data[name]["image_hashes"] = hashes
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

    async def resolve_name(self, name_or_alias: str) -> Optional[str]:
        """解析名称或别名，返回真实的来只名称"""
        # 先检查是否是真实的来只名称
        data = await self._load_data()
        if name_or_alias in data:
            return name_or_alias

        # 如果不是真实名称，检查是否是别名
        for real_name, info in data.items():
            if "aliases" in info and name_or_alias in info["aliases"]:
                return real_name

        return None

    async def add_alias(self, name: str, alias: str) -> bool:
        """添加别名"""
        data = await self._load_data()
        if name not in data:
            return False

        # 检查别名是否已存在（包括与其他来只的别名冲突）
        for real_name, info in data.items():
            if "aliases" in info and alias in info["aliases"]:
                return False

        if "aliases" not in data[name]:
            data[name]["aliases"] = []
        if alias not in data[name]["aliases"]:
            data[name]["aliases"].append(alias)
        await self._save_data(data)
        return True

    async def get_aliases(self, name: str) -> list:
        """获取别名列表"""
        laizhi_info = await self.get_laizhi(name)
        return laizhi_info.aliases if laizhi_info else []

    async def delete_alias(self, name_or_alias: str, alias_to_delete: str) -> bool:
        """
        删除别名（允许删除主名称，只要至少保留一个名称）
        :param name_or_alias: 用来访问的名称或别名
        :param alias_to_delete: 要删除的别名
        :return: 删除成功返回True，失败返回False
        """
        # 解析真实名称
        real_name = await self.resolve_name(name_or_alias)
        if not real_name:
            return False

        data = await self._load_data()
        if real_name not in data:
            return False

        # 获取当前的所有名称（主名称 + 别名）
        current_aliases = data[real_name].get("aliases", [])

        # 检查要删除的名称是主名称还是别名
        if alias_to_delete == real_name:
            # 要删除的是主名称
            if not current_aliases:
                # 没有其他名称，不能删除
                return False

            # 有其他别名，将第一个别名提升为主名称
            new_primary = current_aliases[0]
            remaining_aliases = current_aliases[1:]

            # 创建新条目
            data[new_primary] = data[real_name].copy()
            data[new_primary]["name"] = new_primary
            data[new_primary]["aliases"] = remaining_aliases

            # 删除旧条目
            del data[real_name]

            await self._save_data(data)
            return True
        else:
            # 要删除的是别名
            if alias_to_delete not in current_aliases:
                return False

            # 只有一个名称（没有别名），不能删除
            if not current_aliases:
                return False

            # 从别名列表中删除
            current_aliases.remove(alias_to_delete)
            data[real_name]["aliases"] = current_aliases

            await self._save_data(data)
            return True

    async def _load_data(self) -> dict:
        """加载数据"""
        if not self.db_path.exists():
            return {}

        try:
            with open(self.db_path, encoding="utf-8") as f:
                raw = f.read()
            return json.loads(raw) if raw else {}
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {e}")
            return {}

    async def _save_data(self, data: dict):
        """保存数据"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.db_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=4, ensure_ascii=False))
