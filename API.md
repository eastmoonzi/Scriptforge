# API 文档

本文档说明 `app.py` 中的主要函数和数据结构。

---

## 数据结构

### 消息对象 (Message)

```python
{
    'speaker': str,      # 发言者名字
    'content': str,      # 消息内容
    'type': str         # 'user' 或 'character'
}
```

### 角色对象 (Character)

```python
{
    'name': str,         # 角色名字
    'personality': str   # 角色性格描述
}
```

### Session State 状态

| 键名 | 类型 | 说明 |
|------|------|------|
| `chat_mode` | str | 对话模式：'group' 或 'private' |
| `scene` | str | 场景描述 |
| `characters` | List[Character] | 角色列表（3个） |
| `group_chat_history` | List[Message] | 群聊历史记录 |
| `private_chat_history` | Dict[str, List[Message]] | 私聊历史记录（按角色名索引） |
| `selected_character` | str | 当前选中的私聊角色名 |
| `conversation_started` | bool | 对话是否已开始 |

---

## 核心函数

### 1. 初始化函数

#### `init_session_state()`

初始化 Streamlit 会话状态。

**参数**: 无

**返回**: 无

**功能**:
- 初始化所有 session state 变量
- 如果变量已存在，不会覆盖

---

### 2. Mock 数据生成函数

#### `mock_generate_initial_conversation(scene, characters)`

生成初始的2轮模拟对话。

**参数**:
- `scene` (str): 场景描述
- `characters` (List[Character]): 角色列表

**返回**: `List[Message]` - 消息列表

**示例**:
```python
messages = mock_generate_initial_conversation(
    "在咖啡馆",
    [
        {"name": "小明", "personality": "开朗"},
        {"name": "小红", "personality": "安静"},
        {"name": "小刚", "personality": "幽默"}
    ]
)
```

#### `mock_generate_group_reply(scene, characters, chat_history, user_message)`

生成群聊中角色们对用户消息的模拟回复。

**参数**:
- `scene` (str): 场景描述
- `characters` (List[Character]): 角色列表
- `chat_history` (List[Message]): 聊天历史
- `user_message` (str): 用户发送的消息

**返回**: `List[Message]` - 角色回复列表（3条）

#### `mock_generate_private_reply(scene, character, chat_history, user_message)`

生成私聊中角色对用户消息的模拟回复。

**参数**:
- `scene` (str): 场景描述
- `character` (Character): 角色对象
- `chat_history` (List[Message]): 私聊历史
- `user_message` (str): 用户发送的消息

**返回**: `str` - 角色回复内容

---

### 3. Gemini API 调用函数

#### `generate_initial_conversation_with_gemini(scene, characters, api_key)`

使用 Gemini API 生成初始对话。

**参数**:
- `scene` (str): 场景描述
- `characters` (List[Character]): 角色列表
- `api_key` (str): Gemini API 密钥

**返回**: `List[Message]` - 消息列表

**异常处理**:
- API 调用失败时，自动降级到 Mock 模式
- 显示警告信息给用户

#### `generate_group_reply_with_gemini(scene, characters, chat_history, user_message, api_key)`

使用 Gemini API 生成群聊回复。

**参数**: 同 mock 版本 + `api_key`

**返回**: `List[Message]`

**特性**:
- 自动截取最近10条历史记录作为上下文
- 解析 API 返回的文本为消息对象

#### `generate_private_reply_with_gemini(scene, character, chat_history, user_message, api_key)`

使用 Gemini API 生成私聊回复。

**参数**: 同 mock 版本 + `api_key`

**返回**: `str`

**特性**:
- 提示 AI 以特定角色身份回复
- 强调这是私聊对话

---

### 4. UI 渲染函数

#### `render_chat_message(msg)`

渲染单条聊天消息。

**参数**:
- `msg` (Message): 消息对象

**返回**: 无（直接渲染到 Streamlit）

