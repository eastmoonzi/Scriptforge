# Scriptforge

写剧本的人都知道那种时刻：人物已经在脑子里活了，对白却卡在手指尖，写出来的句子不像那个人说的话。

Scriptforge 从这里出发。后台跑着四个 AI Agent：编剧规划这场戏要去哪里，导演告诉每个角色该怎么演，角色按自己的人设开口说话，审稿人最后检查有没有出戏。生成的对白逐字流入编辑器，你可以随时打断。

编辑器本身支持 Fountain 格式。写完即是标准剧本，导出可直接交付 Final Draft。

---

## 它是怎么工作的

每个角色背后有两条记忆：所有人共享的群聊历史，以及只属于这个角色的私密信息。生成前，系统从 ChromaDB 向量库里召回最相关的片段，拼进 prompt——角色不会失忆，也不会把秘密随便说出去。

风格由模板控制。悬疑、喜剧、现实主义三套预设，每套都带正面示例和反面示例，用 few-shot 的方式约束模型的语言风格。系统也会根据场景描述里的关键词自动推荐合适的模板。

生成结束后，三项指标量化评估这轮对白：CPD 看各角色语言风格是否真的有区分度，DE 检测信息密度和废话率，OOC 由 LLM 直接判断角色有没有说"不像他的话"。

没有 API Key 也能跑——系统用 mock 数据走完整个流程，界面功能全部可用。

---

## 上手

需要 Python 3.12+、Node.js 18+。桌面版额外需要 Rust。

```bash
# 后端
cd backend && pip install -r requirements.txt
cd .. && uvicorn backend.main:app --reload --port 8000

# 前端（新开终端）
cd frontend && npm install && npm run dev
```

打开 `http://localhost:3000`，在 AI 面板填写 Gemini 或 DeepSeek 的 API Key，添加几个角色和人设，点「生成下一段」。

也可以在根目录放 `.env` 文件预配置：

```env
GEMINI_API_KEY=your_gemini_api_key
```

---

## 技术构成

后端是 FastAPI，ChromaDB 做向量记忆，CrewAI 驱动多 Agent 流水线。前端是 Next.js 16 + React 19 + TipTap，Zustand 管状态。桌面壳是 Tauri 2，把 Python 后端作为 sidecar 内嵌，用户无需手动启动服务。LLM 支持 Google Gemini 和 DeepSeek，默认跑 `gemini-2.0-flash-exp`。

CrewAI 不可用时降级为顺序调用，再失败则降级为 mock，每层都有兜底。

项目数据存本地 SQLite，向量记忆存本地 ChromaDB，浏览器端每五秒 localStorage 自动保存。没有任何数据上传到远程服务器。

---

MIT © 2026 Eastmoon
