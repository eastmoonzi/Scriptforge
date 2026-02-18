# GroupChat 部署指南

本文档提供完整的项目部署和演示步骤。

---

## 📦 准备发布到 GitHub

### 1. 创建新的 GitHub 仓库

1. 访问 [GitHub](https://github.com/) 并登录
2. 点击右上角 `+` → `New repository`
3. 填写仓库信息：
   - **Repository name**: `groupchat`
   - **Description**: `AI 多智能体角色对话系统 - 基于 CrewAI 框架`
   - **Public/Private**: 选择 `Public`（如果希望作为作品集展示）
   - **不要**勾选 "Initialize with README"（我们已经有了）
4. 点击 `Create repository`

### 2. 推送代码到 GitHub

如果你需要创建新仓库（而不是使用现有的 Scriptforge），执行以下命令：

```bash
# 移除现有的远程仓库（如果需要）
git remote remove origin

# 添加新的远程仓库（替换为你的 GitHub 用户名）
git remote add origin https://github.com/YOUR_USERNAME/groupchat.git

# 推送代码
git branch -M main
git push -u origin main
```

如果你想使用现有的 Scriptforge 仓库，直接推送即可：

```bash
git push origin main
```

### 3. 验证文件完整性

确保以下文件都已正确上传到 GitHub：

```
✅ 核心文件
├── app.py                          # 主应用程序
├── agent_crew.py                   # CrewAI 封装
├── requirements.txt                # 依赖列表
└── .env.example                    # 环境变量示例

✅ 配置文件
├── .gitignore                      # Git 忽略规则
└── LICENSE                         # MIT 许可证

✅ 文档文件
├── README.md                       # 项目主页
├── README_v3.md                    # 使用指南
├── CREWAI_GUIDE.md                 # 技术详解
├── CHANGELOG.md                    # 版本历史
├── DEPLOYMENT.md                   # 部署指南（本文件）
└── preset_example_*.json           # 预设场景示例
```

---

## 🚀 本地运行 Demo

### 方式一：使用 pip（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/groupchat.git
cd groupchat

# 2. 创建虚拟环境（可选但推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量（可选）
cp .env.example .env
# 编辑 .env 文件，填入你的 GEMINI_API_KEY

# 5. 运行应用
streamlit run app.py
```

### 方式二：使用 Conda

```bash
# 1. 克隆仓库
git clone https://github.com/YOUR_USERNAME/groupchat.git
cd groupchat

# 2. 创建 Conda 环境
conda create -n groupchat python=3.11
conda activate groupchat

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行应用
streamlit run app.py
```

### 访问应用

启动成功后，会自动打开浏览器访问 `http://localhost:8501`

---

## 🔑 获取 Gemini API Key

1. 访问 [Google AI Studio](https://ai.google.dev/)
2. 点击 `Get API Key`
3. 创建新项目或选择现有项目
4. 复制生成的 API Key
5. 在应用侧边栏粘贴 API Key，或保存到 `.env` 文件

---

## 📝 快速体验 Demo

### 使用预设场景

1. 在侧边栏点击 `上传预设文件`
2. 选择项目中的预设文件：
   - `preset_example_startup.json` - 创业公司产品会议
   - `preset_example_castle.json` - 古堡探险 RPG
3. 点击 `载入预设`
4. 确保勾选 `启用 CrewAI 多 Agent 系统`
5. 点击 `开始对话`

### 自定义场景

1. 在侧边栏输入场景描述，例如：
   ```
   三位作家在讨论新小说的剧情走向
   ```

2. 添加角色（至少 2 个）：
   - **角色 1**: 悬疑作家 - 擅长设置悬念和伏笔，喜欢制造意外
   - **角色 2**: 言情作家 - 注重情感细节和人物关系
   - **角色 3**: 科幻作家 - 构建复杂的世界观和设定

3. 输入 Gemini API Key

4. 确保勾选 `启用 CrewAI 多 Agent 系统`

5. 点击 `开始对话`

---

## 🎯 Demo 演示技巧

### 展示 CrewAI 的智能性

**测试 1：自主决策**
```
输入："大家觉得这个方案怎么样？"
观察：不是所有角色都会发言，有些会选择沉默
```

**测试 2：私聊功能**
```
1. 发送群聊消息："我有个秘密计划"
2. 切换到私聊模式，对某个角色说："其实我想..."
3. 回到群聊，看该角色如何巧妙利用信息
```

**测试 3：自主对话**
```
点击"让 AI 自己聊"按钮
观察：角色之间会自发产生对话，而非机械回应
```

### 对比传统模式和 CrewAI 模式

1. 先关闭 `启用 CrewAI 多 Agent 系统`
2. 发送同样的消息
3. 再开启 CrewAI 模式
4. 对比响应的自然度和多样性

---

## 🌐 在线部署（可选）

### Streamlit Community Cloud（免费）

1. 访问 [Streamlit Cloud](https://streamlit.io/cloud)
2. 使用 GitHub 账号登录
3. 点击 `New app`
4. 选择你的 `groupchat` 仓库
5. 主文件路径：`app.py`
6. 在 `Advanced settings` 中添加 Secrets：
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```
7. 点击 `Deploy`

### Railway / Render（备选方案）

详见各平台的 Streamlit 部署文档。

---

## ⚠️ 常见问题

### 1. 依赖安装失败

**问题**：`pip install` 报错
**解决**：
```bash
# 升级 pip
pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 2. Streamlit 无法启动

**问题**：`streamlit: command not found`
**解决**：
```bash
# 确认 streamlit 已安装
pip list | grep streamlit

# 重新安装
pip install streamlit --upgrade
```

### 3. Gemini API 错误

**问题**：`API key not valid`
**解决**：
- 检查 API Key 是否正确复制（无多余空格）
- 确认 API 已启用 Gemini API 服务
- 检查网络连接（可能需要科学上网）

### 4. CrewAI 自动降级

**问题**：日志显示 "CrewAI 模式失败，降级为传统模式"
**解决**：
- 这是正常的容错机制
- 通常因为 Gemini API 限流或网络问题
- 稍后重试即可恢复

### 5. 角色不发言

**问题**：某些角色长时间沉默
**解决**：
- 这是 CrewAI 的正常行为（Agent 自主决策）
- 可以尝试 @ 该角色或提问引导
- 调整角色 prompt 使其更主动

---

## 📊 性能优化建议

### 1. 角色数量

- **推荐**：2-4 个角色
- **最多**：不超过 6 个（响应时间会变长）

### 2. API 配额管理

- Gemini 免费版有每日限额
- 考虑添加重试机制和错误提示
- 生产环境建议使用付费版

### 3. 记忆管理

- 长时间对话后可能导致 token 超限
- 定期使用"清空对话"功能
- 考虑实现记忆摘要机制

---

## 🎓 进阶自定义

### 修改 Agent 行为

编辑 `agent_crew.py` 中的 Agent 配置：

```python
agent = Agent(
    role=char_name,
    goal=char_prompt,
    backstory=f"{scenario}\n\n{char_prompt}",
    verbose=True,              # 显示详细日志
    allow_delegation=False,    # 禁止任务委托
    max_iter=3,                # 最大迭代次数
    llm=llm
)
```

### 添加工具调用

CrewAI 支持为 Agent 配备工具：

```python
from crewai_tools import SerperDevTool

search_tool = SerperDevTool()
agent = Agent(..., tools=[search_tool])
```

---

## 📞 技术支持

- **GitHub Issues**: [提交问题](https://github.com/YOUR_USERNAME/groupchat/issues)
- **文档**: 查看 `README_v3.md` 和 `CREWAI_GUIDE.md`
- **示例**: 参考 `preset_example_*.json` 文件

---

## 🔄 版本更新

查看 `CHANGELOG.md` 了解详细的版本历史和更新内容。

---

<div align="center">

**祝你 Demo 演示顺利！**

Made with ❤️ for AI & Multi-Agent Systems

</div>
