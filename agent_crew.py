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

    def __init__(self, scene: str, characters: List[Dict[str, str]], api_key: str):
        """
        初始化 Agent 团队

        Args:
            scene: 场景描述
            characters: 角色列表 [{'name': '...', 'personality': '...'}, ...]
            api_key: Google API Key
        """
        self.scene = scene
        self.characters = characters
        self.api_key = api_key

        # 初始化 Gemini LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
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
                               character_memories: Optional[Dict[str, List]] = None) -> List[Dict[str, str]]:
        """
        运行一轮对话

        Args:
            user_message: 用户输入（可选，如果为 None 则是自主对话）
            character_memories: 角色的私有记忆 {角色名: [记忆列表]}

        Returns:
            对话结果 [{'speaker': '...', 'content': '...'}, ...]
        """

        # 构建上下文
        context = self._build_context(user_message, character_memories)

        # 创建对话任务
        tasks = []
        for agent in self.agents:
            # 每个 Agent 独立决定是否发言
            task_description = f"""
{context}

作为 {agent.role}，请决定：
1. 你是否想在这轮对话中发言？
2. 如果发言，你想说什么？

规则：
- 如果你觉得没有必要发言，可以保持沉默（输出：PASS）
- 如果要发言，直接输出你想说的话（一句话，不要加角色名）
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
            agents=self.agents,
            tasks=tasks,
            process=Process.sequential,  # 顺序执行
            verbose=False
        )

        # 执行任务
        try:
            result = crew.kickoff()

            # 解析结果
            responses = self._parse_crew_result(result, tasks)

            # 更新对话历史
            if user_message:
                self.conversation_history.append({
                    'speaker': '用户',
                    'content': user_message
                })

            for resp in responses:
                if resp['content'] != 'PASS':
                    self.conversation_history.append(resp)

            return responses

        except Exception as e:
            st.error(f"CrewAI 执行错误: {str(e)}")
            # 降级到简单模式
            return self._fallback_simple_generation(user_message)

    def _build_context(self,
                       user_message: Optional[str],
                       character_memories: Optional[Dict[str, List]]) -> str:
        """构建对话上下文"""
        context_parts = []

        # 场景
        context_parts.append(f"场景：{self.scene}")

        # 最近对话历史
        if self.conversation_history:
            recent = self.conversation_history[-10:]  # 最近10条
            history_text = "\n".join([
                f"{msg['speaker']}: {msg['content']}"
                for msg in recent
            ])
            context_parts.append(f"\n最近对话：\n{history_text}")

        # 用户输入
        if user_message:
            context_parts.append(f"\n用户刚才说：{user_message}")
        else:
            context_parts.append("\n（自主对话，无用户输入）")

        return "\n".join(context_parts)

    def _parse_crew_result(self, result, tasks) -> List[Dict[str, str]]:
        """解析 CrewAI 的返回结果"""
        responses = []

        # CrewAI 返回的是最终结果，我们需要从 tasks 中提取
        for i, task in enumerate(tasks):
            agent_name = self.characters[i]['name']

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
