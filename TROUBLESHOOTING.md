# GroupChat 故障排查指南

**版本**: v3.3.0
**更新时间**: 2026-01-15

本文档汇总了所有常见问题和解决方案，帮助你快速定位和解决问题。

---

## 📋 快速导航

- [按症状快速查找](#按症状快速查找)
- [详细解决方案](#详细解决方案)
  - [环境和安装问题](#环境和安装问题)
  - [CrewAI 相关问题](#crewai-相关问题)
  - [API 调用问题](#api-调用问题)
  - [RAG 系统问题](#rag-系统问题)
  - [对话质量问题](#对话质量问题)
  - [UI 和功能问题](#ui-和功能问题)
- [错误代码对照表](#错误代码对照表)
- [日志诊断方法](#日志诊断方法)
- [上报问题](#上报问题)

---

## 按症状快速查找

根据你遇到的现象，快速跳转到解决方案：

| 症状 | 跳转 |
|------|------|
| 应用无法启动 | [环境-Q1](#q1-应用无法启动) |
| ModuleNotFoundError | [环境-Q2](#q2-依赖缺失) |
| CrewAI 初始化失败 | [CrewAI-Q1](#q1-crewai-模式不可用) |
| Agent 不发言 / 都是 PASS | [CrewAI-Q2](#q2-agent-不发言或全是-pass) |
| API Key 无效 | [API-Q1](#q1-api-key-无效) |
| 配额超限 | [API-Q2](#q2-配额超限quota-exceeded) |
| RAG 初始化失败 | [RAG-Q1](#q1-rag-初始化失败) |
| RAG 检索速度慢 | [RAG-Q3](#q3-rag-检索速度慢) |
| 角色说话都一样 | [质量-Q1](#q1-角色说话都一样角色趋同) |
| 对话重复无效 | [质量-Q2](#q2-对话重复无意义) |
| 角色出戏（OOC） | [质量-Q3](#q3-角色出戏ooc) |
| 预设无法导入 | [UI-Q1](#q1-预设无法导入) |
| 对话无法导出 | [UI-Q2](#q2-对话无法导出) |
| 私聊模式异常 | [UI-Q3](#q3-私聊模式异常) |

---

## 详细解决方案

### 环境和安装问题

#### Q1: 应用无法启动

**症状：**
```bash
streamlit run app.py
# 没有任何反应，或报错
```

**解决步骤：**

**步骤 1：检查 Python 版本**
```bash
python --version
# 或
python3 --version
```
- **要求**：Python >= 3.10
- 如果版本过低，安装新版 Python

**步骤 2：检查依赖安装**
```bash
pip list | grep -E "streamlit|crewai|langchain"
```
- 应该看到：
  - `streamlit>=1.52.2`
  - `crewai>=1.7.2`
  - `langchain-google-genai`

**步骤 3：重新安装依赖**
```bash
pip install -r requirements.txt --upgrade
```

**步骤 4：使用完整路径启动**
```bash
# 如果有虚拟环境
source venv/bin/activate
streamlit run app.py

# 或使用完整路径
/opt/miniconda3/envs/salon/bin/streamlit run app.py
```

---

#### Q2: 依赖缺失

**症状：**
```
ModuleNotFoundError: No module named 'xxx'
```

**常见缺失模块和解决方案：**

| 缺失模块 | 安装命令 |
|---------|---------|
| `streamlit` | `pip install streamlit` |
| `crewai` | `pip install crewai` |
| `langchain_google_genai` | `pip install langchain-google-genai` |
| `chromadb` | `pip install chromadb` |
| `sentence_transformers` | `pip install sentence-transformers` |

**一键修复：**
```bash
pip install -r requirements.txt
```

---

#### Q3: 端口被占用

**症状：**
```
Error: Port 8501 is already in use
```

**解决方案：**

**方法 1：使用其他端口**
```bash
streamlit run app.py --server.port 8502
```

**方法 2：杀死占用进程**
```bash
# macOS/Linux
lsof -ti:8501 | xargs kill -9

# Windows
netstat -ano | findstr :8501
taskkill /PID [进程ID] /F
```

---

### CrewAI 相关问题

#### Q1: CrewAI 模式不可用

**症状：**
```
⚠️  CrewAI 初始化失败，已降级为传统模式
```

**可能原因和解决方案：**

**原因 1：依赖版本不兼容**
```bash
# 检查版本
pip show crewai

# 要求：>= 1.7.2
# 如果版本过低：
pip install --upgrade crewai
```

**原因 2：API Key 未配置或无效**
- 检查侧边栏是否勾选"使用真实 Gemini API"
- 检查 API Key 格式（应以 `AIzaSy` 开头）
- 尝试生成新的 API Key

**原因 3：网络问题**
```bash
# 测试网络连接
ping google.com
curl https://generativelanguage.googleapis.com
```

**原因 4：Python 版本问题**
```bash
# CrewAI 需要 Python >= 3.10
python --version
```

---

#### Q2: Agent 不发言或全是 PASS

**症状：**
- 点击"继续聊"后所有角色都输出 `PASS`
- 用户发言后无人回应

**这是正常还是异常？**

✅ **正常情况**（CrewAI 智能特性）：
- Agent 判断当前不适合发言
- 对话已经充分，无需补充
- 没有被提及或与自己无关

❌ **异常情况**（需要解决）：
- 每次都全员 PASS
- 即使提出明确问题也无人回应

**解决方案：**

**方法 1：提供更明确的引导**

❌ 不好：
```
用户："大家觉得怎么样？"
（问题过于宽泛，Agent 无话可说）
```

✅ 好：
```
用户："前面有红、蓝、绿三个按钮，按错会触发陷阱，你们觉得按哪个？"
（具体场景，Agent 可以分析）
```

**方法 2：提及特定角色**
```
用户："法师，你觉得这个魔法阵是什么意思？"
（直接提及，法师更可能回应）
```

**方法 3：使用自主对话功能**
- 侧边栏 → "自主对话控制"
- 设置 2-3 轮
- 让 Agent 自己互动

**方法 4：临时切换传统模式**
- 取消勾选"启用 CrewAI"
- 传统模式会强制所有角色发言
- 适合需要保证全员参与的场景

---

#### Q3: CrewAI 响应速度慢

**症状：**
- CrewAI 模式比传统模式慢 2-3 倍

**原因：**
- CrewAI 需要为每个 Agent 独立调用 LLM
- 每个 Agent 需要思考是否发言

**解决方案：**

**方法 1：使用更快的模型**
- 侧边栏 → 选择 `gemini-1.5-flash`
- Flash 模型速度更快（但稍弱）

**方法 2：减少角色数量**
- 建议 3-5 个角色
- 角色过多会显著降低速度

**方法 3：关闭 verbose 模式**
- 减少日志输出
- 提升性能

---

### API 调用问题

#### Q1: API Key 无效

**症状：**
```
Error: API_KEY_INVALID
Invalid API key provided
```

**解决步骤：**

**步骤 1：检查 API Key 格式**
- 应以 `AIzaSy` 开头
- 长度约 39 个字符
- 不包含空格或换行

**步骤 2：生成新的 API Key**
1. 访问 [Google AI Studio](https://ai.google.dev/)
2. 点击 "Get API Key"
3. 创建新的 API Key
4. 复制并粘贴到应用中

**步骤 3：检查 API Key 状态**
- 确保 API Key 未被禁用
- 确保未超过使用限制

**步骤 4：测试 API Key**
```bash
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"
```

---

#### Q2: 配额超限（Quota Exceeded）

**症状：**
```
Error: QUOTA_EXCEEDED
You have exceeded your quota
```

**免费版限制：**
- **RPM**（每分钟请求数）：15
- **TPM**（每分钟 Token 数）：1,000,000
- **RPD**（每天请求数）：1,500

**解决方案：**

**方法 1：等待配额重置**
- 免费配额每分钟重置
- 等待 1 分钟后重试

**方法 2：减少请求频率**
- 减少自主对话轮数
- 避免频繁刷新

**方法 3：升级账户**
- 考虑升级到付费账户
- 更高的配额限制

**方法 4：使用更小的模型**
- `gemini-1.5-flash` 消耗更少配额
- 速度更快，成本更低

---

#### Q3: 网络连接超时

**症状：**
```
Error: NETWORK_ERROR
Connection timeout
```

**解决方案：**

**方法 1：检查网络连接**
```bash
ping google.com
curl https://generativelanguage.googleapis.com
```

**方法 2：配置代理（如果需要）**
```bash
# 设置环境变量
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
```

**方法 3：增加超时时间**
在 `app.py` 或 `agent_crew.py` 中：
```python
# 找到 ChatGoogleGenerativeAI 初始化
llm = ChatGoogleGenerativeAI(
    model=model_id,
    google_api_key=api_key,
    temperature=0.7,
    timeout=120  # 增加超时时间到 120 秒
)
```

---

#### Q4: 模型不存在

**症状：**
```
Error: MODEL_NOT_FOUND
Model gemini-xxx not found
```

**可用模型列表：**

| 模型 ID | 特点 | 推荐场景 |
|---------|------|---------|
| `gemini-2.0-flash-exp` | 最新实验版 | 追求最新功能 |
| `gemini-1.5-pro` | 高性能 | 追求质量 |
| `gemini-1.5-flash` | 快速经济 | 追求速度 |

**解决方案：**
- 侧边栏 → 选择其他可用模型
- 推荐使用 `gemini-1.5-flash`（最稳定）

---

### RAG 系统问题

#### Q1: RAG 初始化失败

**症状：**
```
Error initializing RAG: chromadb not installed
```

**解决步骤：**

**步骤 1：安装 ChromaDB**
```bash
pip install chromadb
```

**步骤 2：安装相关依赖**
```bash
pip install langchain-chroma sentence-transformers
```

**步骤 3：检查版本兼容性**
```bash
pip show chromadb
# 推荐版本：>= 0.4.0
```

**步骤 4：完整重装（如果仍失败）**
```bash
pip uninstall chromadb langchain-chroma sentence-transformers -y
pip install chromadb langchain-chroma sentence-transformers
```

---

#### Q2: RAG 数据库损坏

**症状：**
```
Error loading ChromaDB
Database corrupted
```

**解决方案：**

**方法 1：清理并重建数据库**
```bash
# 删除数据库目录
rm -rf ./chroma_db

# 重启应用，会自动重建
streamlit run app.py
```

**方法 2：备份后清理**
```bash
# 备份
mv ./chroma_db ./chroma_db.backup

# 重启应用
streamlit run app.py
```

---

#### Q3: RAG 检索速度慢

**症状：**
- RAG 检索耗时 > 2 秒

**原因分析：**
- Embedding 生成：0.2-0.3s
- 向量检索：0.1-0.2s
- 重排序：0.1-0.2s

**优化方案：**

**方法 1：减少检索数量**
在 `memory_rag.py` 中：
```python
# 找到这一行
top_k = 10

# 改为
top_k = 5  # 减少检索数量
```

**方法 2：使用更快的 Embedding 模型**
```python
# 使用更小的模型
model_name = "all-MiniLM-L6-v2"  # 更快
```

**方法 3：关闭混合检索**
- 侧边栏 → 取消勾选"混合检索"
- 只使用语义检索

---

#### Q4: RAG 检索结果不相关

**症状：**
- 检索到的历史对话与当前话题无关

**可能原因：**
1. Embedding 模型不适合
2. 检索参数需要调整
3. 数据库中噪音数据过多

**解决方案：**

**方法 1：调整检索参数**
在 `memory_rag.py` 中：
```python
# 增加相似度阈值
similarity_threshold = 0.7  # 从 0.5 提高到 0.7
```

**方法 2：清理数据库**
```bash
rm -rf ./chroma_db
# 重新开始对话
```

**方法 3：使用关键词检索**
- 侧边栏 → 选择"关键词检索"
- 更精确但不理解语义

---

#### Q5: RAG 成本问题

**Q: RAG 会增加多少成本？**

**A**:
- **Embedding 成本**：Google Embedding API 免费额度充足
  - 免费：每天数千次调用
  - 付费：$0.0001/1000 tokens（极低）

- **总体成本增加**：约 30-50%
  - 主要增加在 embedding 生成
  - Gemini 生成成本不变

**示例**：100 轮对话
- 传统模式：~$1
- RAG 模式：~$1.3（增加 $0.3）

---

#### Q6: 关闭 RAG 功能

**Q: 可以关闭 RAG 吗？**

**A**: 可以！
- 侧边栏 → 取消勾选"启用 RAG 记忆检索"
- 自动降级到传统时间窗口模式
- 两种模式可随时切换
- 不影响现有对话

---

### 对话质量问题

#### Q1: 角色说话都一样（角色趋同）

**症状：**
```
勇士："我觉得可以试试"
法师："我也觉得可以试试"
盗贼："我也觉得可以试试"
```

**诊断方法：**
```bash
# 运行评测体系
python run_evaluation.py --api-key YOUR_KEY

# 查看 CPD（人设离散度）指标
# 如果 CPD < 60，说明角色趋同
```

**解决方案：**

**方法 1：强化人设对比**

❌ 不好：
```
勇士：勇敢
法师：聪明
盗贼：狡猾
```

✅ 好：
```
勇士：勇敢、冲动、直率、重视荣誉、不善言辞
法师：聪明、谨慎、理性、善于分析、话多
盗贼：狡猾、机智、谨慎、利益导向、话少
```

**方法 2：启用 Few-shot 模版**
- 侧边栏 → "Few-shot 剧本模版"
- 勾选"启用剧本模版"
- 选择合适的风格

**方法 3：查看 Bad Case 库**
```bash
cat bad_case_library.json
```
学习常见问题和解决方案

---

#### Q2: 对话重复无意义

**症状：**
- 角色重复他人观点
- 对话原地打转，无推进

**诊断方法：**
```bash
# 运行评测体系
python run_evaluation.py

# 查看 DE（对话有效率）指标
# 如果 DE < 70，说明对话冗余
```

**解决方案：**

**方法 1：避免过于宽泛的问题**

❌ 宽泛：
```
用户："大家觉得怎么样？"
（角色无话可说，只能客套）
```

✅ 具体：
```
用户："门上有三个按钮：红、蓝、绿，按错会触发陷阱，你们觉得按哪个？为什么？"
（有具体问题，角色可以分析）
```

**方法 2：启用 CrewAI 模式**
- CrewAI 允许 Agent 保持沉默
- 减少无意义发言

**方法 3：使用自主对话**
- 让 Agent 自己互动
- 避免用户过度引导

---

#### Q3: 角色出戏（OOC）

**症状：**
```
角色：中世纪骑士
发言："我用手机查一下地图"  ← 中世纪没有手机（出戏）
```

**诊断方法：**
```bash
# 运行评测体系（需要 API Key）
python run_evaluation.py --api-key YOUR_KEY

# 查看 OOC 率指标
# 如果 OOC > 15%，说明经常出戏
```

**解决方案：**

**方法 1：明确知识范围**

在人设中明确角色的知识背景：

```
角色：中世纪骑士
性格：勇敢、忠诚、虔诚
知识范围：剑术、骑马、中世纪礼仪、基督教信仰
不了解：现代科技、现代武器、现代社会
```

**方法 2：使用 Few-shot 模版**
- 提供符合人设的示例对话
- 引导 AI 保持角色一致性

**方法 3：定期检查**
- 使用评测体系定期检测
- 发现问题及时调整人设

---

#### Q4: 对话缺乏深度

**症状：**
- 对话流于表面
- 没有实质内容

**解决方案：**

**方法 1：利用私聊系统**
- 在私聊中传递秘密信息
- 让角色在群聊中巧妙利用

**方法 2：使用复杂场景**
```
❌ 简单："在房间里"
✅ 复杂："在密室中，墙上有古老的符文，地上有三具尸体，空气中弥漫着血腥味"
```

**方法 3：引入冲突**
- 设计对立的角色
- 制造矛盾和张力

---

### UI 和功能问题

#### Q1: 预设无法导入

**症状：**
- 上传预设文件后无反应
- 提示"文件格式错误"

**解决方案：**

**步骤 1：检查文件格式**
- 必须是 `.json` 文件
- 文件内容必须是有效的 JSON

**步骤 2：验证 JSON 格式**
```bash
# 使用在线工具验证
# https://jsonlint.com/

# 或使用命令行
python -m json.tool preset.json
```

**步骤 3：参考示例文件**
```bash
cat preset_example_castle.json
# 确保格式一致
```

**步骤 4：检查必需字段**
```json
{
  "scene": "场景描述",  ← 必需
  "characters": [       ← 必需
    {
      "name": "角色名",  ← 必需
      "personality": "性格"  ← 必需
    }
  ]
}
```

---

#### Q2: 对话无法导出

**症状：**
- 点击"导出对话"无反应
- 下载的文件为空

**解决方案：**

**方法 1：检查对话历史**
- 确保有对话内容
- 至少需要 1 条消息

**方法 2：检查浏览器设置**
- 允许网站下载文件
- 检查下载目录

**方法 3：手动复制**
- 在 UI 中查看对话历史
- 手动复制内容

---

#### Q3: 私聊模式异常

**症状：**
- 私聊内容泄露到群聊
- 其他角色知道了私聊内容

**原因：**
这可能是 AI 的误判，而非系统 bug。

**解决方案：**

**方法 1：强化 Prompt**
在 `app.py` 中，Prompt 已经明确：
```
- 可以利用私聊信息
- 但不要直接泄露
- 可以巧妙暗示
```

**方法 2：检查记忆**
- 侧边栏 → "角色记忆查看"
- 确认私聊记录只有对应角色拥有

**方法 3：运行评测**
```bash
python run_evaluation.py --api-key YOUR_KEY
# 检查 Bad Case 库中的"记忆混乱"案例
```

---

#### Q4: UI 响应慢或卡顿

**症状：**
- 界面加载慢
- 操作有延迟

**解决方案：**

**方法 1：关闭不需要的功能**
- 关闭 RAG（如果不需要）
- 减少角色数量

**方法 2：清理浏览器缓存**
```
Chrome: Ctrl+Shift+Delete
清除缓存和Cookie
```

**方法 3：重启应用**
```bash
# Ctrl+C 停止
# 重新启动
streamlit run app.py
```

---

## 错误代码对照表

| 错误代码 | 含义 | 常见原因 | 解决方案 |
|---------|------|---------|---------|
| `API_KEY_INVALID` | API Key 无效 | Key 错误或过期 | 重新生成 Key |
| `QUOTA_EXCEEDED` | 配额超限 | 请求过于频繁 | 等待或升级账户 |
| `NETWORK_ERROR` | 网络错误 | 无法连接服务器 | 检查网络连接 |
| `MODEL_NOT_FOUND` | 模型不存在 | 模型 ID 错误 | 更换其他模型 |
| `CREWAI_INIT_FAILED` | CrewAI 初始化失败 | 依赖或配置问题 | 检查依赖版本 |
| `RAG_INIT_FAILED` | RAG 初始化失败 | ChromaDB 未安装 | 安装 chromadb |
| `MEMORY_OVERFLOW` | 记忆溢出 | 对话过长 | 清空或导出记忆 |
| `INVALID_CHARACTER` | 角色配置无效 | 缺少必需字段 | 检查角色设置 |
| `FILE_FORMAT_ERROR` | 文件格式错误 | JSON 格式不正确 | 验证 JSON 格式 |
| `TIMEOUT` | 请求超时 | 网络慢或服务忙 | 增加超时时间 |

---

## 日志诊断方法

### 查看实时日志

**方法 1：终端输出**
```bash
streamlit run app.py
# 日志会实时显示在终端
```

**方法 2：保存到文件**
```bash
streamlit run app.py 2>&1 | tee app.log
# 日志同时显示和保存
```

### 启用详细日志

在 `app.py` 中：
```python
# 找到这一行
verbose = False

# 改为
verbose = True
```

在 `agent_crew.py` 中：
```python
agent = Agent(
    role=char['name'],
    verbose=True,  # 启用详细日志
    ...
)
```

### 查看 CrewAI 日志

CrewAI 的详细日志：
```python
crew = Crew(
    agents=agents,
    tasks=tasks,
    verbose=2,  # 0=无, 1=基础, 2=详细
)
```

### 查看 ChromaDB 日志

RAG 系统日志：
```bash
# 检查数据库目录
ls -la ./chroma_db

# 查看数据库内容
python
>>> import chromadb
>>> client = chromadb.PersistentClient(path="./chroma_db")
>>> client.list_collections()
```

---

## 上报问题

如果以上方法都无法解决你的问题，请按以下步骤上报：

### 步骤 1：收集信息

1. **系统信息**
```bash
# 操作系统
uname -a  # macOS/Linux
ver  # Windows

# Python 版本
python --version

# 依赖版本
pip list | grep -E "streamlit|crewai|langchain|chromadb"
```

2. **错误日志**
- 复制完整的错误信息
- 包含堆栈跟踪（stack trace）

3. **复现步骤**
- 详细描述操作步骤
- 提供最小复现案例

### 步骤 2：提交 Issue

1. 访问 [GitHub Issues](https://github.com/yourusername/groupchat/issues)
2. 点击 "New Issue"
3. 使用以下模板：

```markdown
**问题描述**
简要描述问题

**环境信息**
- OS: macOS 13.0
- Python: 3.10.8
- Streamlit: 1.52.2
- CrewAI: 1.7.2

**复现步骤**
1. 启动应用
2. 导入预设
3. 点击"开始对话"
4. 出现错误

**预期行为**
应该...

**实际行为**
实际...

**错误日志**
```
粘贴错误日志
```

**截图**（如果有）
附上截图
```

### 步骤 3：等待响应

- 我们会在 24-48 小时内响应
- 可能需要你提供更多信息
- 请保持 Issue 开启直到问题解决

---

## 常见问题汇总（FAQ）

### 通用问题

**Q: 需要付费吗？**
A: 软件本身免费开源。只需要 Google Gemini API Key（有免费额度）。

**Q: 支持哪些语言？**
A: 支持所有 Gemini 支持的语言（100+），包括中英文混合。

**Q: 数据安全吗？**
A: 所有对话数据存储在本地，不会上传到服务器（除了调用 Gemini API）。

**Q: 可以商用吗？**
A: 可以！本项目采用 MIT 许可证，可自由商用。

### CrewAI 问题

**Q: 为什么有的 Agent 不发言？**
A: 这是 CrewAI 的智能特性！Agent 会根据上下文自主决策是否发言。

**Q: CrewAI 比传统模式慢吗？**
A: 是的，约慢 2-3 倍。因为需要为每个 Agent 独立决策。

**Q: 可以强制所有 Agent 发言吗？**
A: 可以！切换到传统模式即可。

### RAG 问题

**Q: RAG 必须开启吗？**
A: 不必须。短对话（<50 条）不需要 RAG。

**Q: RAG 数据存在哪里？**
A: 存储在本地 `./chroma_db` 目录。

**Q: 如何清理 RAG 数据？**
A: 删除 `./chroma_db` 目录即可。

---

## 参考资料

- [用户手册](USER_MANUAL.md) - 完整使用指南
- [API 文档](API.md) - 技术细节
- [CrewAI 指南](CREWAI_GUIDE.md) - CrewAI 架构
- [RAG 指南](RAG_GUIDE.md) - RAG 系统详解
- [评测体系指南](EVALUATION_SYSTEM_GUIDE.md) - 质量评估

---

**如果本文档没有解决你的问题，请联系我们！**

**GitHub Issues**: https://github.com/yourusername/groupchat/issues
