from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig


@register(
    "astrbot_plugin_xubiaoshi_reaction",
    "OpenAI",
    "别人发消息后，自动在该消息下添加一个表情回应（续标识）",
    "1.0.0",
    "https://example.com/astrbot_plugin_xubiaoshi_reaction",
)
class XuBiaoShiReactionPlugin(Star):
    # 常见 QQ 表情 ID，可自行补充
    EMOJI_NAME_TO_ID = {
        "赞": "76",
        "鼓掌": "99",
        "比心": "319",
        "庆祝": "320",
        "加油": "315",
        "牛": "128046",
        "火": "128293",
    }

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    def _resolve_emoji_id(self) -> str | None:
        """
        解析配置中的表情：
        1. emoji_id 优先
        2. emoji_name 走内置映射
        3. 单个 unicode emoji 字符则转 codepoint
        """
        emoji_id = str(self.config.get("emoji_id", "")).strip()
        if emoji_id:
            return emoji_id

        emoji_name = str(self.config.get("emoji_name", "")).strip()
        if not emoji_name:
            return None

        if emoji_name in self.EMOJI_NAME_TO_ID:
            return self.EMOJI_NAME_TO_ID[emoji_name]

        # 支持直接填一个 emoji 字符，例如 👍
        if len(emoji_name) == 1:
            cp = ord(emoji_name)
            if cp > 256:
                return str(cp)

        return None

    def _in_group_whitelist(self, group_id: str) -> bool:
        whitelist = [str(x) for x in self.config.get("group_whitelist", []) if str(x).strip()]
        if not whitelist:
            return True
        return group_id in whitelist

    def _is_blacklisted_user(self, user_id: str) -> bool:
        blacklist = {str(x) for x in self.config.get("user_blacklist", []) if str(x).strip()}
        return user_id in blacklist

    def _keyword_matched(self, text: str) -> bool:
        keyword_only = bool(self.config.get("keyword_only", False))
        keywords = [str(x).strip() for x in self.config.get("keywords", []) if str(x).strip()]

        if not keyword_only:
            return True

        if not keywords:
            return False

        return any(k in text for k in keywords)

    @filter.command("开启续标识")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def enable_plugin(self, event: AstrMessageEvent):
        self.config["enabled"] = True
        self.config.save_config()
        yield event.plain_result("✅ 已开启续标识")

    @filter.command("关闭续标识")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def disable_plugin(self, event: AstrMessageEvent):
        self.config["enabled"] = False
        self.config.save_config()
        yield event.plain_result("✅ 已关闭续标识")

    @filter.command("续标识状态")
    @filter.permission_type(filter.PermissionType.ADMIN)
    async def plugin_status(self, event: AstrMessageEvent):
        emoji_id = self._resolve_emoji_id()
        enabled = bool(self.config.get("enabled", True))
        yield event.plain_result(
            f"续标识状态：{'开启' if enabled else '关闭'}\n"
            f"当前 emoji_id：{emoji_id or '未配置'}"
        )

    @filter.event_message_type(filter.EventMessageType.ALL, priority=99)
    async def on_message(self, event: AstrMessageEvent):
        # 1) 总开关
        if not bool(self.config.get("enabled", True)):
            return

        # 2) 仅支持 aiocqhttp / NapCat 这套调用
        if event.get_platform_name() != "aiocqhttp":
            return

        # 3) 解析消息基本信息
        msg = event.message_obj
        message_id = str(getattr(msg, "message_id", "") or "")
        sender_id = str(event.get_sender_id() or "")
        self_id = str(getattr(msg, "self_id", "") or "")
        group_id = str(getattr(msg, "group_id", "") or "")
        text = event.message_str or ""

        if not message_id or not sender_id:
            return

        # 4) 不给自己点
        if self_id and sender_id == self_id:
            return

        # 5) 群 / 私聊开关
        is_group = bool(group_id)
        if is_group and not bool(self.config.get("enable_group", True)):
            return
        if (not is_group) and not bool(self.config.get("enable_private", False)):
            return

        # 6) 群白名单
        if is_group and not self._in_group_whitelist(group_id):
            return

        # 7) 用户黑名单
        if self._is_blacklisted_user(sender_id):
            return

        # 8) 关键词模式
        if not self._keyword_matched(text):
            return

        # 9) 表情解析
        emoji_id = self._resolve_emoji_id()
        if not emoji_id:
            logger.warning("[续标识] 未配置有效的 emoji_id / emoji_name")
            return

        # 10) 调用 NapCat / OneBot 动作接口给消息添加表情回应
        try:
            await event.bot.api.call_action(
                "set_msg_emoji_like",
                message_id=message_id,
                emoji_id=emoji_id,
            )
        except Exception as e:
            logger.error(f"[续标识] 添加表情回应失败: {e}")