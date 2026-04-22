"""
导演系统 - Director System
引入管理级别的 Agent：导演、编剧、审核
v3.4.0 - 分层架构实验
"""

from crewai import Agent, Task, Crew, Process
from typing import List, Dict, Optional
import json

# Provider → OpenAI-compatible base URL mapping (duplicated here to avoid
# cross-module import complexity with backend.services)
_PROVIDER_BASE_URLS: dict = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.cn/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "minimax": "https://api.minimax.chat/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}


class DirectorSystem:
    """
    导演系统 - 三层架构

    架构：
    1. 编剧 Agent：规划剧情走向
    2. 导演 Agent：分配角色任务
    3. 角色 Agents：执行对话生成
    4. 审核 Agent：质量检查
    """

    def __init__(self, scene: str, characters: List[Dict[str, str]],
                 api_key: str, model_id: str = "gemini-2.0-flash-exp",
                 provider: str = "gemini", base_url: str = ""):
        """
        初始化导演系统

        Args:
            scene: 场景描述
            characters: 角色列表
            api_key: API Key
            model_id: 模型 ID
            provider: LLM 提供商
            base_url: 自定义 OpenAI 兼容端点
        """
        self.scene = scene
        self.characters = characters
        self.api_key = api_key
        self.model_id = model_id

        # 初始化 LLM — Gemini 用 LangChain Google 包装，其他走 OpenAI 兼容
        if provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            self.llm = ChatGoogleGenerativeAI(
                model=model_id,
                google_api_key=api_key,
                temperature=0.7,
                convert_system_message_to_human=True
            )
        else:
            from langchain_openai import ChatOpenAI
            resolved_url = base_url or _PROVIDER_BASE_URLS.get(provider, "")
            self.llm = ChatOpenAI(
                model=model_id,
                api_key=api_key,
                base_url=resolved_url,
                temperature=0.7,
            )

        # 创建管理层 Agents
        self.writer_agent = self._create_writer_agent()
        self.director_agent = self._create_director_agent()
        self.reviewer_agent = self._create_reviewer_agent()

        # 创建角色 Agents
        self.character_agents = self._create_character_agents()

        # 对话历史
        self.conversation_history = []

    def _create_writer_agent(self) -> Agent:
        """创建编剧 Agent"""
        return Agent(
            role="编剧（Scriptwriter）",
            goal="设计引人入胜的剧情走向，制造冲突和悬念，埋设伏笔",
            backstory=f"""
你是一位经验丰富的话剧编剧，擅长：
1. 剧情设计：根据当前对话状态，规划下一步剧情发展
2. 冲突制造：让角色之间产生有趣的矛盾和碰撞
3. 节奏把控：知道何时推进情节，何时留白
4. 伏笔埋设：在对话中暗藏线索，为后续发展做铺垫

当前场景：{self.scene}
角色：{', '.join([c['name'] for c in self.characters])}

你的任务是：为每一轮对话设计明确的剧情目标。
""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def _create_director_agent(self) -> Agent:
        """创建导演 Agent"""
        return Agent(
            role="导演（Director）",
            goal="控制对话节奏，分配角色发言，确保场面调度合理",
            backstory=f"""
你是一位资深话剧导演，负责：
1. 节奏控制：决定本轮对话的快慢、紧张度
2. 发言分配：根据剧情需要，决定哪些角色发言
3. 氛围营造：通过指导语，帮助角色进入状态
4. 矛盾激化：鼓励角色间的真实互动和冲突

当前场景：{self.scene}
角色：{', '.join([f"{c['name']}({c['personality']})" for c in self.characters])}

你的任务是：根据编剧的剧情目标，为每个需要发言的角色提供明确的发言指示。
""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def _create_reviewer_agent(self) -> Agent:
        """创建审核 Agent"""
        return Agent(
            role="审核（Reviewer）",
            goal="检查对话质量，确保角色不 OOC，对话有深度",
            backstory=f"""
你是一位严格的戏剧评论家，负责质量把关：
1. OOC 检测：检查角色发言是否符合人设
2. 逻辑审查：对话是否合理、前后是否矛盾
3. 深度评估：对话是否有实质内容，还是流于表面
4. 节奏判断：对话推进是否合理

当前场景：{self.scene}
角色人设：
{chr(10).join([f"- {c['name']}: {c['personality']}" for c in self.characters])}

你的任务是：审查生成的对话，给出"通过/重做"的判断和具体建议。
""",
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

    def _create_character_agents(self) -> List[Agent]:
        """创建角色 Agents"""
        agents = []
        for char in self.characters:
            agent = Agent(
                role=char['name'],
                goal=f"以{char['personality']}的性格参与对话",
                backstory=f"""
你是 {char['name']}，性格：{char['personality']}
场景：{self.scene}

你需要：
1. 严格遵循导演的指示
2. 保持你的性格特点
3. 与其他角色真实互动
4. 让对话自然流畅
""",
                llm=self.llm,
                verbose=False,
                allow_delegation=False,
                memory=True
            )
            agents.append(agent)
        return agents

    def run_conversation_round(self, user_message: Optional[str] = None,
                              character_memories: Optional[Dict[str, List]] = None,
                              max_retries: int = 2) -> Dict:
        """
        运行一轮完整的对话（含管理层）

        Args:
            user_message: 用户输入
            character_memories: 角色记忆
            max_retries: 最大重试次数（审核不通过时）

        Returns:
            {
                'plot_goal': '本轮剧情目标',
                'director_plan': '导演分配计划',
                'dialogues': [{'speaker': '...', 'content': '...'}],
                'review_result': {'pass': True/False, 'feedback': '...'},
                'retry_count': 重试次数
            }
        """

        # ========== 阶段1：编剧规划 ==========
        plot_goal = self._writer_plan(user_message, character_memories)

        # ========== 阶段2：导演分配 ==========
        director_plan = self._director_assign(plot_goal, user_message, character_memories)

        # ========== 阶段3：角色生成（支持重试）==========
        retry_count = 0
        feedback = ""
        while retry_count <= max_retries:
            dialogues = self._characters_perform(director_plan, character_memories, feedback=feedback)

            # ========== 阶段4：审核检查 ==========
            review_result = self._reviewer_check(plot_goal, director_plan, dialogues)

            if review_result['pass']:
                # 通过，跳出循环
                break
            else:
                # 不通过，重试
                retry_count += 1
                if retry_count <= max_retries:
                    feedback = review_result.get('feedback', '')
                    print(f"⚠️  审核不通过，第 {retry_count} 次重试...")
                else:
                    print(f"⚠️  已达最大重试次数，保留审核不通过状态")
                    review_result['forced_after_retries'] = True

        return {
            'plot_goal': plot_goal,
            'director_plan': director_plan,
            'dialogues': dialogues,
            'review_result': review_result,
            'retry_count': retry_count
        }

    def _writer_plan(self, user_message: Optional[str],
                    character_memories: Optional[Dict[str, List]]) -> str:
        """编剧规划剧情目标"""

        # 构建上下文
        context = self._build_context(user_message, character_memories)

        task = Task(
            description=f"""
{context}

作为编剧，你需要为这一轮对话设计明确的剧情目标。

思考：
1. 当前剧情处于什么阶段？（开场/发展/高潮/收尾）
2. 需要制造什么样的冲突或悬念？
3. 是否需要埋伏笔或推进已有线索？
4. 本轮对话的情感基调是什么？（紧张/轻松/沉重/幽默）

请用1-2句话描述本轮对话的剧情目标。

输出格式：
剧情目标: [你的目标描述]
""",
            agent=self.writer_agent,
            expected_output="本轮对话的剧情目标（1-2句话）"
        )

        crew = Crew(
            agents=[self.writer_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )

        result = crew.kickoff()
        plot_goal = str(result).strip()

        print(f"\n📝 编剧规划: {plot_goal}")
        return plot_goal

    def _director_assign(self, plot_goal: str, user_message: Optional[str],
                        character_memories: Optional[Dict[str, List]]) -> str:
        """导演分配任务"""

        context = self._build_context(user_message, character_memories)

        task = Task(
            description=f"""
{context}

编剧的剧情目标：{plot_goal}

作为导演，你需要：
1. 决定本轮哪些角色需要发言（可以是全部，也可以只选几个）
2. 为每个发言的角色提供明确的指示：
   - 发言方向：应该说什么类型的内容
   - 态度/语气：用什么样的态度
   - 与其他角色的关系：是支持、反对、还是中立

输出格式（JSON）：
{{
  "selected_characters": ["角色1", "角色2"],
  "instructions": {{
    "角色1": "发言指示...",
    "角色2": "发言指示..."
  }}
}}

只输出 JSON，不要有其他说明。
""",
            agent=self.director_agent,
            expected_output="角色发言分配计划（JSON格式）"
        )

        crew = Crew(
            agents=[self.director_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )

        result = crew.kickoff()
        director_plan = str(result).strip()

        print(f"\n🎬 导演分配: {director_plan[:100]}...")
        return director_plan

    def _characters_perform(self, director_plan: str,
                           character_memories: Optional[Dict[str, List]],
                           feedback: str = "") -> List[Dict]:
        """角色们执行表演"""

        # 解析导演计划
        try:
            plan = json.loads(director_plan)
            selected_chars = plan.get('selected_characters', [])
            instructions = plan.get('instructions', {})
        except:
            # 解析失败，让所有角色发言
            selected_chars = [c['name'] for c in self.characters]
            instructions = {c['name']: "按你的性格自然发言" for c in self.characters}

        # 只让选中的角色执行
        selected_agents = [
            agent for agent in self.character_agents
            if agent.role in selected_chars
        ]

        if not selected_agents:
            # 没有选中任何角色，默认让第一个发言
            selected_agents = [self.character_agents[0]]

        # 创建任务
        tasks = []
        for agent in selected_agents:
            char_name = agent.role
            instruction = instructions.get(char_name, "按你的性格自然发言")

            # 获取角色记忆
            memory_text = self._format_character_memory(
                char_name, character_memories
            )

            feedback_section = ""
            if feedback:
                feedback_section = f"""
【审稿人反馈（请根据反馈改进）】
{feedback}
"""

            task = Task(
                description=f"""
场景：{self.scene}

你的角色：{char_name}
{feedback_section}
【导演指示】
{instruction}

【你的记忆】
{memory_text}

请按照导演的指示，以你的性格发言。
只输出你要说的话，不要加角色名，不要有其他说明。
""",
                agent=agent,
                expected_output="角色的发言内容"
            )
            tasks.append(task)

        # 执行
        crew = Crew(
            agents=selected_agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=False
        )

        result = crew.kickoff()

        # 解析结果
        dialogues = []
        for i, task in enumerate(tasks):
            try:
                content = str(task.output).strip()
                if content and content != "PASS":
                    dialogues.append({
                        'speaker': selected_agents[i].role,
                        'content': content
                    })
            except:
                continue

        print(f"\n🎭 角色表演: {len(dialogues)}个角色发言")
        return dialogues

    def _reviewer_check(self, plot_goal: str, director_plan: str,
                       dialogues: List[Dict]) -> Dict:
        """审核检查质量"""

        # 格式化对话
        dialogue_text = "\n".join([
            f"{d['speaker']}: {d['content']}" for d in dialogues
        ])

        task = Task(
            description=f"""
编剧的剧情目标：{plot_goal}

导演的分配计划：{director_plan}

实际生成的对话：
{dialogue_text}

作为审核，请检查：
1. ✅ 角色是否符合人设（有无 OOC）
2. ✅ 对话是否推进了剧情目标
3. ✅ 对话是否有实质内容（不是空话套话）
4. ✅ 角色间的互动是否自然

输出格式（JSON）：
{{
  "pass": true/false,
  "feedback": "具体反馈...",
  "scores": {{
    "character_consistency": 0-10,
    "plot_advancement": 0-10,
    "content_quality": 0-10,
    "interaction_nature": 0-10
  }}
}}

只输出 JSON，不要有其他说明。
""",
            agent=self.reviewer_agent,
            expected_output="审核结果（JSON格式）"
        )

        crew = Crew(
            agents=[self.reviewer_agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False
        )

        result = crew.kickoff()

        # 解析结果
        try:
            review_result = json.loads(str(result).strip())
        except:
            # 解析失败，默认通过
            review_result = {
                'pass': True,
                'feedback': '审核解析失败，默认通过',
                'scores': {}
            }

        status = "✅ 通过" if review_result['pass'] else "❌ 不通过"
        print(f"\n📋 审核结果: {status}")
        if not review_result['pass']:
            print(f"   反馈: {review_result.get('feedback', '')}")

        return review_result

    def _build_context(self, user_message: Optional[str],
                      character_memories: Optional[Dict[str, List]]) -> str:
        """构建上下文"""
        context_parts = [f"场景：{self.scene}"]

        # 角色信息
        context_parts.append("\n角色：")
        for char in self.characters:
            context_parts.append(f"- {char['name']}: {char['personality']}")

        # 对话历史
        if character_memories:
            first_char = list(character_memories.keys())[0]
            group_messages = [
                msg for msg in character_memories[first_char]
                if msg.get('type') == 'group'
            ]
            recent = group_messages[-10:] if len(group_messages) > 10 else group_messages

            if recent:
                context_parts.append("\n最近对话：")
                for msg in recent:
                    context_parts.append(f"{msg['speaker']}: {msg['content']}")

        # 对话历史（跨轮累积）
        if self.conversation_history:
            context_parts.append("\n之前轮次的对话：")
            recent_history = self.conversation_history[-20:]  # keep last 20 entries
            for entry in recent_history:
                if isinstance(entry, dict) and 'speaker' in entry:
                    context_parts.append(f"{entry['speaker']}: {entry['content']}")

        # 用户输入
        if user_message:
            context_parts.append(f"\n用户刚才说：{user_message}")

        return "\n".join(context_parts)

    def _format_character_memory(self, char_name: str,
                                 character_memories: Optional[Dict[str, List]]) -> str:
        """格式化角色记忆"""
        if not character_memories or char_name not in character_memories:
            return "（暂无记忆）"

        memories = character_memories[char_name][-10:]
        memory_lines = []
        for msg in memories:
            memory_lines.append(f"{msg['speaker']}: {msg['content']}")

        return "\n".join(memory_lines) if memory_lines else "（暂无记忆）"


def demo():
    """演示导演系统"""
    print("="*60)
    print("🎬 导演系统演示")
    print("="*60)

    # 模拟配置
    scene = "古堡探险，三位冒险者在寻找宝藏"
    characters = [
        {"name": "勇士", "personality": "勇敢、冲动、直率"},
        {"name": "法师", "personality": "聪明、谨慎、理性"},
        {"name": "盗贼", "personality": "狡猾、机智、谨慎"}
    ]

    # 注意：需要真实的 API Key 才能运行
    api_key = "YOUR_API_KEY_HERE"

    print("\n初始化导演系统...")
    director_system = DirectorSystem(
        scene=scene,
        characters=characters,
        api_key=api_key
    )

    print("\n运行一轮对话...")
    result = director_system.run_conversation_round(
        user_message="前面有一扇门，我们该怎么办？",
        character_memories=None
    )

    print("\n" + "="*60)
    print("最终结果:")
    print(f"编剧目标: {result['plot_goal']}")
    print(f"重试次数: {result['retry_count']}")
    print(f"\n生成的对话:")
    for dialogue in result['dialogues']:
        print(f"  {dialogue['speaker']}: {dialogue['content']}")


if __name__ == "__main__":
    demo()
