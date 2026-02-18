"""
Few-shot 剧本模版管理系统
加载、选择和应用话剧风格模版到 Prompt 中
"""

import json
import os
from typing import List, Dict, Optional
from pathlib import Path


class TemplateManager:
    """剧本模版管理器"""

    def __init__(self, templates_dir: str = "templates"):
        """
        初始化模版管理器

        Args:
            templates_dir: 模版文件夹路径
        """
        self.templates_dir = templates_dir
        self.templates = {}
        self.load_all_templates()

    def load_all_templates(self):
        """加载所有模版文件"""
        if not os.path.exists(self.templates_dir):
            print(f"⚠️  模版目录不存在: {self.templates_dir}")
            return

        template_files = Path(self.templates_dir).glob("*.json")

        for file_path in template_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    template = json.load(f)

                template_id = template.get('template_id')
                if template_id:
                    self.templates[template_id] = template
                    print(f"✅ 加载模版: {template.get('template_name')} ({template_id})")
                else:
                    print(f"⚠️  模版缺少 template_id: {file_path}")

            except Exception as e:
                print(f"❌ 加载模版失败 {file_path}: {str(e)}")

        print(f"\n📚 共加载 {len(self.templates)} 个模版")

    def list_templates(self) -> List[Dict]:
        """列出所有可用模版"""
        return [
            {
                'id': template_id,
                'name': template.get('template_name'),
                'genre': template.get('genre'),
                'description': template.get('description')
            }
            for template_id, template in self.templates.items()
        ]

    def get_template(self, template_id: str) -> Optional[Dict]:
        """获取指定模版"""
        return self.templates.get(template_id)

    def get_few_shot_examples(self, template_id: str, max_examples: int = 2) -> List[Dict]:
        """
        获取 Few-shot 示例

        Args:
            template_id: 模版 ID
            max_examples: 最多返回几个示例

        Returns:
            示例列表
        """
        template = self.get_template(template_id)
        if not template:
            return []

        examples = template.get('few_shot_examples', [])
        return examples[:max_examples]

    def format_few_shot_for_prompt(self, template_id: str,
                                   max_examples: int = 1,
                                   include_analysis: bool = False) -> str:
        """
        格式化 Few-shot 示例为 Prompt 文本

        Args:
            template_id: 模版 ID
            max_examples: 包含几个示例
            include_analysis: 是否包含分析说明

        Returns:
            格式化后的文本
        """
        template = self.get_template(template_id)
        if not template:
            return ""

        examples = self.get_few_shot_examples(template_id, max_examples)
        if not examples:
            return ""

        prompt_text = f"【{template.get('template_name')}参考示例】\n\n"

        for i, example in enumerate(examples, 1):
            prompt_text += f"示例{i}：{example.get('scene', '')}\n\n"

            # 角色设定
            characters = example.get('characters', {})
            if characters:
                prompt_text += "角色：\n"
                for char_name, char_desc in characters.items():
                    prompt_text += f"- {char_name}: {char_desc}\n"
                prompt_text += "\n"

            # 对话
            dialogue = example.get('dialogue', [])
            prompt_text += "对话：\n"
            for turn in dialogue:
                speaker = turn.get('speaker', '')
                content = turn.get('content', '')
                prompt_text += f"{speaker}：{content}\n"

                if include_analysis and turn.get('analysis'):
                    prompt_text += f"   ↳ {turn['analysis']}\n"

            prompt_text += "\n"

            # 关键技巧
            if include_analysis and example.get('key_techniques'):
                prompt_text += "关键技巧：\n"
                for technique in example['key_techniques']:
                    prompt_text += f"• {technique}\n"
                prompt_text += "\n"

        # 添加反面示例
        anti_patterns = template.get('anti_patterns', [])
        if anti_patterns and include_analysis:
            prompt_text += "【避免以下问题】\n"
            for i, pattern in enumerate(anti_patterns[:2], 1):
                prompt_text += f"\n❌ 反例{i}：{pattern['bad_example']}\n"
                prompt_text += f"   问题：{pattern['issue']}\n"
                prompt_text += f"✅ 改进：{pattern['good_alternative']}\n"

        return prompt_text

    def generate_enhanced_prompt(self, template_id: str,
                                scene: str,
                                character: Dict[str, str],
                                base_prompt: str) -> str:
        """
        生成增强版 Prompt（融入 Few-shot）

        Args:
            template_id: 模版 ID
            scene: 场景描述
            character: 角色信息 {'name': '', 'personality': ''}
            base_prompt: 基础 Prompt

        Returns:
            增强后的 Prompt
        """
        template = self.get_template(template_id)
        if not template:
            return base_prompt

        # 获取风格特征
        language_features = template.get('language_features', {})
        vocabulary = language_features.get('vocabulary', [])
        sentence_patterns = language_features.get('sentence_patterns', [])
        tone = language_features.get('tone', '')

        # 获取 Few-shot 示例
        few_shot_text = self.format_few_shot_for_prompt(
            template_id,
            max_examples=1,
            include_analysis=False
        )

        # 构建增强 Prompt
        enhanced_prompt = f"""
你正在扮演角色：{character['name']}（性格：{character['personality']}）
场景：{scene}

【风格要求：{template.get('template_name')}】
• 语气：{tone}
• 推荐词汇：{', '.join(vocabulary[:5])}
• 句式参考：{', '.join(sentence_patterns[:2])}

{few_shot_text}

【重要提示】
- 严格保持你的性格特点
- 参考上述示例的对话风格和节奏
- 让对话自然、有深度、符合话剧表现形式
- 只输出你要说的一句话，不要加角色名，不要有其他说明

{base_prompt}

你的发言：
"""

        return enhanced_prompt

    def get_template_suggestions(self, scene_keywords: List[str]) -> List[str]:
        """
        根据场景关键词推荐合适的模版

        Args:
            scene_keywords: 场景关键词列表

        Returns:
            推荐的模版 ID 列表
        """
        suggestions = []

        # 简单的关键词匹配
        keyword_mapping = {
            '悬疑': ['drama_suspense'],
            '推理': ['drama_suspense'],
            '侦探': ['drama_suspense'],
            '案件': ['drama_suspense'],
            '喜剧': ['drama_comedy'],
            '搞笑': ['drama_comedy'],
            '幽默': ['drama_comedy'],
            '轻松': ['drama_comedy'],
            '现实': ['drama_realism'],
            '生活': ['drama_realism'],
            '社会': ['drama_realism'],
            '亲情': ['drama_realism']
        }

        for keyword in scene_keywords:
            for key, templates in keyword_mapping.items():
                if key in keyword.lower():
                    suggestions.extend(templates)

        # 去重
        return list(set(suggestions))