**功能**:
- 根据消息类型选择不同的头像
- user 类型：🧑 头像
- character 类型：🎭 头像，显示角色名

---

### 5. 主函数

#### `main()`

应用的主入口函数。

**功能**:
- 设置页面配置
- 初始化状态
- 渲染侧边栏（设置、模式切换）
- 根据状态渲染不同界面：
  - 未开始：场景和角色设置界面
  - 已开始：
    - 群聊模式：显示群聊历史和输入框
    - 私聊模式：显示私聊历史和输入框
- 处理用户输入和 AI 回复
- 提供导出功能

---

## 使用流程

### 典型的函数调用流程

1. **启动应用**
   ```
   main()
   → init_session_state()
   → 渲染初始设置界面
   ```

2. **生成初始对话**
   ```
   用户点击"开始对话"
   → 验证输入
   → generate_initial_conversation_with_gemini() 或 mock_generate_initial_conversation()
   → 保存到 group_chat_history
   → 切换到对话界面
   ```

3. **群聊交互**
   ```
   用户输入消息
   → 添加到 group_chat_history
   → generate_group_reply_with_gemini() 或 mock_generate_group_reply()
   → 扩展 group_chat_history
   → 刷新界面
   ```

4. **私聊交互**
   ```
   切换到私聊模式
   → 选择角色
   → 用户输入消息
   → 添加到 private_chat_history[角色名]
   → generate_private_reply_with_gemini() 或 mock_generate_private_reply()
   → 扩展 private_chat_history[角色名]
   → 刷新界面
   ```

---

## 扩展开发指南

### 添加新的对话模式

1. 在 `init_session_state()` 中添加新的状态变量
2. 在侧边栏添加新的模式选项
3. 在 `main()` 中添加新模式的渲染逻辑
4. 创建对应的 mock 和 API 生成函数

### 添加更多角色

目前角色数量固定为3个，如需支持可变数量：

1. 修改角色输入界面，使用动态表单
2. 调整 prompt 模板以支持不同数量的角色
3. 更新相关生成函数的逻辑

### 实现记忆同步

在生成群聊回复时，将对应角色的私聊历史加入上下文：

```python
def generate_group_reply_with_memory(scene, characters, group_history,
                                     private_history, user_message, api_key):
    for char in characters:
        # 合并该角色的群聊和私聊上下文
        char_private = private_history.get(char['name'], [])
        full_context = combine_context(group_history, char_private)
        # 生成回复...
```

---

## 性能优化建议

1. **上下文截断**: 当对话历史过长时，只保留最近 N 条记录
2. **缓存**: 使用 `@st.cache_data` 缓存重复的 API 调用
3. **异步调用**: 对于群聊，可以并行生成多个角色的回复
4. **流式输出**: 使用 Gemini 的流式 API，逐字显示回复

---

## 常见问题

### Q: 如何更换 AI 模型？

A: 修改 `generate_*_with_gemini` 函数中的 `model` 参数：
```python
response = client.models.generate_content(
    model='gemini-2.0-flash-exp',  # 改为其他模型
    contents=prompt
)
```

### Q: 如何调整对话风格？

A: 修改 prompt 模板，例如在 `generate_group_reply_with_gemini` 中添加：
```python
prompt = f"""
你是一个剧本创作助手。场景是：{scene}
请用幽默风格回复...  # 添加风格指导
"""
```

### Q: 如何持久化对话历史？

A: 添加保存/加载功能：
```python
import json

def save_conversation():
    data = {
        'scene': st.session_state.scene,
        'characters': st.session_state.characters,
        'group_chat_history': st.session_state.group_chat_history,
        'private_chat_history': st.session_state.private_chat_history
    }
    with open('conversation.json', 'w') as f:
        json.dump(data, f)

def load_conversation():
    with open('conversation.json', 'r') as f:
        data = json.load(f)
    st.session_state.update(data)
```
