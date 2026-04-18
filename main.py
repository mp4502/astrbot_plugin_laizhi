from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class LaizhiInfo:
    """来只信息数据类"""

    def __init__(
        self,
        name: str,
        created_at: str = None,
        image_count: int = 0,
        last_used: str = None,
        description: str = "",
    ):
        self.name = name
        self.created_at = created_at or datetime.now().isoformat()
        self.image_count = image_count
        self.last_used = last_used or datetime.now().isoformat()
        self.description = description

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "name": self.name,
            "created_at": self.created_at,
            "image_count": self.image_count,
            "last_used": self.last_used,
            "description": self.description,
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
        )


class LaizhiDB:
    """来只插件数据库 - 基于 JSON 存储"""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            # 默认存储在插件 data 目录下
            self.db_path = Path(__file__).parent / "data" / "laizhi_db.json"
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

@register("laizhi", "mp4502", "AstrBot 来只图库插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.db = LaizhiDB()

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self.db.initialize()
        logger.info("来只插件数据库初始化完成")


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

    @filter.regex(r"^别名(\S+)$")
    async def handle_alias(self, event: AstrMessageEvent):
        """处理别名命令"""
        name = event.message_str.removeprefix("别名")
        laizhi_info = await self.db.get_laizhi(name)  # 验证来只是否存在
        if not laizhi_info:
            yield event.plain_result(f"❌ 来只 '{name}' 不存在，请先使用 '新建{name}' 创建！")
            return
        repr = ""
        for i in range(len(laizhi_info.aliases)):
            repr += f"• {laizhi_info.aliases[i]}\n"
        yield event.plain_result(f"📋 '{name}' 的别名列表：\n{repr}")

    @filter.regex(r"^别名(\S+)\s+(.+)$")
    async def handle_alias(self, event: AstrMessageEvent):
        """处理别名命令"""
        name = event.message_str.removeprefix("别名")
        alias = event.message_str.split(maxsplit=1)[1] if len(event.message_str.split()) > 1 else None
        laizhi_info = await self.db.get_laizhi(name)  # 验证来只是否存在
        if not laizhi_info:
            yield event.plain_result(f"❌ 来只 '{name}' 不存在，请先使用 '新建{name}' 创建！")
            return
        if alias:
            await self.db.update_laizhi(name, aliases=laizhi_info.aliases + [alias])
            yield event.plain_result(f"✅ 为 '{name}' 设置别名 '{alias}' 成功！")
        else:
            yield event.plain_result(f"❌ 未提供别名，请使用 '别名{name} <别名>' 格式！")

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
    

        