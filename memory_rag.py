"""
RAG-based Memory System for Multi-Agent Chat
基于 RAG 的多智能体记忆系统

v3.2.0 新增功能
"""

from typing import List, Dict, Optional
import chromadb
from chromadb.config import Settings
import google.generativeai as genai
from datetime import datetime


class RAGMemorySystem:
    """
    RAG 记忆系统

    特性：
    - 向量存储：使用 ChromaDB 存储对话历史
    - 语义检索：基于语义相似度检索相关记忆
    - 混合检索：结合时间窗口和语义检索
    - 信息隔离：支持角色独立记忆（群聊+私聊）
    """

    def __init__(self, api_key: str, persist_directory: str = "./chroma_db"):
        """
        初始化 RAG 记忆系统

        Args:
            api_key: Google API Key（用于 embedding）
            persist_directory: ChromaDB 持久化目录
        """
        self.api_key = api_key

        # 配置 Google Embedding API
        genai.configure(api_key=api_key)

        # 初始化 ChromaDB（本地持久化）
        self.client = chromadb.Client(Settings(
            persist_directory=persist_directory,
            anonymized_telemetry=False
        ))

        # 创建集合（Collection）- 每个场景一个集合
        self.collection_name = f"memories_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Multi-agent conversation memories"}
        )

    def _generate_embedding(self, text: str) -> List[float]:
        """
        生成文本的向量表示

        Args:
            text: 输入文本

        Returns:
            向量（768维）
        """
        try:
            # 使用 Google 的 text-embedding-004 模型
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            print(f"Embedding 生成失败: {str(e)}")
            # 降级：返回零向量
            return [0.0] * 768

    def add_memory(self,
                   character_name: str,
                   speaker: str,
                   content: str,
                   msg_type: str = 'group',
                   timestamp: Optional[str] = None):
        """
        添加记忆到向量数据库

        Args:
            character_name: 角色名称
            speaker: 发言者
            content: 消息内容
            msg_type: 消息类型（'group' 或 'private'）
            timestamp: 时间戳（可选）
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        # 生成唯一 ID
        doc_id = f"{character_name}_{timestamp}_{msg_type}"

        # 生成 embedding
        embedding = self._generate_embedding(content)

        # 存储到 ChromaDB
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[{
                'character_name': character_name,
                'speaker': speaker,
                'msg_type': msg_type,
                'type': msg_type,
                'timestamp': timestamp,
                'visible_to': character_name if msg_type == 'private' else 'all'
            }]
        )

    def retrieve_relevant_memories(self,
                                   character_name: str,
                                   query: str,
                                   k: int = 5) -> List[Dict]:
        """
        检索与查询语义相关的记忆

        Args:
            character_name: 角色名称
            query: 查询文本（当前用户输入）
            k: 返回 top-k 条相关记忆

        Returns:
            相关记忆列表
        """
        # 生成查询向量
        query_embedding = self._generate_embedding(query)

        # 语义检索（过滤该角色可见的记忆）
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where={
                "$or": [
                    {"visible_to": "all"},           # 群聊消息
                    {"visible_to": character_name}   # 该角色的私聊
                ]
            }
        )

        # 转换为统一格式
        memories = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i, doc in enumerate(results['documents'][0]):
                metadata = results['metadatas'][0][i]
                memories.append({
                    'speaker': metadata['speaker'],
                    'content': doc,
                    'type': metadata['type'],
                    'msg_type': metadata['msg_type'],
                    'timestamp': metadata['timestamp'],
                    'visible_to': metadata['visible_to']
                })

        return memories

    def get_recent_memories(self,
                           character_name: str,
                           limit: int = 10) -> List[Dict]:
        """
        获取角色最近的记忆（按时间排序）

        Args:
            character_name: 角色名称
            limit: 返回最近 N 条

        Returns:
            最近的记忆列表
        """
        # 获取该角色的所有记忆
        results = self.collection.get(
            where={
                "$or": [
                    {"visible_to": "all"},
                    {"visible_to": character_name}
                ]
            },
            limit=1000  # 先获取全部
        )

        # 转换格式并按时间排序
        memories = []
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                metadata = results['metadatas'][i]
                memories.append({
                    'speaker': metadata['speaker'],
                    'content': doc,
                    'type': metadata['type'],
                    'msg_type': metadata['msg_type'],
                    'timestamp': metadata['timestamp'],
                    'visible_to': metadata['visible_to']
                })

        # 按时间戳排序
        memories.sort(key=lambda x: x['timestamp'])

        # 返回最近的 N 条
        return memories[-limit:] if limit > 0 else memories

    def get_hybrid_context(self,
                          character_name: str,
                          current_query: str,
                          recent_k: int = 10,
                          relevant_k: int = 5) -> List[Dict]:
        """
        混合检索：时间窗口 + 语义检索

        Args:
            character_name: 角色名称
            current_query: 当前查询
            recent_k: 最近 N 条消息
            relevant_k: 语义相关的 N 条消息

        Returns:
            合并去重后的记忆列表
        """
        # 1. 获取最近的消息（保证连贯性）
        recent = self.get_recent_memories(character_name, limit=recent_k)

        # 2. 语义检索相关消息
        relevant = self.retrieve_relevant_memories(character_name, current_query, k=relevant_k)

        # 3. 合并去重（按 timestamp 去重）
        seen = set()
        combined = []

        for memory in recent + relevant:
            timestamp = memory['timestamp']
            if timestamp not in seen:
                seen.add(timestamp)
                combined.append(memory)

        # 4. 按时间排序
        combined.sort(key=lambda x: x['timestamp'])

        return combined

    def clear_memories(self):
        """清空所有记忆"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )


def test_rag_memory():
    """测试 RAG 记忆系统"""
    print("RAG Memory System - Test")
    print("=" * 50)

    # 模拟测试（需要真实 API Key）
    # rag = RAGMemorySystem(api_key="your_api_key")

    # # 添加记忆
    # rag.add_memory("勇士", "勇士", "我们应该去左边的通道")
    # rag.add_memory("法师", "法师", "我感觉右边更安全")
    # rag.add_memory("盗贼", "盗贼", "让我先探路")

    # # 语义检索
    # results = rag.retrieve_relevant_memories("勇士", "应该往哪里走", k=3)
    # print("语义检索结果：", results)

    # # 混合检索
    # context = rag.get_hybrid_context("勇士", "我们现在的策略是什么？")
    # print("混合检索结果：", context)

    print("\n测试需要真实 API Key，请在实际环境中运行")


if __name__ == "__main__":
    test_rag_memory()
