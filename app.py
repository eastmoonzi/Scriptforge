import streamlit as st
import os
import json
from typing import List, Dict, Optional
from datetime import datetime

# v3.0.0: 导入 CrewAI 多 Agent 系统
try:
    from agent_crew import CharacterAgentCrew
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    st.warning("⚠️ CrewAI 未安装，使用降级模式")

# 初始化 session state
def init_session_state():
    """初始化会话状态 - v2.2.0 多 Agent 架构"""
    if 'chat_mode' not in st.session_state:
        st.session_state.chat_mode = 'group'  # 'group' 或 'private'

    if 'scene' not in st.session_state:
        st.session_state.scene = ''

    if 'characters' not in st.session_state:
        st.session_state.characters = []

    if 'num_characters' not in st.session_state:
        st.session_state.num_characters = 3  # 默认3个角色

    # v2.2.0 新架构：真正的多 Agent 记忆系统
    if 'shared_events' not in st.session_state:
        # 共享事件流（群聊消息），用于显示群聊界面
        st.session_state.shared_events = []

    if 'character_memories' not in st.session_state:
        # 每个角色的独立记忆（包含群聊+自己的私聊）
        st.session_state.character_memories = {}

    if 'selected_character' not in st.session_state:
        st.session_state.selected_character = None

    if 'conversation_started' not in st.session_state:
        st.session_state.conversation_started = False

    if 'api_key' not in st.session_state:
        st.session_state.api_key = ''

    # v3.0.0: CrewAI Agent 管理器
    if 'crew_manager' not in st.session_state:
        st.session_state.crew_manager = None

    # v3.0.0: 使用 CrewAI 模式
    if 'use_crewai' not in st.session_state:
        st.session_state.use_crewai = True  # 默认启用


# ============= v3.0.0 CrewAI 辅助函数 =============

def _fallback_sequential_generation(user_input, use_real_api, api_key, status_placeholder):
    """
    降级方案：传统顺序发言模式
    当 CrewAI 不可用或失败时使用
    """
    for idx, char in enumerate(st.session_state.characters, 1):
        status_placeholder.info(f"🤔 {char['name']} 正在回复... ({idx}/{len(st.session_state.characters)})")

        # 获取角色的完整记忆
        char_memory = get_character_memory(char['name'])

        # 生成回复
        if use_real_api and api_key:
            content = generate_single_reply_with_gemini(
                st.session_state.scene,
                char,
                st.session_state.characters,
                char_memory,
                is_initial=False,
                api_key=api_key
            )
        else:
            content = mock_generate_single_reply(
                st.session_state.scene,
                char,
                char_memory,
                is_initial=False
            )

        # 添加到记忆系统
        add_group_message(char['name'], content, 'character')


# ============= v2.2.0 多 Agent 记忆管理系统 =============

def init_character_memories():
    """初始化所有角色的记忆"""
    st.session_state.character_memories = {
        char['name']: [] for char in st.session_state.characters
    }


def add_group_message(speaker: str, content: str, msg_type: str = 'character'):
    """
    添加群聊消息（所有角色都能看到）

    Args:
        speaker: 发言者名称
        content: 消息内容
        msg_type: 消息类型 ('user' 或 'character')
    """
    message = {
        'timestamp': datetime.now().isoformat(),
        'speaker': speaker,
        'content': content,
        'type': 'group',
        'msg_type': msg_type,
        'visible_to': 'all'
    }

    # 添加到共享事件流（用于显示）
    st.session_state.shared_events.append(message)

    # 添加到所有角色的记忆
    for char_name in st.session_state.character_memories:
        st.session_state.character_memories[char_name].append(message.copy())


def add_private_message(character_name: str, speaker: str, content: str, msg_type: str = 'character'):
    """
    添加私聊消息（只有指定角色能看到）

    Args:
        character_name: 角色名称
        speaker: 发言者名称
        content: 消息内容
        msg_type: 消息类型 ('user' 或 'character')
    """
    message = {
        'timestamp': datetime.now().isoformat(),
        'speaker': speaker,
        'content': content,
        'type': 'private',
        'msg_type': msg_type,
        'visible_to': [character_name]
    }

    # 只添加到指定角色的记忆
    if character_name in st.session_state.character_memories:
        st.session_state.character_memories[character_name].append(message)


