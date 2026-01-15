"""
CrewAI Multi-Agent System
基于 CrewAI 框架的真正多 Agent 对话系统
"""

from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List, Dict, Optional
import streamlit as st


class CharacterAgentCrew:
    """
    角色 Agent 团队管理器
    封装 CrewAI 的复杂性，提供简单的 API
    """

    def __init__(self, scene: str, characters: List[Dict[str, str]], api_key: str, model_id: str = "gemini-2.0-flash-exp", user_character: Optional[Dict[str, str]] = None):
        """
        初始化 Agent 团队

        Args:
            scene: 场景描述
            characters: 角色列表 [{'name': '...', 'personality': '...'}, ...]
            api_key: Google API Key
            model_id: Gemini 模型 ID (默认: gemini-2.0-flash-exp)
            user_character: 用户角色信息 {'name': '...', 'personality': '...'} (可选)
        """
        self.scene = scene
        self.characters = characters
        self.api_key = api_key
        self.model_id = model_id
        self.user_character = user_character or {'name': '你', 'personality': ''}

        # 初始化 Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model=model_id,
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=True  # 兼容性设置
        )

        # 创建 Agents
        self.agents = self._create_agents()

        # 对话历史（用于 Agent 间共享上下文）
        self.conversation_history = []

    def _create_agents(self) -> List[Agent]:
        """创建 CrewAI Agents"""
        agents = []

        for char in self.characters:
            # 构建 Agent 的系统提示
            backstory = f"""
你是 {char['name']}，性格特点：{char['personality']}

当前场景：{self.scene}

你的行为准则：
1. 始终保持你的性格特点
2. 根据对话上下文做出真实反应
3. 可以主动提出话题或回应其他人
4. 如果你有私聊记忆，可以巧妙利用但不要直接泄露
5. 让对话自然流畅
"""

            agent = Agent(
                role=char['name'],
                goal=f"在场景中以 {char['personality']} 的性格参与对话",
                backstory=backstory,
                llm=self.llm,
                verbose=False,  # 关闭详细输出（避免干扰 Streamlit）
                allow_delegation=False,  # 不允许委托（避免复杂性）
                memory=True  # 启用记忆
            )

            agents.append(agent)

        return agents

    def run_conversation_round(self,
                               user_message: Optional[str] = None,
                               character_memories: Optional[Dict[str, List]] = None,
                               single_speaker: bool = False,
                               next_speaker_index: int = 0) -> tuple[List[Dict[str, str]], int]:
        """
        运行一轮对话

        Args:
            user_message: 用户输入（可选，如果为 None 则是自主对话）
            character_memories: 角色的私有记忆 {角色名: [记忆列表]}
            single_speaker: 是否单次发言模式（v3.1.1 新增）
            next_speaker_index: 下一个发言的角色索引（仅在 single_speaker=True 时使用）

        Returns:
            (对话结果, 下一个发言者索引)
            - 对话结果: [{'speaker': '...', 'content': '...'}, ...]
            - 下一个发言者索引: 用于轮流发言
        """

        # 构建上下文
        context = self._build_context(user_message, character_memories)

        # v3.1.1: 单次发言模式 - 只为指定角色创建任务
        if single_speaker:
            # 确保索引有效
            speaker_index = next_speaker_index % len(self.agents)
            agents_to_run = [self.agents[speaker_index]]
            agent_indices = [speaker_index]
        else:
            # 多人模式 - 所有角色都参与
            agents_to_run = self.agents
            agent_indices = list(range(len(self.agents)))

        # 创建对话任务
        tasks = []
        for agent in agents_to_run:
            # v3.1.1: 根据是否有用户输入，调整任务描述
            if user_message:
                # 有用户输入：强调要回应用户
                task_description = f"""
{context}

作为 {agent.role}，用户刚才说了话，请决定如何回应：
1. 你是否想对用户的话做出回应？
2. 如果回应，你想说什么？

规则：
- 用户刚才说："{user_message}"
- 你应该认真考虑用户的话，并根据你的性格和记忆做出回应
- 如果你觉得这轮不适合发言，可以保持沉默（输出：PASS）
- 如果要发言，直接输出你想说的话（一句话，不要加角色名）
- 基于你的完整记忆（包括私聊）来决定
"""
            else:
                # 自主对话：自由决定是否发言
                task_description = f"""
{context}

作为 {agent.role}，这是一轮自主对话（没有用户输入），请决定：
1. 你是否想在这轮对话中发言？
2. 如果发言，你想说什么？

规则：
- 如果你觉得没有必要发言，可以保持沉默（输出：PASS）
- 如果要发言，直接输出你想说的话（一句话，不要加角色名）
- 可以主动提出话题，或回应其他角色
- 基于你的完整记忆（包括私聊）来决定
"""

            task = Task(
                description=task_description,
                agent=agent,
                expected_output="你的发言内容（或 PASS）"
            )
            tasks.append(task)

        # 创建 Crew 并执行
        crew = Crew(
            agents=agents_to_run,  # v3.1.1: 使用筛选后的 agents
            tasks=tasks,
            process=Process.sequential,  # 顺序执行
            verbose=False
        )

        # 执行任务
        try:
            result = crew.kickoff()

            # 解析结果（需要传入正确的索引）
            responses = self._parse_crew_result(result, tasks, agent_indices)

            # 更新对话历史
            if user_message:
                self.conversation_history.append({
                    'speaker': '用户',
                    'content': user_message
                })

            for resp in responses:
                if resp['content'] != 'PASS':
                    self.conversation_history.append(resp)

            # v3.1.1: 计算下一个发言者索引（轮流）
            if single_speaker:
                next_index = (next_speaker_index + 1) % len(self.agents)
            else:
                next_index = 0  # 多人模式下索引无意义

            return responses, next_index

        except Exception as e:
            st.error(f"CrewAI 执行错误: {str(e)}")
            # 降级到简单模式
            fallback_responses = self._fallback_simple_generation(user_message)
            # 计算下一个索引
            if single_speaker:
                next_index = (next_speaker_index + 1) % len(self.agents)
            else:
                next_index = 0
            return fallback_responses, next_index

    def _build_context(self,
                       user_message: Optional[str],
                       character_memories: Optional[Dict[str, List]]) -> str:
        """构建对话上下文"""
        context_parts = []

        # 场景
        context_parts.append(f"场景：{self.scene}")

        # 用户角色信息
        if self.user_character and self.user_character.get('personality'):
            context_parts.append(f"\n用户角色：{self.user_character['name']}（{self.user_character['personality']}）")
        else:
            context_parts.append(f"\n用户：{self.user_character['name']}")

        # 最近对话历史（使用 character_memories 中的群聊记录）
        if character_memories:
            # 从任意角色的记忆中获取群聊消息（所有角色的群聊记忆是相同的）
            first_char = list(character_memories.keys())[0]
            group_messages = [
                msg for msg in character_memories[first_char]
                if msg.get('type') == 'group'
            ]

            # 最近 10 条群聊消息
            recent = group_messages[-10:] if len(group_messages) > 10 else group_messages
            if recent:
                history_text = "\n".join([
                    f"{msg['speaker']}: {msg['content']}"
                    for msg in recent
                ])
                context_parts.append(f"\n群聊记录：\n{history_text}")

        # 用户输入（如果有的话，这部分作为强调）
        if user_message:
            context_parts.append(f"\n【用户刚才说】：{user_message}")
        else:
            context_parts.append("\n（自主对话，无用户输入）")

        return "\n".join(context_parts)

    def _parse_crew_result(self, result, tasks, agent_indices: List[int]) -> List[Dict[str, str]]:
        """
        解析 CrewAI 的返回结果

        Args:
            result: CrewAI 返回结果
            tasks: 任务列表
            agent_indices: 对应的 agent 索引列表（用于单次发言模式）
        """
        responses = []

        # CrewAI 返回的是最终结果，我们需要从 tasks 中提取
        for i, task in enumerate(tasks):
            # v3.1.1: 使用 agent_indices 获取正确的角色名
            agent_idx = agent_indices[i]
            agent_name = self.characters[agent_idx]['name']

            # 尝试获取任务输出
            try:
                output = str(task.output) if hasattr(task, 'output') else ""

                # 清理输出
                content = output.strip()

                # 过滤 PASS
                if content and content != "PASS" and "PASS" not in content.upper()[:10]:
                    responses.append({
                        'speaker': agent_name,
                        'content': content
                    })
            except:
                continue

        return responses

    def _fallback_simple_generation(self, user_message: Optional[str]) -> List[Dict[str, str]]:
        """降级方案：简单生成"""
        responses = []

        for char in self.characters:
            # 使用 LLM 直接生成
            prompt = f"""
你是 {char['name']}（{char['personality']}）
场景：{self.scene}
最近对话：{self.conversation_history[-5:] if self.conversation_history else '无'}
{'用户说：' + user_message if user_message else ''}

请简短回应（一句话）：
"""
            try:
                response = self.llm.invoke(prompt)
                content = response.content.strip()

                responses.append({
                    'speaker': char['name'],
                    'content': content
                })
            except:
                continue

        return responses


def test_crew():
    """测试函数"""
    characters = [
        {"name": "勇士", "personality": "勇敢、冲动"},
        {"name": "法师", "personality": "聪明、谨慎"},
        {"name": "盗贼", "personality": "狡猾、机智"}
    ]

    crew_manager = CharacterAgentCrew(
        scene="古堡探险",
        characters=characters,
        api_key="test_key"
    )

    print("CrewAI 系统初始化成功！")


if __name__ == "__main__":
    test_crew()