def demo():
    """演示模版系统的使用"""
    print("="*60)
    print("📚 Few-shot 剧本模版系统演示")
    print("="*60)

    # 初始化
    manager = TemplateManager()

    # 列出所有模版
    print("\n📋 可用模版:")
    for template_info in manager.list_templates():
        print(f"  • [{template_info['id']}] {template_info['name']}")
        print(f"    类型: {template_info['genre']}")
        print(f"    说明: {template_info['description']}")
        print()

    # 获取 Few-shot 示例
    print("="*60)
    print("📝 悬疑风格 Few-shot 示例:")
    print("="*60)
    few_shot_text = manager.format_few_shot_for_prompt(
        'drama_suspense',
        max_examples=1,
        include_analysis=True
    )
    print(few_shot_text)

    # 生成增强 Prompt
    print("="*60)
    print("🔧 生成增强版 Prompt:")
    print("="*60)
    enhanced_prompt = manager.generate_enhanced_prompt(
        template_id='drama_comedy',
        scene='搬家公司，准备搬运一架钢琴',
        character={'name': '老王', 'personality': '老员工、懒惰、爱吹牛'},
        base_prompt='请以老王的身份，在这个场景下说一句话。'
    )
    print(enhanced_prompt)

    # 模版推荐
    print("="*60)
    print("💡 场景模版推荐:")
    print("="*60)
    scene_keywords = ['悬疑', '推理', '案件']
    suggestions = manager.get_template_suggestions(scene_keywords)
    print(f"场景关键词: {scene_keywords}")
    print(f"推荐模版: {suggestions}")


if __name__ == "__main__":
    demo()