def get_character_memory(character_name: str, limit: int = 20) -> List[Dict]:
    """
    获取角色的记忆（按时间排序）

    Args:
        character_name: 角色名称
        limit: 返回最近 N 条记忆

    Returns:
        角色的记忆列表
    """
    if character_name not in st.session_state.character_memories:
        return []

    memories = st.session_state.character_memories[character_name]
    # 按时间戳排序（已经是按顺序添加的，但保险起见）
    sorted_memories = sorted(memories, key=lambda x: x['timestamp'])
    return sorted_memories[-limit:] if limit > 0 else sorted_memories


def get_private_messages(character_name: str) -> List[Dict]:
    """
    获取角色的所有私聊消息

    Args:
        character_name: 角色名称

    Returns:
        私聊消息列表
    """
    if character_name not in st.session_state.character_memories:
        return []

    return [
        msg for msg in st.session_state.character_memories[character_name]
        if msg['type'] == 'private'
    ]


# ============= 结束记忆管理系统 =============


# 预设管理
def load_preset_from_json(json_str: str) -> bool:
    """
    从 JSON 字符串加载预设

    Args:
        json_str: JSON 格式的预设数据

    Returns:
        加载是否成功
    """
    try:
        data = json.loads(json_str)

        # 验证必要字段
        if 'scene' not in data or 'characters' not in data:
            st.error("预设文件格式错误：缺少 scene 或 characters 字段")
            return False

        # 加载预设
        st.session_state.scene = data.get('scene', '')
        st.session_state.characters = data.get('characters', [])
        st.session_state.num_characters = len(st.session_state.characters)

        # 可选：加载 API Key
        if 'api_key' in data and data['api_key']:
            st.session_state.api_key = data['api_key']

        st.success(f"✅ 预设 '{data.get('preset_name', '未命名')}' 加载成功！")
        return True
    except Exception as e:
        st.error(f"预设加载失败: {str(e)}")
        return False


