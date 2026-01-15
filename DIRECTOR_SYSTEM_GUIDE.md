# 导演系统使用指南

**版本**: v3.3.0（Beta）
**更新时间**: 2026-01-15
**功能状态**: ⚠️ 实验性功能

---

## 📖 概述

导演系统是 GroupChat v3.3 引入的管理层 Agent 架构，模拟真实话剧创作流程，通过编剧、导演、审核三个管理层 Agent 来提升对话质量。

**核心理念**：
```
传统系统：用户 → AI 角色 → 输出
导演系统：用户 → 编剧规划 → 导演分配 → 角色表演 → 审核把关 → 输出
```

---

## 🎬 四个核心 Agent

### 1. 编剧 Agent（Writer）

**职责**：从宏观角度设计本轮对话的剧情走向

**输入**：
- 场景描述
- 角色列表
- 对话历史
- 用户输入（如果有）

**输出**：
```
剧情目标: 勇士和法师对是否开门产生分歧，盗贼发现门上有机关，
制造紧张气氛，为下一步剧情埋下伏笔。
```

**Prompt 设计**（`director_system.py:64-75`）：
```python
backstory = """
你是一位经验丰富的话剧编剧，擅长：
1. 剧情设计：根据当前对话状态，规划下一步剧情发展
2. 冲突制造：让角色之间产生有趣的矛盾和碰撞
3. 节奏把控：知道何时推进情节，何时留白
4. 伏笔埋设：在对话中暗藏线索，为后续发展做铺垫
"""
```

---

### 2. 导演 Agent（Director）

**职责**：将剧情目标转化为具体的角色任务

**输入**：
- 编剧的剧情目标
- 场景和角色信息
- 对话历史

**输出**（JSON格式）：
```json
{
  "selected_characters": ["勇士", "法师", "盗贼"],
  "instructions": {
    "勇士": "表现出急躁和冲动，主张立即开门，与法师产生冲突。用直率的语气。",
    "法师": "保持冷静和理性，反对贸然行动，建议先观察。用分析的语气。",
    "盗贼": "发现门上的机关，打断两人争论，制造紧张感。用谨慎的语气。"
  }
}
```

**关键决策**：
- 本轮哪些角色发言（不必全员）
- 每个角色的发言方向
- 角色的态度/语气
- 角色间的关系（支持/反对/中立）

**Prompt 设计**（`director_system.py:86-100`）：
```python
backstory = """
你是一位资深话剧导演，负责：
1. 节奏控制：决定本轮对话的快慢、紧张度
2. 发言分配：根据剧情需要，决定哪些角色发言
3. 氛围营造：通过指导语，帮助角色进入状态
4. 矛盾激化：鼓励角色间的真实互动和冲突
"""
```

---

### 3. 角色 Agents（Characters）

**职责**：根据导演指示生成具体对话

**输入**：
- 导演的任务分配
- 角色自身的人设
- 角色的记忆（群聊+私聊）

**输出示例**：
```python
[
  {'speaker': '勇士', 'content': '管那么多干什么！我们来就是找宝藏的，开门就完了！'},
  {'speaker': '法师', 'content': '等等，勇士！这扇门看起来不对劲，我感觉到了魔法波动...'},
  {'speaker': '盗贼', 'content': '法师说得对，你们看这里——门框上有细小的符文，这是陷阱机关！'}
]
```

---

### 4. 审核 Agent（Reviewer）

**职责**：检查生成的对话质量，决定是否通过

**检查维度**：
```python
1. ✅ 角色是否符合人设（有无 OOC）
2. ✅ 对话是否推进了剧情目标
3. ✅ 对话是否有实质内容（不是空话套话）
4. ✅ 角色间的互动是否自然
```

**输出示例**（JSON格式）：
```json
{
  "pass": true,
  "feedback": "对话质量良好。勇士的冲动、法师的理性、盗贼的谨慎都表现得很到位，推进了剧情，制造了悬念。",
  "scores": {
    "character_consistency": 9,
    "plot_advancement": 8,
    "content_quality": 9,
    "interaction_nature": 8
  }
}
```

**重试机制**：
- 如果 `pass: false`，返回阶段3重新生成对话
- 最多重试 2 次
- 达到最大次数后强制通过（避免死循环）

**Prompt 设计**（`director_system.py:108-123`）：
```python
backstory = """
你是一位严格的戏剧评论家，负责质量把关：
1. OOC 检测：检查角色发言是否符合人设
2. 逻辑审查：对话是否合理、前后是否矛盾
3. 深度评估：对话是否有实质内容，还是流于表面
4. 节奏判断：对话推进是否合理
"""
```

