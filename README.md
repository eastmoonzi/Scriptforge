# Scriptforge

AI 驱动的剧本编辑器，支持多角色对白生成、导演模式与 RAG 记忆系统。  
基于 FastAPI + Next.js + Tauri 构建，使用 Google Gemini / DeepSeek 作为 LLM 后端。

---

## 核心特性

- **Fountain 原生支持**：直接编写 Fountain 格式剧本，支持导出为 FDX / HTML / PDF
- **多智能体对白生成**：编剧 → 导演 → 角色 → 审稿人四级流水线，生成高质量角色对白
- **双重记忆系统**：群聊公共记忆 + 角色私有记忆，基于 ChromaDB RAG 实现上下文连贯
- **风格模板引擎**：少样本戏剧风格模板 + 反模式示例，精准控制生成风格
- **对话质量评测**：CPD（角色个性分歧）/ DE（对话效率）/ OOC（出戏率）三项量化指标
- **桌面原生应用**：Tauri 封装，跨平台支持，后端以 sidecar 方式内嵌

---

## 快速上手

**环境要求**：Python 3.12+、Node.js 18+、Rust（仅桌面版）

```bash
# 1. 启动后端
cd backend && pip install -r requirements.txt
cd .. && uvicorn backend.main:app --reload --port 8000

# 2. 启动前端（新开终端）
cd frontend && npm install && npm run dev
```

在浏览器访问 `http://localhost:3000`，在 AI 面板中填写 API Key 即可开始使用。

也可以通过 `.env` 文件预先配置：

```env
GEMINI_API_KEY=your_gemini_api_key
```

---

## 架构概览

```
src-tauri/   Tauri 桌面壳（Rust）
frontend/    Next.js + TipTap 编辑器 + Zustand 状态管理
backend/     FastAPI + ChromaDB + SQLite
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12, FastAPI, ChromaDB, CrewAI |
| AI   | Google Gemini (`gemini-2.0-flash-exp`), DeepSeek |
| 前端 | Next.js 16, React 19, TipTap, Tailwind CSS 4 |
| 桌面 | Tauri 2, Rust |

---

## License

MIT © 2026 Eastmoon
