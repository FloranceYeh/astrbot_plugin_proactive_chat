## 🌟 功能特色

- **定时触发**: 基于用户沉默时间，在设定的随机时间范围内自动触发。
- **自动主动消息**: 插件每次重载时可以按需求自动开始创建主动消息任务，不需要用户输入来激活。
- **多会话支持**:支持同时为多个私聊和群聊提供主动消息服务，分别设置专属的配置和备注名。
- **会话完全隔离**: 每个会话拥有独立的状态、计数器、触发器，避免相互干扰。
- **上下文感知**: 支持灵活选择上下文来源，回顾历史对话，并根据你设定的提示词，生成与之前话题相关的回复，而不是生硬的问候。
- **日程联动**: 可读取 `astrbot_plugin_life_scheduler` 的今日穿搭和日程，让主动消息自然包含角色当天状态。
- **完整人格支持**: 加载并应用你为当前会话设置的专属人格，确保每一次主动消息都符合人设。
- **动态情绪**: 内置一个"未回复计数器"，你可以利用它在 Prompt 中设计不同的情绪表达，并且支持设置未回复上限。
- **持久化会话**: 无论您是"重启 AstrBot"还是"重载插件"，都能够从文件中恢复所有未执行的主动消息任务。
- **免打扰时段**: 可以自由设定一个时间段，在此期间 Bot 不会主动打扰用户。
- **分段回复**: 支持将长文本回复切分为多条短消息发送，并模拟真实的打字间隔，让对话更自然。
- **高度兼容**: 兼容其他需要对主动消息进行修饰的插件如表情包插件等。

### 📅 Life Scheduler 日程联动

如需让主动消息包含日程，请同时安装并启用 [`astrbot_plugin_life_scheduler`](https://github.com/muyouzhi6/astrbot_plugin_life_scheduler)。

本插件会在生成主动消息前尝试调用该插件的 `get_life_context()` 公共方法，读取今日穿搭与日程，并注入到模型的系统提示词中。未安装、未启用或暂时读取失败时会自动跳过，不影响主动消息主流程。

相关配置位于 `friend_settings.life_scheduler_settings` 和 `group_settings.life_scheduler_settings`：

```json
{
  "life_scheduler_settings": {
    "enable": true,
    "plugin_name": "astrbot_plugin_life_scheduler",
    "include_outfit": true,
    "include_schedule": true,
    "max_chars": 1600
  }
}
```

## 📑 插件配置项详解

<details>
<summary>点击查看配置项详解</summary>

### ⚙️ 1. 私聊全局配置 (`friend_settings`)

这一组配置决定插件如何在私聊场景下创建、调度并发送主动消息。只有被明确加入会话列表的私聊，才会真正获得主动消息服务。

- **启用私聊全局主动消息功能 (`enable`)**:
  - 类型：`Boolean`
  - 默认值：`true`
  - 说明：私聊主动消息总开关。关闭后，插件不会为任何私聊会话创建新的主动消息任务。

- **私聊会话 UMO 列表 (`session_list`)**:
  - 类型：`List[string]`
  - 默认值：`[]`
  - 说明：指定哪些私聊会话启用主动消息。
  - 提示：
    - 请输入完整 UMO，格式为 `平台名:消息类型:会话ID`。
    - 私聊消息类型固定为 `FriendMessage`。
    - 可通过 `/sid` 指令快捷获取当前会话的完整 UMO。
    - 例如：`default:FriendMessage:123456789`

- **私聊全局主动消息提示词 (`proactive_prompt`)**:
  - 类型：`Text`
  - 说明：这是私聊主动消息的核心配置，用于指导模型“为什么主动开口、该怎么开口、要保持什么语气”。
  - 支持占位符：
    - `{{unanswered_count}}`：当前会话连续未回复次数。
    - `{{current_time}}`：当前时间。
  - 编写建议：
    - 明确告诉模型“这是一次主动发起的消息”，避免它误判为用户先开口。
    - 让提示词同时包含“上下文延续”和“新话题开启”两套策略，效果通常更自然。
    - 如果你希望 Bot 更有情绪层次，可以结合 `{{unanswered_count}}` 设计轻微失落、想念、撒娇等动态表现。

#### 🔪 群聊分段回复

群聊分段回复规则与私聊一致，支持 `regex / words` 两种切分方式与 `random / log` 两种发送间隔算法。

```json
{
  "group_settings": {
    "enable": true,
    "session_list": ["default:GroupMessage:123456789"],
    "group_idle_trigger_minutes": 30,
    "auto_trigger_settings": {
      "enable_auto_trigger": false,
      "auto_trigger_after_minutes": 5
    },
    "schedule_settings": {
      "min_interval_minutes": 90,
      "max_interval_minutes": 360,
      "quiet_hours": "2-6",
      "max_unanswered_times": 2
    }
  }
}
```

原项目
[DBJD-CR/astrbot_plugin_proactive_chat](https://github.com/DBJD-CR/astrbot_plugin_proactive_chat)
