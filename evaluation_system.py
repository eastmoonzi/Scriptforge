"""
评测体系 - Evaluation System
用于量化评估多角色对话系统的质量

核心指标：
1. 人设离散度（Character Personality Divergence, CPD）
2. 对话有效率（Dialogue Efficiency, DE）
3. OOC 率（Out of Character Rate）
"""

import json
import re
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import Counter, defaultdict
import math


# Provider → OpenAI-compatible base URL mapping
_PROVIDER_BASE_URLS: dict = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "kimi": "https://api.moonshot.cn/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "minimax": "https://api.minimax.chat/v1",
    "zhipu": "https://open.bigmodel.cn/api/paas/v4",
}


def _tokenize(text: str) -> list[str]:
    """Tokenize text — use jieba for Chinese, regex for non-Chinese."""
    if any('\u4e00' <= ch <= '\u9fff' for ch in text):
        try:
            import jieba
            return [w for w in jieba.lcut(text) if w.strip()]
        except ImportError:
            pass
    return re.findall(r'\w+', text.lower())


class EvaluationMetrics:
    """评测指标计算器"""

    def __init__(self, api_key: Optional[str] = None,
                 provider: str = "gemini",
                 model: str = "gemini-2.0-flash-exp",
                 base_url: str = ""):
        """
        初始化评测系统

        Args:
            api_key: LLM API Key（用于 OOC 语义分析）
            provider: LLM 提供商（gemini / openai / deepseek / ...）
            model: 模型 ID
            base_url: 自定义 OpenAI 兼容端点
        """
        self.api_key = api_key
        self._provider = provider
        self._model = model
        self.llm = None

        if api_key:
            try:
                if provider == "gemini":
                    import google.genai as genai
                    self.llm = genai.Client(api_key=api_key)
                else:
                    from openai import OpenAI
                    url = base_url or _PROVIDER_BASE_URLS.get(provider, "")
                    if url:
                        self.llm = OpenAI(api_key=api_key, base_url=url)
            except ImportError:
                print("⚠️ LLM SDK 未安装，将使用基础指标")

    # ==================== 1. 人设离散度（CPD）====================

    def calculate_cpd(self, conversations: List[Dict]) -> Dict:
        """
        计算人设离散度（Character Personality Divergence）

        衡量不同角色发言的差异程度，数值越高表示角色性格越鲜明

        Args:
            conversations: 对话列表 [{'speaker': '角色名', 'content': '内容'}, ...]

        Returns:
            {
                'cpd_score': float,  # 0-100，越高越好
                'details': {
                    'vocabulary_diversity': float,  # 词汇多样性
                    'length_variance': float,       # 发言长度差异
                    'punctuation_diversity': float, # 标点风格差异
                    'character_scores': dict        # 每个角色的得分
                }
            }
        """
        # 按角色分组对话
        character_messages = defaultdict(list)
        for msg in conversations:
            if msg.get('speaker') and msg.get('content'):
                character_messages[msg['speaker']].append(msg['content'])

        if len(character_messages) < 2:
            return {'cpd_score': 0, 'details': {}}

        # 1. 词汇多样性分析
        vocab_diversity = self._calculate_vocabulary_diversity(character_messages)

        # 2. 发言长度差异
        length_variance = self._calculate_length_variance(character_messages)

        # 3. 标点风格差异
        punct_diversity = self._calculate_punctuation_diversity(character_messages)

        # 综合得分（加权平均）
        cpd_score = (
            vocab_diversity * 0.5 +      # 词汇差异占50%
            length_variance * 0.3 +       # 长度差异占30%
            punct_diversity * 0.2         # 标点差异占20%
        )

        return {
            'cpd_score': round(cpd_score, 2),
            'details': {
                'vocabulary_diversity': round(vocab_diversity, 2),
                'length_variance': round(length_variance, 2),
                'punctuation_diversity': round(punct_diversity, 2),
                'character_count': len(character_messages)
            }
        }

    def _calculate_vocabulary_diversity(self, character_messages: Dict[str, List[str]]) -> float:
        """计算角色间词汇多样性"""
        character_vocabs = {}

        for char, messages in character_messages.items():
            # 提取词汇（简单分词）
            words = []
            for msg in messages:
                # 移除标点，分词
                words.extend(_tokenize(msg))

            # 词频统计
            character_vocabs[char] = Counter(words)

        # 计算角色间的词汇重叠度（Jaccard 相似度的反向）
        chars = list(character_vocabs.keys())
        if len(chars) < 2:
            return 0

        overlaps = []
        for i in range(len(chars)):
            for j in range(i + 1, len(chars)):
                vocab1 = set(character_vocabs[chars[i]].keys())
                vocab2 = set(character_vocabs[chars[j]].keys())

                if not vocab1 or not vocab2:
                    continue

                # Jaccard 相似度
                intersection = len(vocab1 & vocab2)
                union = len(vocab1 | vocab2)
                similarity = intersection / union if union > 0 else 0

                # 差异度 = 1 - 相似度
                overlaps.append(1 - similarity)

        # 平均差异度，转换为 0-100 分
        avg_diversity = sum(overlaps) / len(overlaps) if overlaps else 0
        return avg_diversity * 100

    def _calculate_length_variance(self, character_messages: Dict[str, List[str]]) -> float:
        """计算角色发言长度的方差"""
        char_avg_lengths = {}

        for char, messages in character_messages.items():
            lengths = [len(msg) for msg in messages]
            char_avg_lengths[char] = sum(lengths) / len(lengths) if lengths else 0

        if len(char_avg_lengths) < 2:
            return 0

        # 计算方差
        avg_lengths = list(char_avg_lengths.values())
        mean = sum(avg_lengths) / len(avg_lengths)
        variance = sum((x - mean) ** 2 for x in avg_lengths) / len(avg_lengths)

        # 归一化到 0-100（假设标准差在 0-50 字符范围）
        std_dev = math.sqrt(variance)
        normalized = min(std_dev / 50 * 100, 100)

        return normalized

    def _calculate_punctuation_diversity(self, character_messages: Dict[str, List[str]]) -> float:
        """计算标点符号使用风格的差异"""
        char_punct_patterns = {}

        for char, messages in character_messages.items():
            punct_counts = Counter()
            for msg in messages:
                # 统计标点符号
                puncts = re.findall(r'[！？。，、；：""''…—（）《》【】]', msg)
                punct_counts.update(puncts)

            # 标点符号分布（归一化）
            total = sum(punct_counts.values())
            if total > 0:
                char_punct_patterns[char] = {
                    p: count / total for p, count in punct_counts.items()
                }
            else:
                char_punct_patterns[char] = {}

        # 计算角色间标点分布的差异（使用 KL 散度的简化版）
        chars = list(char_punct_patterns.keys())
        if len(chars) < 2:
            return 0

        differences = []
        for i in range(len(chars)):
            for j in range(i + 1, len(chars)):
                pattern1 = char_punct_patterns[chars[i]]
                pattern2 = char_punct_patterns[chars[j]]

                if not pattern1 or not pattern2:
                    continue

                # 简化的差异度：统计不同的标点种类占比
                all_puncts = set(pattern1.keys()) | set(pattern2.keys())
                diff = sum(abs(pattern1.get(p, 0) - pattern2.get(p, 0))
                          for p in all_puncts)
                differences.append(diff)

        avg_diff = sum(differences) / len(differences) if differences else 0
        return min(avg_diff * 100, 100)

    # ==================== 2. 对话有效率（DE）====================

    def calculate_de(self, conversations: List[Dict]) -> Dict:
        """
        计算对话有效率（Dialogue Efficiency）

        衡量对话中有效信息的密度，数值越高表示对话越高效

        Args:
            conversations: 对话列表

        Returns:
            {
                'de_score': float,  # 0-100
                'details': {
                    'avg_info_density': float,      # 平均信息密度
                    'repetition_rate': float,       # 重复率
                    'meaningless_rate': float,      # 无意义发言率
                    'total_rounds': int             # 总轮次
                }
            }
        """
        if not conversations:
            return {'de_score': 0, 'details': {}}

        # 1. 信息密度（基于独特词汇数 / 总字数）
        info_density = self._calculate_info_density(conversations)

        # 2. 重复率
        repetition_rate = self._calculate_repetition_rate(conversations)

        # 3. 无意义发言率
        meaningless_rate = self._calculate_meaningless_rate(conversations)

        # 综合得分
        de_score = (
            info_density * 0.4 +                    # 信息密度占40%
            (1 - repetition_rate) * 0.3 +           # 低重复率占30%
            (1 - meaningless_rate) * 0.3            # 低无意义率占30%
        ) * 100

        return {
            'de_score': round(de_score, 2),
            'details': {
                'avg_info_density': round(info_density, 2),
                'repetition_rate': round(repetition_rate, 2),
                'meaningless_rate': round(meaningless_rate, 2),
                'total_rounds': len(conversations)
            }
        }

    def _calculate_info_density(self, conversations: List[Dict]) -> float:
        """计算信息密度"""
        all_words = []
        for msg in conversations:
            content = msg.get('content', '')
            words = _tokenize(content)
            all_words.extend(words)

        if not all_words:
            return 0

        # 独特词汇数 / 总词汇数
        unique_ratio = len(set(all_words)) / len(all_words)
        return unique_ratio

    def _calculate_repetition_rate(self, conversations: List[Dict]) -> float:
        """计算重复率（相似内容占比）"""
        contents = [msg.get('content', '') for msg in conversations]

        if len(contents) < 2:
            return 0

        # 简单的重复检测：相同内容或高度相似内容
        repetitions = 0
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                similarity = self._simple_text_similarity(contents[i], contents[j])
                if similarity > 0.7:  # 相似度阈值
                    repetitions += 1

        max_pairs = len(contents) * (len(contents) - 1) / 2
        return repetitions / max_pairs if max_pairs > 0 else 0

    def _calculate_meaningless_rate(self, conversations: List[Dict]) -> float:
        """计算无意义发言率"""
        # 定义无意义模式（过短、过于通用等）
        meaningless_patterns = [
            r'^(好的?|是的?|嗯|哦|啊|呃|嘿|喂)$',
            r'^\.{3,}$',  # 只有省略号
            r'^[！？。，]{1,3}$',  # 只有标点
        ]

        meaningless_count = 0
        for msg in conversations:
            content = msg.get('content', '').strip()

            # 检查是否过短（<5字符）
            if len(content) < 5:
                meaningless_count += 1
                continue

            # 检查是否匹配无意义模式
            for pattern in meaningless_patterns:
                if re.match(pattern, content):
                    meaningless_count += 1
                    break

        return meaningless_count / len(conversations) if conversations else 0

    def _simple_text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算（基于词汇重叠）"""
        words1 = set(_tokenize(text1))
        words2 = set(_tokenize(text2))

        if not words1 or not words2:
            return 0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0

    # ==================== 3. OOC 率检测 ====================

    def calculate_ooc_rate(self, conversations: List[Dict],
                          character_profiles: Dict[str, str]) -> Dict:
        """
        计算 OOC 率（Out of Character Rate）

        检测角色发言是否符合人设

        Args:
            conversations: 对话列表
            character_profiles: 角色人设 {'角色名': '性格描述', ...}

        Returns:
            {
                'ooc_rate': float,  # 0-100，越低越好
                'ooc_cases': list,  # OOC 案例
                'details': dict
            }
        """
        if not self.llm:
            return {
                'ooc_rate': 0,
                'message': '需要 API Key 才能进行 OOC 检测',
                'ooc_cases': []
            }

        # 按角色分组
        character_messages = defaultdict(list)
        for msg in conversations:
            speaker = msg.get('speaker')
            if speaker and speaker in character_profiles:
                character_messages[speaker].append(msg)

        ooc_cases = []
        total_checked = 0

        # 对每个角色的发言进行采样检测（最多检查每角色5条）
        for char, messages in character_messages.items():
            profile = character_profiles[char]
            sample_size = min(5, len(messages))

            # 均匀采样
            step = len(messages) // sample_size if sample_size > 0 else 1
            sampled = messages[::step][:sample_size]

            for msg in sampled:
                total_checked += 1
                is_ooc = self._check_ooc_with_llm(
                    character_name=char,
                    personality=profile,
                    message=msg['content']
                )

                if is_ooc:
                    ooc_cases.append({
                        'character': char,
                        'content': msg['content'],
                        'expected_personality': profile
                    })

        ooc_rate = (len(ooc_cases) / total_checked * 100) if total_checked > 0 else 0

        return {
            'ooc_rate': round(ooc_rate, 2),
            'ooc_cases': ooc_cases,
            'details': {
                'total_checked': total_checked,
                'ooc_count': len(ooc_cases)
            }
        }

    def _check_ooc_with_llm(self, character_name: str,
                           personality: str, message: str) -> bool:
        """使用 LLM 检测单条发言是否 OOC"""
        try:
            prompt = f"""
