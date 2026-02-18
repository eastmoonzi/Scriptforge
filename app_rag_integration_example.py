"""
RAG 集成示例代码
展示如何将 RAG 记忆系统集成到 app.py

v3.2.0 - 可选功能
"""

# ============= 1. 导入 RAG 模块 =============

from memory_rag import RAGMemorySystem

# ============= 2. 初始化 session_state（添加到 init_session_state()）=============

def init_session_state():
    """初始化会话状态"""
    # ... 现有代码 ...

    # v3.2.0: RAG 记忆系统
    if 'use_rag' not in st.session_state:
        st.session_state.use_rag = False  # 默认关闭

    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = None


# ============= 3. 添加 UI 开关（添加到侧边栏）=============

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # ... 现有 API 配置 ...

        # v3.2.0: RAG 记忆系统开关
        if use_real_api and api_key:
            st.markdown("---")
            st.header("🧠 RAG 记忆系统")

            use_rag = st.checkbox(
                "启用 RAG（语义检索）",
                value=st.session_state.use_rag,
                help="使用向量数据库和语义检索，智能检索相关历史对话"
            )
            st.session_state.use_rag = use_rag

            if use_rag:
                st.success("✅ 使用混合检索（时间+语义）")
                st.caption("📊 检索策略：最近10条 + 相关5条")

                # 初始化 RAG 系统
                if st.session_state.rag_system is None:
                    try:
                        st.session_state.rag_system = RAGMemorySystem(
                            api_key=api_key,
                            persist_directory="./chroma_db"
                        )
                        st.success("RAG 系统初始化成功")
                    except Exception as e:
                        st.error(f"RAG 初始化失败: {str(e)}")
                        st.session_state.use_rag = False
            else:
                st.info("ℹ️ 使用传统时间窗口检索")


# ============= 4. 修改消息添加函数（同步到 RAG）=============

def add_group_message(speaker: str, content: str, msg_type: str = 'character'):
    """
    添加群聊消息（所有角色都能看到）
    v3.2.0: 同步到 RAG 系统
    """
    message = {
        'timestamp': datetime.now().isoformat(),
        'speaker': speaker,
        'content': content,
        'type': 'group',
        'msg_type': msg_type,
        'visible_to': 'all'
    }

    # 添加到共享事件流
    st.session_state.shared_events.append(message)

    # 添加到所有角色的记忆
    for char_name in st.session_state.character_memories:
        st.session_state.character_memories[char_name].append(message.copy())

        # v3.2.0: 同步到 RAG 系统
        if st.session_state.use_rag and st.session_state.rag_system:
            st.session_state.rag_system.add_memory(
                character_name=char_name,
                speaker=speaker,
                content=content,
                msg_type='group',
                timestamp=message['timestamp']
            )


def add_private_message(character_name: str, speaker: str, content: str, msg_type: str = 'character'):
    """
    添加私聊消息（只有指定角色能看到）
    v3.2.0: 同步到 RAG 系统
    """
    message = {
        'timestamp': datetime.now().isoformat(),
        'speaker': speaker,
        'content': content,
        'type': 'private',
        'msg_type': msg_type,
        'visible_to': [character_name]
    }

    # 添加到指定角色的记忆
    if character_name in st.session_state.character_memories:
        st.session_state.character_memories[character_name].append(message)

        # v3.2.0: 同步到 RAG 系统
        if st.session_state.use_rag and st.session_state.rag_system:
            st.session_state.rag_system.add_memory(
                character_name=character_name,
                speaker=speaker,
                content=content,
                msg_type='private',
                timestamp=message['timestamp']
            )


# ============= 5. 修改记忆获取函数（使用 RAG 检索）=============

def get_character_memory(character_name: str,
                        current_query: str = "",
                        limit: int = 20) -> List[Dict]:
    """
    获取角色的记忆
    v3.2.0: 支持 RAG 混合检索

    Args:
        character_name: 角色名称
        current_query: 当前查询（用于语义检索）
        limit: 返回条数（仅用于传统模式）

    Returns:
        角色的记忆列表
    """
    # v3.2.0: RAG 混合检索模式
    if st.session_state.use_rag and st.session_state.rag_system and current_query:
        try:
            # 使用混合检索：时间窗口 + 语义检索
            memories = st.session_state.rag_system.get_hybrid_context(
                character_name=character_name,
                current_query=current_query,
                recent_k=10,   # 最近10条
                relevant_k=5   # 相关5条
            )
            return memories
        except Exception as e:
            print(f"RAG 检索失败，降级到传统模式: {str(e)}")
            # 降级到传统模式

    # 传统模式：时间窗口检索
    if character_name not in st.session_state.character_memories:
        return []

    memories = st.session_state.character_memories[character_name]
    sorted_memories = sorted(memories, key=lambda x: x['timestamp'])
    return sorted_memories[-limit:] if limit > 0 else sorted_memories


# ============= 6. 修改生成回复函数（传入当前查询）=============

def generate_reply_with_context(scene: str,
                                character: Dict[str, str],
                                characters: List[Dict[str, str]],
                                user_message: str,  # 当前用户输入
                                api_key: str) -> str:
    """
    生成角色回复（使用 RAG 上下文）

    v3.2.0: 支持 RAG 语义检索
    """
    # 获取角色记忆（可能使用 RAG）
    char_memory = get_character_memory(
        character['name'],
        current_query=user_message,  # 传入当前查询
        limit=20
    )

    # 构建 Prompt（使用检索到的记忆）
    memory_text = "\n".join([
        f"{msg['speaker']}: {msg['content']}"
        for msg in char_memory
    ])

    prompt = f"""
你是 {character['name']}（{character['personality']}）
场景：{scene}

相关记忆（智能检索）：
{memory_text}

用户刚才说：{user_message}

请以 {character['name']} 的身份回应：
"""

    # 调用 Gemini 生成
    # ... 生成代码 ...


# ============= 7. 使用示例 =============

"""
用户体验流程：

1. 用户勾选"启用 RAG（语义检索）"
2. 系统初始化 ChromaDB
3. 用户开始对话：
   - 用户："你们还记得之前我们讨论的宝藏位置吗？"
   - 系统：
     a. 传统模式：返回最近20条消息（可能不包含宝藏讨论）
     b. RAG 模式：语义检索"宝藏位置"相关的历史消息（即使是很早之前的）
   - 角色基于相关记忆回应

效果对比：
- 传统模式：可能回答"我不记得了"（因为宝藏讨论在很早之前）
- RAG 模式：准确回答宝藏位置（因为检索到了相关历史）
"""


# ============= 8. 性能优化建议 =============

"""
1. 批量添加记忆：
   - 避免每条消息都调用 embedding API
   - 可以缓存 embedding 结果

2. 异步处理：
   - 将 embedding 生成放在后台线程
   - 避免阻塞用户体验

3. 成本控制：
   - Google Embedding API 有免费额度
   - 可以设置每日调用上限

4. 降级策略：
   - RAG 失败时自动降级到传统模式
   - 保证系统可用性
"""
