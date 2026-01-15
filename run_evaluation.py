"""
自动化评测脚本
运行测试数据集并生成评估报告
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from evaluation_system import EvaluationMetrics, print_evaluation_report, save_evaluation_report


class AutomatedEvaluationRunner:
    """自动化评测运行器"""

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化评测运行器

        Args:
            api_key: Gemini API Key（可选，用于 OOC 检测）
        """
        self.evaluator = EvaluationMetrics(api_key=api_key)
        self.results = []

    def load_test_dataset(self, dataset_path: str = "test_dataset.json") -> Dict:
        """加载测试数据集"""
        if not os.path.exists(dataset_path):
            raise FileNotFoundError(f"测试数据集不存在: {dataset_path}")

        with open(dataset_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def run_single_scenario(self, scenario: Dict) -> Dict:
        """
        评估单个场景

        Args:
            scenario: 场景数据

        Returns:
            评估结果
        """
        print(f"\n{'='*60}")
        print(f"📋 评估场景: {scenario['name']} (ID: {scenario['id']})")
        print(f"{'='*60}")

        conversations = scenario.get('conversations', [])
        characters = scenario.get('characters', {})

        # 运行综合评估
        report = self.evaluator.comprehensive_evaluation(
            conversations=conversations,
            character_profiles=characters
        )

        # 添加场景元信息
        report['scenario_info'] = {
            'id': scenario['id'],
            'name': scenario['name'],
            'quality': scenario.get('quality', 'unknown'),
            'scene': scenario.get('scene', ''),
            'issue': scenario.get('issue', None)
        }

        # 对比预期指标
        expected = scenario.get('expected_metrics', {})
        if expected:
            report['comparison'] = self._compare_with_expected(report, expected)

        return report

    def _compare_with_expected(self, report: Dict, expected: Dict) -> Dict:
        """对比实际结果与预期指标"""
        comparison = {}

        # CPD 对比
        cpd_actual = report['metrics']['cpd']['cpd_score']
        cpd_expected = expected.get('cpd_score', '')

        comparison['cpd'] = {
            'actual': cpd_actual,
            'expected': cpd_expected,
            'pass': self._check_condition(cpd_actual, cpd_expected)
        }

        # DE 对比
        de_actual = report['metrics']['de']['de_score']
        de_expected = expected.get('de_score', '')

        comparison['de'] = {
            'actual': de_actual,
            'expected': de_expected,
            'pass': self._check_condition(de_actual, de_expected)
        }

        # OOC 对比
        if report['metrics'].get('ooc'):
            ooc_actual = report['metrics']['ooc']['ooc_rate']
            ooc_expected = expected.get('ooc_rate', '')

            comparison['ooc'] = {
                'actual': ooc_actual,
                'expected': ooc_expected,
                'pass': self._check_condition(ooc_actual, ooc_expected)
            }

        return comparison

    def _check_condition(self, actual: float, expected: str) -> bool:
        """
        检查实际值是否符合预期条件

        Args:
            actual: 实际值
            expected: 预期条件（如 ">70", "<10", "60-75"）

        Returns:
            是否符合
        """
        if not expected or expected == "任意":
            return True

        # 大于条件
        if expected.startswith('>'):
            threshold = float(expected[1:])
            return actual > threshold

        # 小于条件
        if expected.startswith('<'):
            threshold = float(expected[1:])
            return actual < threshold

        # 范围条件
        if '-' in expected:
            min_val, max_val = map(float, expected.split('-'))
            return min_val <= actual <= max_val

        return True

    def run_all_scenarios(self, dataset_path: str = "test_dataset.json") -> List[Dict]:
        """运行所有场景评测"""
        print("\n" + "="*60)
        print("🚀 开始自动化评测")
        print("="*60)

        # 加载数据集
        dataset = self.load_test_dataset(dataset_path)
        print(f"\n📦 加载数据集: {dataset['dataset_name']}")
        print(f"📊 版本: {dataset['version']}")

        all_scenarios = dataset.get('scenarios', []) + dataset.get('additional_test_cases', [])
        print(f"📋 测试场景数: {len(all_scenarios)}")

        # 运行评测
        results = []
        for i, scenario in enumerate(all_scenarios, 1):
            print(f"\n[{i}/{len(all_scenarios)}] 评估中...")

            try:
                result = self.run_single_scenario(scenario)
                results.append(result)

                # 打印简要结果
                self._print_brief_result(result)

            except Exception as e:
                print(f"❌ 评估失败: {str(e)}")
                results.append({
                    'scenario_info': {
                        'id': scenario.get('id'),
                        'name': scenario.get('name'),
                        'error': str(e)
                    }
                })

        self.results = results
        return results

    def _print_brief_result(self, result: Dict):
        """打印简要结果"""
        scenario_info = result.get('scenario_info', {})
        quality = scenario_info.get('quality', 'unknown')

        print(f"\n✅ 评估完成")
        print(f"   质量标签: {quality}")
        print(f"   综合得分: {result.get('overall_score', 0):.1f}/100")

        # 打印对比结果
        if result.get('comparison'):
            comp = result['comparison']
            print(f"\n   📊 指标对比:")

            for metric, data in comp.items():
                status = "✅" if data['pass'] else "❌"
                print(f"      {metric.upper()}: {data['actual']:.1f} (预期: {data['expected']}) {status}")

    def generate_summary_report(self) -> Dict:
        """生成汇总报告"""
        if not self.results:
            return {}

        # 按质量分组统计
        quality_groups = {}
        for result in self.results:
            quality = result.get('scenario_info', {}).get('quality', 'unknown')

            if quality not in quality_groups:
                quality_groups[quality] = []

            quality_groups[quality].append(result)

        # 计算统计数据
        summary = {
            'total_scenarios': len(self.results),
            'timestamp': datetime.now().isoformat(),
            'by_quality': {}
        }

        for quality, results in quality_groups.items():
            scores = [r.get('overall_score', 0) for r in results]

            summary['by_quality'][quality] = {
                'count': len(results),
                'avg_score': sum(scores) / len(scores) if scores else 0,
                'min_score': min(scores) if scores else 0,
                'max_score': max(scores) if scores else 0
            }

        # 通过率统计（如果有对比数据）
        pass_count = 0
        total_with_comparison = 0

        for result in self.results:
            if result.get('comparison'):
                total_with_comparison += 1
                # 检查所有指标是否都通过
                all_pass = all(data['pass'] for data in result['comparison'].values())
                if all_pass:
                    pass_count += 1

        if total_with_comparison > 0:
            summary['pass_rate'] = pass_count / total_with_comparison * 100
            summary['pass_count'] = pass_count
            summary['total_with_comparison'] = total_with_comparison

        return summary

    def print_summary_report(self):
        """打印汇总报告"""
        summary = self.generate_summary_report()

        print("\n" + "="*60)
        print("📊 评测汇总报告")
        print("="*60)

        print(f"\n总场景数: {summary['total_scenarios']}")
        print(f"评测时间: {summary['timestamp']}")

        if summary.get('pass_rate') is not None:
            print(f"\n✅ 通过率: {summary['pass_rate']:.1f}%")
            print(f"   通过: {summary['pass_count']}/{summary['total_with_comparison']}")

        print("\n📈 按质量分组统计:")
        for quality, stats in summary['by_quality'].items():
            print(f"\n   【{quality.upper()}】")
            print(f"      数量: {stats['count']}")
            print(f"      平均得分: {stats['avg_score']:.1f}/100")
            print(f"      得分范围: {stats['min_score']:.1f} - {stats['max_score']:.1f}")

        # 提升建议
        print("\n💡 改进建议:")
        if 'low' in summary['by_quality']:
            low_avg = summary['by_quality']['low']['avg_score']
            if low_avg > 50:
                print("   ⚠️ 低质量样本的得分偏高，评测系统可能需要调整权重")

        if 'high' in summary['by_quality']:
            high_avg = summary['by_quality']['high']['avg_score']
            if high_avg < 70:
                print("   ⚠️ 高质量样本的得分偏低，系统仍有改进空间")

        print("\n" + "="*60)

    def save_full_report(self, output_dir: str = "evaluation_reports"):
        """保存完整评测报告"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        detail_path = os.path.join(output_dir, f"detailed_results_{timestamp}.json")
        with open(detail_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 详细结果已保存: {detail_path}")

        # 保存汇总报告
        summary = self.generate_summary_report()
        summary_path = os.path.join(output_dir, f"summary_{timestamp}.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"💾 汇总报告已保存: {summary_path}")

        return detail_path, summary_path


def main():
    """主函数 - 命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="GroupChat 评测系统")
    parser.add_argument('--dataset', default='test_dataset.json', help='测试数据集路径')
    parser.add_argument('--api-key', default=None, help='Gemini API Key（用于OOC检测）')
    parser.add_argument('--output-dir', default='evaluation_reports', help='报告输出目录')
    parser.add_argument('--no-save', action='store_true', help='不保存报告文件')

    args = parser.parse_args()

    # 如果没有提供 API Key，尝试从环境变量获取
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("⚠️  未提供 API Key，将跳过 OOC 检测")
        print("   提示: 可通过 --api-key 参数或 GEMINI_API_KEY 环境变量提供")

    # 创建评测运行器
    runner = AutomatedEvaluationRunner(api_key=api_key)

    # 运行评测
    try:
        results = runner.run_all_scenarios(dataset_path=args.dataset)

        # 打印汇总
        runner.print_summary_report()

        # 保存报告
        if not args.no_save:
            runner.save_full_report(output_dir=args.output_dir)

        print("\n✅ 评测完成！")

    except Exception as e:
        print(f"\n❌ 评测失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