你是一个角色性格一致性检测专家。请判断以下发言是否符合角色人设。

角色名称：{character_name}
角色性格：{personality}

发言内容：{message}

请回答：这条发言是否符合该角色的性格？（只需回答"符合"或"不符合"，不要解释）
"""

            if self._provider == "gemini":
                response = self.llm.models.generate_content(
                    model=self._model,
                    contents=prompt
                )
                result = response.text.strip()
            else:
                response = self.llm.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                )
                result = (response.choices[0].message.content or "").strip()

            return '不符合' in result

        except Exception as e:
            print(f"OOC 检测失败: {e}")
            return False

    # ==================== 综合评估 ====================

    def comprehensive_evaluation(self, conversations: List[Dict],
                                character_profiles: Optional[Dict[str, str]] = None) -> Dict:
        """
        综合评估

        Args:
            conversations: 对话列表
            character_profiles: 角色人设（可选，用于 OOC 检测）

        Returns:
            完整的评估报告
        """
        # 1. 人设离散度
        cpd_result = self.calculate_cpd(conversations)

        # 2. 对话有效率
        de_result = self.calculate_de(conversations)

        # 3. OOC 率（如果提供了人设）
        ooc_result = None
        if character_profiles:
            ooc_result = self.calculate_ooc_rate(conversations, character_profiles)

        # 综合得分（加权平均）
        scores = [cpd_result['cpd_score'], de_result['de_score']]
        if ooc_result:
            # OOC 率越低越好，转换为得分
            ooc_score = 100 - ooc_result['ooc_rate']
            scores.append(ooc_score)

        overall_score = sum(scores) / len(scores)

        return {
            'overall_score': round(overall_score, 2),
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'cpd': cpd_result,
                'de': de_result,
                'ooc': ooc_result
            },
            'summary': {
                'total_messages': len(conversations),
                'unique_characters': len(set(msg.get('speaker') for msg in conversations if msg.get('speaker')))
            }
        }


# ==================== 工具函数 ====================

def save_evaluation_report(report: Dict, output_path: str):
    """保存评估报告为 JSON"""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ 评估报告已保存: {output_path}")


def print_evaluation_report(report: Dict):
    """打印评估报告（友好格式）"""
    print("\n" + "="*60)
    print("📊 评估报告")
    print("="*60)

    print(f"\n🎯 综合得分: {report['overall_score']}/100")
    print(f"📅 评估时间: {report['timestamp']}")

    print(f"\n📈 基础统计:")
    summary = report['summary']
    print(f"  • 总消息数: {summary['total_messages']}")
    print(f"  • 参与角色数: {summary['unique_characters']}")

    metrics = report['metrics']

    # CPD
    print(f"\n💎 人设离散度 (CPD): {metrics['cpd']['cpd_score']}/100")
    cpd_details = metrics['cpd']['details']
    print(f"  • 词汇多样性: {cpd_details.get('vocabulary_diversity', 0)}/100")
    print(f"  • 长度差异: {cpd_details.get('length_variance', 0)}/100")
    print(f"  • 标点风格: {cpd_details.get('punctuation_diversity', 0)}/100")

    # DE
    print(f"\n⚡ 对话有效率 (DE): {metrics['de']['de_score']}/100")
    de_details = metrics['de']['details']
    print(f"  • 信息密度: {de_details.get('avg_info_density', 0):.2f}")
    print(f"  • 重复率: {de_details.get('repetition_rate', 0)*100:.1f}%")
    print(f"  • 无意义率: {de_details.get('meaningless_rate', 0)*100:.1f}%")

    # OOC
    if metrics.get('ooc'):
        ooc = metrics['ooc']
        print(f"\n🎭 OOC 率: {ooc['ooc_rate']:.1f}%")
        if ooc.get('ooc_cases'):
            print(f"  • 检测到 {len(ooc['ooc_cases'])} 个 OOC 案例")

    print("\n" + "="*60)


if __name__ == "__main__":
    # 测试示例
    print("评测系统测试")

    # 示例对话数据
    test_conversations = [
        {'speaker': '勇士', 'content': '让我打头阵！我不怕危险！'},
        {'speaker': '法师', 'content': '等等，让我先分析一下魔法波动...'},
        {'speaker': '盗贼', 'content': '嘿嘿，我去探探路，小心陷阱。'},
        {'speaker': '勇士', 'content': '前面有敌人，冲啊！'},
        {'speaker': '法师', 'content': '这个咒语需要3秒施法时间...'},
        {'speaker': '盗贼', 'content': '我已经绕到后面了，准备偷袭。'}
    ]

    evaluator = EvaluationMetrics()

    # 计算 CPD
    cpd_result = evaluator.calculate_cpd(test_conversations)
    print(f"\n人设离散度: {cpd_result['cpd_score']}/100")

    # 计算 DE
    de_result = evaluator.calculate_de(test_conversations)
    print(f"对话有效率: {de_result['de_score']}/100")

    # 综合评估
    character_profiles = {
        '勇士': '勇敢、冲动、喜欢冒险',
        '法师': '聪明、谨慎、善于分析',
        '盗贼': '狡猾、机智、行动迅速'
    }

    report = evaluator.comprehensive_evaluation(test_conversations, character_profiles)
    print_evaluation_report(report)