---

## 🔄 四阶段工作流程

```
┌─────────────────────────────────────────┐
│ 用户输入："前面有一扇门，我们该怎么办？"│
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 阶段1: 编剧规划                          │
│ 输出: "勇士和法师产生分歧，盗贼发现机关" │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 阶段2: 导演分配                          │
│ 输出: {                                 │
│   "selected_characters": ["勇士","法师","盗贼"],│
│   "instructions": {...}                 │
│ }                                       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 阶段3: 角色表演                          │
│ 勇士："开门就完了！"                     │
│ 法师："等等，这扇门不对劲..."            │
│ 盗贼："门框上有符文，这是机关！"         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│ 阶段4: 审核检查                          │
│ pass: true                              │
│ scores: {consistency:9, advancement:8}  │
└─────────────────────────────────────────┘
                    ↓
                  Pass?
                 /     \
               Yes      No
                ↓        ↓
             输出    重试（最多2次）
```

---

## 💻 使用方法

### 基础使用

```python
from director_system import DirectorSystem

# 1. 初始化导演系统
director = DirectorSystem(
    scene="古堡探险，三位冒险者在寻找宝藏",
    characters=[
        {"name": "勇士", "personality": "勇敢、冲动、直率"},
        {"name": "法师", "personality": "聪明、谨慎、理性"},
        {"name": "盗贼", "personality": "狡猾、机智、谨慎"}
    ],
    api_key="YOUR_GEMINI_API_KEY",
    model_id="gemini-2.0-flash-exp"
)

# 2. 运行一轮对话
result = director.run_conversation_round(
    user_message="前面有一扇门，我们该怎么办？",
    character_memories=None  # 或传入现有记忆
)

# 3. 查看结果
print(f"编剧规划: {result['plot_goal']}")
print(f"重试次数: {result['retry_count']}")
print(f"\n生成的对话:")
for dialogue in result['dialogues']:
    print(f"  {dialogue['speaker']}: {dialogue['content']}")
```

### 高级配置

```python
# 自定义重试次数
result = director.run_conversation_round(
    user_message="...",
    character_memories=memory_dict,
    max_retries=3  # 默认是 2
)

# 访问内部 Agent
print(director.writer_agent)
print(director.director_agent)
print(director.reviewer_agent)
print(director.character_agents)
```

---

## 📊 性能与成本

### 响应时间

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 编剧规划 | 0.8-1.2s | 简单的剧情目标生成 |
| 导演分配 | 1.0-1.5s | JSON 输出，稍慢 |
| 角色表演 | 2.0-3.0s | 多个角色顺序执行 |
| 审核检查 | 0.8-1.2s | 快速质量评估 |
| **总计** | **4.6-6.9s** | 不含重试 |

**重试影响**：
- 每次重试增加 2.8-4.2s（阶段3+4）
- 2次重试最多增加 8.4s

**对比传统系统**：
- 传统 CrewAI：2.5s
- 导演系统：4.6-6.9s（慢 2-3 倍）

### Token 消耗

| 阶段 | 输入 Token | 输出 Token | 成本估算（gemini-2.0-flash-exp）|
|------|-----------|-----------|--------------------------------|
| 编剧规划 | ~500 | ~50 | $0.0001 |
| 导演分配 | ~600 | ~150 | $0.0002 |
| 角色表演 | ~800 | ~150 | $0.0002 |
| 审核检查 | ~700 | ~100 | $0.0001 |
| **总计** | **~2600** | **~450** | **~$0.0006/轮** |

**对比传统系统**：
- 传统 CrewAI：~$0.0003/轮
- 导演系统：~$0.0006/轮（贵 2 倍）

---

## ⚖️ 优势与劣势

### ✅ 优势

1. **质量保证**
   - 审核不通过 → 自动重试
   - 量化评分 → 可追踪质量
   - 减少 OOC 和低质量对话

2. **灵活的角色选择**
   - 不必每轮都让所有角色发言
   - 导演根据剧情需要动态选择
   - 更符合真实对话场景

3. **可观测性**
   - 每个阶段的输出都可见
   - 便于调试和优化
   - 用户可看到"幕后信息"

4. **剧情连贯性**
   - 编剧统一规划剧情
   - 导演协调角色行为
   - 避免剧情跳跃

### ⚠️ 劣势

