# 文件名: main.py (位于 data/plugins/astrbot_plugin_proactive_chat/ 目录下)
# 版本: v1.2.0

"""插件入口与主类定义。"""

from __future__ import annotations

import asyncio
import time

import astrbot.api.star as star
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.config.astrbot_config import AstrBotConfig

# 导入各模块的 Mixins，用于组装插件能力
from .core.chat_flow import ProactiveCoreMixin
from .core.data_storage import StorageMixin
from .core.llm_adapter import LlmMixin
from .core.message_events import EventsMixin
from .core.message_sender import SenderMixin
from .core.plugin_lifecycle import LifecycleMixin
from .core.session_config import ConfigMixin
from .core.session_override_manager import SessionOverrideManager
from .core.session_parser import SessionMixin
from .core.task_scheduler import SchedulerMixin


class ProactiveChatPlugin(
    SessionMixin,  # 会话 ID 解析、规范化与日志格式化
    StorageMixin,  # 会话数据加载/保存与迁移清理
    ConfigMixin,  # 配置读取与会话级配置路由
    SchedulerMixin,  # 定时任务、自动触发与沉默计时
    LlmMixin,  # 上下文准备与 LLM 调用封装
    SenderMixin,  # 主动消息发送与装饰钩子
    EventsMixin,  # 私聊/群聊事件监听处理
    LifecycleMixin,  # initialize/terminate 生命周期管理
    ProactiveCoreMixin,  # 主动消息主流程编排
    star.Star,
):
    """
    插件的主类，负责生命周期管理、事件监听和核心逻辑执行。
    """

    def __init__(self, context: star.Context, config: AstrBotConfig) -> None:
        super().__init__(context)

        # 注入的配置对象（由 AstrBot 框架提供）
        self.config: AstrBotConfig = config
        # 调度器与时区会在 initialize 中初始化
        self.scheduler = None  # AsyncIOScheduler 实例（initialize 中创建）
        self.timezone = None  # ZoneInfo 时区对象（initialize 中加载）

        # 使用 StarTools 获取插件专属数据目录（Path 对象）
        self.data_dir = star.StarTools.get_data_dir("astrbot_plugin_proactive_chat")
        self.session_data_file = self.data_dir / "session_data.json"

        # 共享锁与持久化数据容器
        self.data_lock = None
        self.session_data: dict = {}
        # 记录当前正在执行“立即触发”的会话，防止重复点击导致并发主动消息。
        self.manual_trigger_sessions: set[str] = set()

        # 会话差异配置管理器
        self.session_override_manager = SessionOverrideManager(self.data_dir)
        # 保存已创建但尚未完成的后台任务引用，避免被垃圾回收或在终止时遗漏清理。
        self._background_tasks: set[asyncio.Task[None]] = set()

        # 群聊沉默倒计时与自动触发计时器
        self.group_timers: dict[str, asyncio.TimerHandle] = {}
        self.last_bot_message_time = 0  # 预留字段：记录 Bot 最近发言时间
        self.session_temp_state: dict[
            str, dict
        ] = {}  # 临时态（如群聊最后用户发言时间）
        self.last_message_times: dict[str, float] = {}  # 会话最近消息时间，用于触发判断
        self.auto_trigger_timers: dict[
            str, asyncio.TimerHandle
        ] = {}  # 自动触发计时器句柄
        # 插件启动时间与日志控制
        self.plugin_start_time = time.time()
        self.first_message_logged: set[str] = set()
        self._cleanup_counter = 0

        logger.info("[主动消息] 插件实例已创建喵。")

    def _track_task(self, task: asyncio.Task[None] | None) -> asyncio.Task[None] | None:
        """登记后台任务引用，避免任务过早释放。"""
        if task is None:
            return None
        # 统一把后台 task 收口到集合中，便于生命周期结束时批量取消与等待回收。
        self._background_tasks.add(task)
        # 任务结束后自动把自己从集合移除，避免集合无限增长。
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def _cleanup_background_tasks(self) -> None:
        """清理所有未完成的后台任务。"""
        if not self._background_tasks:
            return

        # 先做快照，避免遍历过程中因回调移除元素导致集合发生变化。
        pending_tasks = list(self._background_tasks)
        for task in pending_tasks:
            if not task.done():
                # 未完成任务先统一取消，防止插件关闭时仍有后台协程悬挂。
                task.cancel()

        if pending_tasks:
            # 吞掉所有异常，确保后台任务清理失败不会影响插件主清理流程。
            await asyncio.gather(*pending_tasks, return_exceptions=True)

        self._background_tasks.clear()

    async def terminate(self) -> None:
        """插件终止入口：委托 LifecycleMixin 清理。"""
        await LifecycleMixin.terminate(self)

    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE, priority=999)
    async def on_friend_message(self, event: AstrMessageEvent) -> None:
        """私聊消息入口：委托 EventsMixin 处理。"""
        # 主类仅做入口转发，具体逻辑由 EventsMixin 实现
        await EventsMixin.on_friend_message(self, event)

    @filter.event_message_type(filter.EventMessageType.GROUP_MESSAGE, priority=998)
    async def on_group_message(self, event: AstrMessageEvent) -> None:
        """群聊消息入口：委托 EventsMixin 处理。"""
        # 主类仅做入口转发，具体逻辑由 EventsMixin 实现
        await EventsMixin.on_group_message(self, event)

    @filter.after_message_sent()
    async def on_after_message_sent(self, event: AstrMessageEvent) -> None:
        """消息发送后入口：委托 EventsMixin 处理。"""
        # 主类仅做入口转发，具体逻辑由 EventsMixin 实现
        await EventsMixin.on_after_message_sent(self, event)
