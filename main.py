# AstrBot 自动回复按按钮表情包 核心代码
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger


# 插件注册信息
@register(
    name="auto_button",
    author="我自己",
    desc="自动回复按按钮表情包",
    version="1.0.0"
)
class AutoButton(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        logger.info("[按按钮插件] 加载成功！")

    # 监听所有消息
    @filter.all()
    async def on_message(self, event: AstrMessageEvent):
        # 1. 跳过机器人自己发的消息（防止无限刷屏）
        if event.is_self_msg():
            return

        # 2. 只在 QQ 平台生效
        if event.get_platform_name() != "aiocqhttp":
            return

        # 3. 自动回复：按按钮表情包（CQ 码，直接显示）
        yield event.plain_result("[CQ:face,id=393]")

    # 插件卸载时执行
    async def terminate(self):
        logger.info("[按按钮插件] 已卸载")