1. **响应时间较长**
   - 4个阶段顺序执行
   - 审核不通过还会重试
   - 比传统系统慢 2-3 倍

2. **Token 消耗较大**
   - 每个阶段都要调用 LLM
   - 成本增加约 100%

3. **复杂度增加**
   - 多个 Agent 协作
   - 调试难度增加

---

## 🔧 优化建议

### 1. 性能优化

**方法 1：使用更快的模型**
```python
director = DirectorSystem(
    ...,
    model_id="gemini-1.5-flash"  # 比 2.0-flash-exp 快 30%
)
```

**方法 2：减少重试次数**
```python
result = director.run_conversation_round(
    ...,
    max_retries=1  # 从 2 降到 1
)
```

**方法 3：异步处理（未来）**
```python
# 未来版本可能支持
# 并行执行某些阶段
```

### 2. 成本优化

**方法 1：编剧和导演用小模型**
```python
# 在 director_system.py 中修改
llm_small = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",  # 小模型
    ...
)

self.writer_agent = Agent(..., llm=llm_small)
self.director_agent = Agent(..., llm=llm_small)
```

**方法 2：缓存剧情目标**
```python
# 对于连续对话，可以复用上一轮的剧情目标
# 减少编剧 Agent 调用
```

---

## 🧪 测试与调试

### 运行测试

```bash
# 基础测试
python director_system.py

# 需要修改 demo() 函数中的 API Key
```

### 查看日志

```python
# 启用详细日志
crew = Crew(
    agents=agents,
    tasks=tasks,
    verbose=2  # 0=无, 1=基础, 2=详细
)
```

### 常见问题

**Q: 编剧输出的不是剧情目标，而是对话？**

A: 调整 Prompt，明确要求输出剧情目标而非对话内容。

**Q: 导演输出的不是 JSON？**

A: 在 Task description 中明确：
```python
"只输出 JSON，不要有其他说明。"
```

**Q: 审核总是不通过？**

A: 降低审核标准或减少 max_retries。

---

## 🔮 未来规划

### v3.4.0 - 集成到主应用

**计划**：
- [ ] 集成到 `app.py`
- [ ] 添加 UI 控制开关
- [ ] 与现有 CrewAI 模式并存
- [ ] 优化响应速度

**UI 设计草案**：
```
侧边栏：
☑️ 启用 CrewAI
☑️ 启用导演系统（实验性）

说明：
- 导演系统会增加 2-3 倍响应时间
- 但能显著提升对话质量
- 适合追求质量的场景
```

### v3.5.0 - 性能优化

- [ ] 并行执行某些阶段
- [ ] 缓存机制
- [ ] 流式输出
- [ ] 模型选择优化

---

## 📚 相关资源

- **实现代码**：`director_system.py`
- **Prompt 设计**：`prompt.md`（第三层：管理层 Prompt）
- **评测体系**：`EVALUATION_SYSTEM_GUIDE.md`（配合使用）
- **用户手册**：`USER_MANUAL.md`（第三部分 3.5 节）

---

## 💡 最佳实践

### 1. 何时使用导演系统

✅ **适合使用**：
- 追求高质量对话
- 复杂剧情场景
- 演示和展示
- 评测和对比

❌ **不适合使用**：
- 追求快速响应
- 日常聊天
- 简单场景
- 成本敏感场景

### 2. 与其他功能配合

**导演系统 + Few-shot 模版**：
```python
# 在 character agent 的 backstory 中加入模版内容
# 进一步提升对话风格
```

**导演系统 + 评测体系**：
```python
# 使用评测体系量化导演系统的效果
python run_evaluation.py --with-director
```

---

## ⚡ 快速开始示例

```python
# 1. 安装依赖
pip install crewai langchain-google-genai

# 2. 创建测试脚本
from director_system import DirectorSystem

# 3. 初始化
director = DirectorSystem(
    scene="古堡探险",
    characters=[
        {"name": "勇士", "personality": "勇敢、冲动"},
        {"name": "法师", "personality": "聪明、谨慎"},
        {"name": "盗贼", "personality": "狡猾、机智"}
    ],
    api_key="YOUR_API_KEY"
)

# 4. 运行对话
result = director.run_conversation_round(
    user_message="前面有一扇门",
    character_memories=None
)

# 5. 查看结果
for d in result['dialogues']:
    print(f"{d['speaker']}: {d['content']}")
```

---

**导演系统是一个强大的实验性功能，适合追求高质量对话的场景！** 🎭