# 保存对话历史到 JSON 文件
def save_conversation_to_json() -> str:
    """
    保存当前对话状态到 JSON 文件 - v2.2.0 多 Agent 架构

    Returns:
        JSON 字符串，可用于下载
    """
    data = {
        'version': '2.2.0',
        'saved_at': datetime.now().isoformat(),
        'scene': st.session_state.scene,
        'characters': st.session_state.characters,
        'num_characters': st.session_state.num_characters,
        'shared_events': st.session_state.shared_events,
        'character_memories': st.session_state.character_memories,
        'conversation_started': st.session_state.conversation_started
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


# 从 JSON 加载对话历史
def load_conversation_from_json(json_str: str) -> bool:
    """
    从 JSON 字符串加载对话历史 - 支持 v2.1.x 到 v2.2.0 的迁移

    Args:
        json_str: JSON 格式的对话数据

    Returns:
        加载是否成功
    """
    try:
        data = json.loads(json_str)
        version = data.get('version', '1.0.0')

        st.info(f"加载的对话版本: {version}")

        # 恢复基本状态
        st.session_state.scene = data.get('scene', '')
        st.session_state.characters = data.get('characters', [])
        st.session_state.num_characters = data.get('num_characters', len(data.get('characters', [])))
        st.session_state.conversation_started = data.get('conversation_started', False)

        # 版本兼容处理
        if version.startswith('2.2'):
            # v2.2.0 格式：直接加载新架构
            st.session_state.shared_events = data.get('shared_events', [])
            st.session_state.character_memories = data.get('character_memories', {})
        else:
            # v2.1.x 或更早版本：转换到新架构
            st.warning("检测到旧版本格式，正在转换到 v2.2.0 架构...")

            # 初始化新结构
            st.session_state.shared_events = []
            st.session_state.character_memories = {
                char['name']: [] for char in st.session_state.characters
            }

            # 迁移群聊历史
            old_group_history = data.get('group_chat_history', [])
            for msg in old_group_history:
                speaker = msg.get('speaker', '未知')
                content = msg.get('content', '')
                msg_type = msg.get('type', 'character')
                add_group_message(speaker, content, msg_type)

            # 迁移私聊历史
            old_private_history = data.get('private_chat_history', {})
            for char_name, messages in old_private_history.items():
                for msg in messages:
                    speaker = msg.get('speaker', '未知')
                    content = msg.get('content', '')
                    msg_type = msg.get('type', 'character')
                    add_private_message(char_name, speaker, content, msg_type)

            st.success("✅ 已成功转换到 v2.2.0 多 Agent 架构！")

        return True
    except Exception as e:
        st.error(f"加载失败: {str(e)}")
        return False


# 顺序生成单个角色的发言（Mock版本）- v2.2.0 基于完整记忆
def mock_generate_single_reply(scene: str, character: Dict[str, str],
                                character_memory: List[Dict[str, str]], is_initial: bool = False) -> str:
    """
    Mock function: 生成单个角色的发言（基于角色完整记忆）

    Args:
        scene: 场景描述
        character: 角色信息
        character_memory: 角色的完整记忆（包含群聊+私聊）
        is_initial: 是否是初始对话

    Returns:
        角色的发言内容
    """
    if is_initial and len(character_memory) == 0:
        return f"大家好！{scene}真是个有趣的地方。我是{character['name']}。"
    elif is_initial:
        # 初始对话，回应前面的角色
        return f"({character['personality']})我也很期待！让我们一起探索吧。"
    else:
        # 续写对话，基于完整记忆
        # 检查是否有私聊记忆
        private_msgs = [m for m in character_memory if m['type'] == 'private']
        has_secret = len(private_msgs) > 0

        last_msg = character_memory[-1] if character_memory else None

        if has_secret and len(character_memory) % 5 == 0:
            # 偶尔暗示私聊内容
            return f"({character['personality']})基于我了解的一些信息，我觉得..."
        elif last_msg and last_msg.get('msg_type') == 'user':
            return f"({character['personality']})听到你说'{last_msg['content']}'，我觉得很有意思！"
        else:
            return f"({character['personality']})对于刚才的讨论，我想补充一点..."


# 模拟生成初始群聊对话（已废弃，保留兼容性）
def mock_generate_initial_conversation(scene: str, characters: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Mock function: 生成初始群聊对话（旧版本，已被顺序发言取代）
    仅用于向后兼容，实际使用顺序发言机制
    """
    messages = []
    for char in characters:
        content = mock_generate_single_reply(scene, char, messages, is_initial=True)
        messages.append({
            'speaker': char['name'],
            'content': content,
            'type': 'character'
        })
    return messages


# 模拟生成群聊续写回复（已废弃，保留兼容性）
def mock_generate_group_reply(scene: str, characters: List[Dict[str, str]],
                               chat_history: List[Dict[str, str]], user_message: str) -> List[Dict[str, str]]:
    """
    Mock function: 根据用户发言生成角色们的回复（旧版本，已被顺序发言取代）
    仅用于向后兼容
    """
    replies = []
    for char in characters:
        content = mock_generate_single_reply(scene, char, chat_history, is_initial=False)
        replies.append({
            'speaker': char['name'],
            'content': content,
            'type': 'character'
        })
    return replies


# 模拟生成私聊回复
def mock_generate_private_reply(scene: str, character: Dict[str, str],
                                chat_history: List[Dict[str, str]], user_message: str) -> str:
    """
    Mock function: 生成私聊回复
    """
    return f"({character['personality']})关于'{user_message}'这个问题，让我私下跟你说..."


# 使用 Gemini API 生成单个角色的发言 - v2.2.0 基于完整记忆
def generate_single_reply_with_gemini(scene: str, character: Dict[str, str],
                                      characters: List[Dict[str, str]],
                                      character_memory: List[Dict[str, str]],
                                      is_initial: bool, api_key: str) -> str:
    """
    使用 Gemini API 生成单个角色的发言（基于角色完整记忆）

    Args:
        scene: 场景描述
        character: 当前发言的角色
        characters: 所有角色列表
        character_memory: 角色的完整记忆（包含群聊+私聊）
        is_initial: 是否是初始对话
        api_key: API密钥

    Returns:
        角色的发言内容
    """
    try:
        import google.genai as genai

        client = genai.Client(api_key=api_key)

        # 构建角色记忆（最近20条）
        recent_memory = character_memory[-20:] if len(character_memory) > 20 else character_memory

        # 分离群聊和私聊记忆
        group_msgs = []
        private_msgs = []
        for msg in recent_memory:
            msg_line = f"{msg['speaker']}：{msg['content']}"
            if msg['type'] == 'group':
                group_msgs.append(msg_line)
            else:
                private_msgs.append(msg_line)

        # 构建显示文本
        group_text = "\n".join(group_msgs) if group_msgs else "（暂无群聊记录）"
        private_text = "\n".join(private_msgs) if private_msgs else "（暂无私聊记录）"

        # 构建角色列表
        characters_text = "\n".join([f"- {c['name']}: {c['personality']}" for c in characters])

        if is_initial:
            prompt = f"""
你正在扮演角色：{character['name']}（性格：{character['personality']}）
场景：{scene}

所有角色：
{characters_text}

群聊记录：
{group_text}

请以{character['name']}的身份和性格，在这个场景下说一句话。

【重要提示】
- 仔细阅读上面的群聊记录，理解整体对话的氛围和方向
- 如果你是第一个发言，可以打招呼并对场景做出反应
- 如果前面已有人发言，你可以：
  * 回应任何一个角色说的话（不仅仅是最后一个人）
  * 对整体对话做出评论或补充
  * 提出新的话题或观点
  * 根据整体对话氛围自然地表达
- 你的发言要符合你的性格特点
- 要让对话自然流畅，不要生硬
- 只输出你要说的一句话，不要加角色名，不要有其他说明

你的发言：
"""
        else:
            prompt = f"""
你正在扮演角色：{character['name']}（性格：{character['personality']}）
场景：{scene}

所有角色：
{characters_text}

【你的记忆系统】
你拥有两种记忆：

1. 群聊记录（所有人都能看到的公开对话）：
{group_text}

2. 私聊记录（只有你知道的私密信息）：
{private_text}

请以{character['name']}的身份和性格，在群聊中发言。

【重要提示】
- 仔细阅读你的完整记忆（群聊+私聊），统揽全局，理解整体对话的走向
- 你可以自由选择回应的对象和方式：
  * 回应用户的发言
  * 回应任何一个角色说的话
  * 对之前提到的话题进行补充或延伸
  * 综合多个人的观点给出你的看法
  * 提出与对话相关的新想法
- **关键**：你可以利用私聊中获得的信息，但要注意：
  * 不要直接泄露私聊内容（其他人不知道）
  * 可以巧妙地暗示或利用这些信息
  * 让你的发言更有深度和策略性
- 你的发言要基于对整个记忆的理解，而不是只看最后一条消息
- 要让对话连贯、自然、有深度
- 充分展现你的性格特点
- 只输出你要说的一句话，不要加角色名，不要有其他说明

你的发言：
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:
        st.warning(f"API 调用失败: {str(e)}，使用 Mock 数据")
        return mock_generate_single_reply(scene, character, character_memory, is_initial)


# 真实的 Gemini API 调用函数（旧版本，保留兼容性）
def generate_initial_conversation_with_gemini(scene: str, characters: List[Dict[str, str]], api_key: str) -> List[Dict[str, str]]:
    """
    使用 Gemini API 生成初始对话
    """
    try:
        import google.genai as genai

        client = genai.Client(api_key=api_key)

        prompt = f"""
你是一个剧本创作助手。请根据以下信息创作一段对话：

场景：{scene}

角色：
1. {characters[0]['name']} - 性格：{characters[0]['personality']}
2. {characters[1]['name']} - 性格：{characters[1]['personality']}
3. {characters[2]['name']} - 性格：{characters[2]['personality']}

要求：
- 让这3个角色进行2轮对话（每轮每个角色说一句话）
- 对话要符合各自的性格特点
- 对话要与场景相关
- 格式：角色名：对话内容（每行一句）

请直接输出对话内容，不要有其他说明。
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )

        # 解析响应为消息列表
        messages = []
        for line in response.text.strip().split('\n'):
            if '：' in line or ':' in line:
                sep = '：' if '：' in line else ':'
                speaker, content = line.split(sep, 1)
                messages.append({
                    'speaker': speaker.strip(),
                    'content': content.strip(),
                    'type': 'character'
                })

        return messages if messages else mock_generate_initial_conversation(scene, characters)

    except Exception as e:
        st.warning(f"API 调用失败: {str(e)}，使用 Mock 数据")
        return mock_generate_initial_conversation(scene, characters)


def generate_group_reply_with_gemini(scene: str, characters: List[Dict[str, str]],
                                     chat_history: List[Dict[str, str]], user_message: str, api_key: str) -> List[Dict[str, str]]:
    """使用 Gemini API 生成群聊回复"""
    try:
        import google.genai as genai

        client = genai.Client(api_key=api_key)

        # 构建对话历史
        history_text = "\n".join([f"{msg['speaker']}：{msg['content']}" for msg in chat_history[-10:]])  # 只取最近10条

        # 构建角色设定
        characters_text = "\n".join([f"- {c['name']}: {c['personality']}" for c in characters])

        prompt = f"""
你是一个剧本创作助手。场景是：{scene}

角色设定：
{characters_text}

对话历史：
{history_text}

用户（真实玩家）：{user_message}

请让3个角色分别对用户的发言做出回应，符合各自的性格。
格式：角色名：对话内容（每行一句）
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )

        messages = []
        for line in response.text.strip().split('\n'):
            if '：' in line or ':' in line:
                sep = '：' if '：' in line else ':'
                speaker, content = line.split(sep, 1)
                messages.append({
                    'speaker': speaker.strip(),
                    'content': content.strip(),
                    'type': 'character'
                })

        return messages if messages else mock_generate_group_reply(scene, characters, chat_history, user_message)

    except Exception as e:
        st.warning(f"API 调用失败: {str(e)}，使用 Mock 数据")
        return mock_generate_group_reply(scene, characters, chat_history, user_message)


def generate_private_reply_with_gemini(scene: str, character: Dict[str, str],
                                       chat_history: List[Dict[str, str]], user_message: str, api_key: str) -> str:
    """使用 Gemini API 生成私聊回复"""
    try:
        import google.genai as genai

        client = genai.Client(api_key=api_key)

        history_text = "\n".join([f"{msg['speaker']}：{msg['content']}" for msg in chat_history[-10:]])

        prompt = f"""
你正在扮演角色：{character['name']}（性格：{character['personality']}）
场景：{scene}

对话历史：
{history_text}

用户：{user_message}

请以{character['name']}的身份和性格回复用户，这是私聊对话。
只输出对话内容，不要加角色名。
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )

        return response.text.strip()

    except Exception as e:
        st.warning(f"API 调用失败: {str(e)}，使用 Mock 数据")
        return mock_generate_private_reply(scene, character, chat_history, user_message)


def render_chat_message(msg: Dict[str, str]):
    """渲染单条聊天消息"""
    if msg['type'] == 'user':
        with st.chat_message("user", avatar="🧑"):
            st.write(msg['content'])
    else:
        with st.chat_message("assistant", avatar="🎭"):
            st.write(f"**{msg['speaker']}**: {msg['content']}")


def main():
    st.set_page_config(page_title="群聊对话生成器", page_icon="💬", layout="wide")

    # 初始化
    init_session_state()

    st.title("💬 群聊对话生成器")

    # 侧边栏：设置和模式切换
    with st.sidebar:
        st.header("⚙️ 设置")

        # 预设导入
        if not st.session_state.conversation_started:
            st.header("📂 快速开始")
            preset_file = st.file_uploader(
                "导入预设",
                type=['json'],
                help="上传预设文件快速初始化场景和角色"
            )

            if preset_file is not None:
                try:
                    json_str = preset_file.read().decode('utf-8')
                    if load_preset_from_json(json_str):
                        st.rerun()
                except Exception as e:
                    st.error(f"文件读取失败: {str(e)}")

            st.markdown("---")

        # API 配置
        use_real_api = st.checkbox("使用真实 Gemini API", value=False)
        if use_real_api:
            api_key = st.text_input("Gemini API Key",
                                   value=st.session_state.get('api_key', ''),
                                   type="password",
                                   help="从 Google AI Studio 获取")

            # v3.0.0: CrewAI 开关
            if CREWAI_AVAILABLE:
                use_crewai = st.checkbox(
                    "🤖 启用 CrewAI 多 Agent 系统",
                    value=True,
                    help="使用 CrewAI 框架实现真正的多智能体协作（推荐）"
                )
                st.session_state.use_crewai = use_crewai

                if use_crewai:
                    st.success("✅ 真正多 Agent 模式")
                else:
                    st.info("ℹ️ 传统顺序发言模式")
            else:
                st.warning("⚠️ CrewAI 未安装，使用传统模式")
        else:
            api_key = ""
            st.info("当前使用 Mock 数据模式")

        st.markdown("---")

        # 模式切换
        st.header("💬 对话模式")
        chat_mode = st.radio(
            "选择模式",
            options=['group', 'private'],
            format_func=lambda x: "群聊模式" if x == 'group' else "私聊模式",
            key='mode_selector'
        )

        if chat_mode != st.session_state.chat_mode:
            st.session_state.chat_mode = chat_mode

        # 私聊模式下选择角色
        if st.session_state.chat_mode == 'private' and st.session_state.conversation_started:
            st.subheader("选择私聊对象")
            character_names = [c['name'] for c in st.session_state.characters]
            selected = st.selectbox(
                "角色",
                options=character_names,
                key='character_selector'
            )
            st.session_state.selected_character = selected

        st.markdown("---")

        # 全局记忆功能
        st.header("💾 全局记忆")

        # 保存对话
        if st.session_state.conversation_started:
            json_data = save_conversation_to_json()
            st.download_button(
                label="💾 保存对话",
                data=json_data,
                file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
                help="保存当前对话到文件，包括场景、角色和所有对话历史"
            )
        else:
            st.info("开始对话后才能保存")

        # 加载对话
        uploaded_file = st.file_uploader(
            "📂 加载对话",
            type=['json'],
            help="上传之前保存的对话文件"
        )

        if uploaded_file is not None:
            try:
                json_str = uploaded_file.read().decode('utf-8')
                if load_conversation_from_json(json_str):
                    st.success("✅ 对话加载成功！")
                    st.rerun()
            except Exception as e:
                st.error(f"文件读取失败: {str(e)}")

        st.markdown("---")

        # 重置按钮
        if st.button("🔄 重新开始", use_container_width=True):
            st.session_state.conversation_started = False
            st.session_state.shared_events = []
            st.session_state.character_memories = {}
            st.session_state.scene = ''
            st.session_state.characters = []
            st.rerun()

    # 主界面
    if not st.session_state.conversation_started:
        # 初始设置界面
        st.header("📝 场景和角色设置")

        scene = st.text_area(
            "场景描述",
            value=st.session_state.scene,
            placeholder="例如：在一个神秘的古堡里，三个冒险家正在寻找宝藏...",
            height=100
        )

        # 角色数量控制
        st.subheader("角色设置")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**当前角色数量: {st.session_state.num_characters}** (范围: 2-8)")
        with col2:
            if st.button("➕ 添加角色", disabled=st.session_state.num_characters >= 8):
                st.session_state.num_characters += 1
                st.rerun()
        with col3:
            if st.button("➖ 减少角色", disabled=st.session_state.num_characters <= 2):
                st.session_state.num_characters -= 1
                st.rerun()

        # 动态生成角色输入框
        characters = []
        num_cols = min(st.session_state.num_characters, 4)  # 每行最多4个
        rows = (st.session_state.num_characters + num_cols - 1) // num_cols

        for row in range(rows):
            cols = st.columns(num_cols)
            for col_idx in range(num_cols):
                char_idx = row * num_cols + col_idx + 1
                if char_idx <= st.session_state.num_characters:
                    with cols[col_idx]:
                        st.markdown(f"**角色 {char_idx}**")
                        name = st.text_input(
                            f"角色{char_idx}名字",
                            key=f"setup_name_{char_idx}",
                            placeholder=f"角色{char_idx}"
                        )
                        personality = st.text_area(
                            f"角色{char_idx}性格",
                            key=f"setup_personality_{char_idx}",
                            placeholder="例如：勇敢、冲动、喜欢冒险...",
                            height=80
                        )
                        characters.append({"name": name, "personality": personality})

        st.markdown("---")

        if st.button("🎭 开始对话", type="primary", use_container_width=True):
            # 验证输入
            if not scene.strip():
                st.error("请输入场景描述！")
                return

            valid = True
            for i, char in enumerate(characters, 1):
                if not char['name'].strip():
                    st.error(f"请输入角色{i}的名字！")
                    valid = False
                if not char['personality'].strip():
                    st.error(f"请输入角色{i}的性格描述！")
                    valid = False

            if not valid:
                return

            # 保存设置
            st.session_state.scene = scene
            st.session_state.characters = characters
            st.session_state.conversation_started = True

            # v2.2.0: 初始化新的记忆系统
            st.session_state.shared_events = []
            init_character_memories()

            # v3.0.0: 初始化 CrewAI（如果启用且有 API Key）
            if CREWAI_AVAILABLE and st.session_state.use_crewai and api_key:
                try:
                    st.session_state.crew_manager = CharacterAgentCrew(
                        scene=scene,
                        characters=characters,
                        api_key=api_key
                    )
                except Exception as e:
                    st.error(f"CrewAI 初始化失败: {str(e)}")
                    st.session_state.crew_manager = None
            else:
                st.session_state.crew_manager = None

            st.rerun()

    else:
        # 对话界面
        st.header(f"{'👥 群聊' if st.session_state.chat_mode == 'group' else '💬 私聊'}")

        if st.session_state.chat_mode == 'group':
            # 群聊模式
            st.caption(f"场景：{st.session_state.scene}")

            # 检查是否需要生成初始对话
            if len(st.session_state.shared_events) == 0:
                st.info("💬 角色们正在开始对话...")

                # 顺序生成初始对话
                chat_placeholder = st.empty()
                status_placeholder = st.empty()

                for idx, char in enumerate(st.session_state.characters, 1):
                    status_placeholder.info(f"🤔 {char['name']} 正在思考... ({idx}/{len(st.session_state.characters)})")

                    # 获取角色的当前记忆
                    char_memory = get_character_memory(char['name'])

                    # 生成发言
                    if use_real_api and api_key:
                        content = generate_single_reply_with_gemini(
                            st.session_state.scene,
                            char,
                            st.session_state.characters,
                            char_memory,
                            is_initial=True,
                            api_key=api_key
                        )
                    else:
                        content = mock_generate_single_reply(
                            st.session_state.scene,
                            char,
                            char_memory,
                            is_initial=True
                        )

                    # 添加到记忆系统
                    add_group_message(char['name'], content, 'character')

                    # 实时显示更新后的对话
                    with chat_placeholder.container():
                        for msg in st.session_state.shared_events:
                            render_chat_message(msg)

                status_placeholder.success("✅ 初始对话生成完成！")
                st.rerun()

            # 显示聊天历史
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.shared_events:
                    render_chat_message(msg)

            # 用户交互区域
            st.markdown("---")
            col1, col2 = st.columns([1, 1])

            with col1:
                user_input = st.chat_input("💬 输入你的消息，参与群聊...")

            with col2:
                auto_continue_cols = st.columns([3, 1])
                with auto_continue_cols[0]:
                    num_rounds = st.number_input(
                        "轮数",
                        min_value=1,
                        max_value=5,
                        value=1,
                        key="auto_rounds",
                        help="角色们自主对话的轮数"
                    )
                with auto_continue_cols[1]:
                    auto_continue = st.button("🎭 继续聊", use_container_width=True, help="让角色们自主继续对话")

            if user_input:
                # 添加用户消息到所有角色的记忆
                add_group_message('你', user_input, 'user')

                status_placeholder = st.empty()

                # v3.0.0: 使用 CrewAI 或降级模式
                if st.session_state.crew_manager and CREWAI_AVAILABLE:
                    # CrewAI 模式：真正的多 Agent 协作
                    status_placeholder.info("🤖 多 Agent 系统正在协作...")

                    try:
                        # 运行 CrewAI
                        responses = st.session_state.crew_manager.run_conversation_round(
                            user_message=user_input,
                            character_memories=st.session_state.character_memories
                        )

                        # 将结果添加到记忆
                        for resp in responses:
                            if resp['content'] and resp['content'] != 'PASS':
                                add_group_message(resp['speaker'], resp['content'], 'character')

                    except Exception as e:
                        st.error(f"CrewAI 执行错误: {str(e)}, 降级到传统模式")
                        # 降级到传统模式
                        _fallback_sequential_generation(user_input, use_real_api, api_key, status_placeholder)
                else:
                    # 传统模式：顺序发言
                    _fallback_sequential_generation(user_input, use_real_api, api_key, status_placeholder)

                status_placeholder.empty()
                st.rerun()

            # 自主对话功能
            if auto_continue:
                status_placeholder = st.empty()

                for round_num in range(int(num_rounds)):
                    status_placeholder.info(f"🎭 第 {round_num + 1}/{int(num_rounds)} 轮自主对话...")

                    # v3.0.0: 使用 CrewAI 或降级模式
                    if st.session_state.crew_manager and CREWAI_AVAILABLE:
                        # CrewAI 模式：让 Agent 自主决定是否发言
                        try:
                            responses = st.session_state.crew_manager.run_conversation_round(
                                user_message=None,  # 自主对话，无用户输入
                                character_memories=st.session_state.character_memories
                            )

                            # 将结果添加到记忆
                            for resp in responses:
                                if resp['content'] and resp['content'] != 'PASS':
                                    add_group_message(resp['speaker'], resp['content'], 'character')

                        except Exception as e:
                            st.error(f"CrewAI 执行错误: {str(e)}")
                            # 降级
                            _fallback_sequential_generation(None, use_real_api, api_key, status_placeholder)
                    else:
                        # 传统模式
                        _fallback_sequential_generation(None, use_real_api, api_key, status_placeholder)

                status_placeholder.success(f"✅ 完成 {int(num_rounds)} 轮自主对话！")
                st.rerun()

        else:
            # 私聊模式
            if not st.session_state.selected_character:
                st.info("请在左侧选择一个角色进行私聊")
                return

            selected_char_name = st.session_state.selected_character
            selected_char = next((c for c in st.session_state.characters if c['name'] == selected_char_name), None)

            if not selected_char:
                st.error("未找到选中的角色")
                return

            st.caption(f"与 {selected_char_name} 私聊 | 场景：{st.session_state.scene}")

            # 获取该角色的私聊消息
            private_messages = get_private_messages(selected_char_name)

            # 显示私聊历史
            chat_container = st.container()
            with chat_container:
                for msg in private_messages:
                    render_chat_message(msg)

            # 用户输入
            user_input = st.chat_input(f"与 {selected_char_name} 私聊...")

            if user_input:
                # 添加用户私聊消息
                add_private_message(selected_char_name, '你', user_input, 'user')

                # 生成角色回复（基于角色的完整记忆）
                with st.spinner(f"{selected_char_name} 正在回复..."):
                    # 获取角色的完整记忆（群聊+私聊）
                    char_memory = get_character_memory(selected_char_name)

                    if use_real_api and api_key:
                        reply_content = generate_single_reply_with_gemini(
                            st.session_state.scene,
                            selected_char,
                            st.session_state.characters,
                            char_memory,
                            is_initial=False,
                            api_key=api_key
                        )
                    else:
                        reply_content = mock_generate_single_reply(
                            st.session_state.scene,
                            selected_char,
                            char_memory,
                            is_initial=False
                        )

                    # 添加角色的私聊回复
                    add_private_message(selected_char_name, selected_char_name, reply_content, 'character')

                st.rerun()

        # 导出对话按钮
        st.markdown("---")
        col1, col2 = st.columns([1, 1])

        with col1:
            if st.session_state.chat_mode == 'group':
                export_text = "\n".join([
                    f"{msg['speaker']}：{msg['content']}"
                    for msg in st.session_state.shared_events
                ])
                st.download_button(
                    label="📥 导出群聊记录",
                    data=export_text,
                    file_name="group_chat.txt",
                    mime="text/plain"
                )

        with col2:
            if st.session_state.chat_mode == 'private' and st.session_state.selected_character:
                char_name = st.session_state.selected_character
                private_msgs = get_private_messages(char_name)
                export_text = "\n".join([
                    f"{msg['speaker']}：{msg['content']}"
                    for msg in private_msgs
                ])
                st.download_button(
                    label=f"📥 导出与{char_name}的私聊",
                    data=export_text,
                    file_name=f"private_chat_{char_name}.txt",
                    mime="text/plain"
                )


if __name__ == "__main__":
    main()
