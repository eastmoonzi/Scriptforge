Plan to implement                                                                                                                             │
│                                                                                                                                               │
│ 集成 Claude Code CLI 的剧本感知对话面板                                                                                                       │
│                                                                                                                                               │
│ Context                                                                                                                                       │
│                                                                                                                                               │
│ 用户希望在 Scriptforge 中添加一个 AI 对话面板，让文艺工作者用户可以与 AI 自由讨论剧本。通过集成 Claude Code CLI（而非直接调 API），用户可以： │
│ - 用自己已有的 Claude 订阅（Pro/Max），无需单独购买 API Key                                                                                   │
│ - 使用 Claude Code 的 skills、tools 等高级能力                                                                                                │
│ - 未来可扩展到其他 CLI（Gemini CLI、Copilot CLI 等）                                                                                          │
│                                                                                                                                               │
│ 核心思路：Scriptforge 在后台 spawn claude CLI 进程，把剧本上下文作为 system prompt 注入，流式读取输出并渲染到聊天界面。                       │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ 技术调研结论                                                                                                                                  │
│                                                                                                                                               │
│ Claude Code CLI 关键能力                                                                                                                      │
│                                                                                                                                               │
│ - claude -p "prompt" --output-format stream-json — 非交互流式输出（NDJSON）                                                                   │
│ - --system-prompt "..." — 注入剧本上下文                                                                                                      │
│ - --resume <session_id> — 多轮对话（复用会话）                                                                                                │
│ - --allowedTools "Read,Glob,Grep" — 限制工具范围                                                                                              │
│ - --max-turns N / --timeout S — 安全边界                                                                                                      │
│ - 认证：子进程自动继承已登录用户的 session，零配置                                                                                            │
│                                                                                                                                               │
│ Tauri 进程调用                                                                                                                                │
│                                                                                                                                               │
│ - @tauri-apps/plugin-shell 已安装（JS + Rust 两侧）                                                                                           │
│ - JS 端 Command.create('claude', args) 可直接 spawn + 流式读 stdout                                                                           │
│ - 需在 capabilities/default.json 添加 claude 的 spawn 权限                                                                                    │
│ - 现有 sidecar 模式可参考，但需要把 stdout 转发到前端（目前只 log 了）                                                                        │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ Step 1：Tauri 权限配置                                                                                                                        │
│                                                                                                                                               │
│ 修改 src-tauri/capabilities/default.json                                                                                                      │
│                                                                                                                                               │
│ 在 shell:allow-spawn 的 allow 列表中添加 claude：                                                                                             │
│                                                                                                                                               │
│ {                                                                                                                                             │
│   "identifier": "shell:allow-spawn",                                                                                                          │
│   "allow": [                                                                                                                                  │
│     { "name": "binaries/scriptforge-server", "sidecar": true, "args": true },                                                                 │
│     { "name": "claude", "sidecar": false, "args": true }                                                                                      │
│   ]                                                                                                                                           │
│ }                                                                                                                                             │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ Step 2：前端 — CLI 调用服务                                                                                                                   │
│                                                                                                                                               │
│ 新建 frontend/src/lib/cli.ts                                                                                                                  │
│                                                                                                                                               │
│ 封装 Claude CLI 的调用逻辑：                                                                                                                  │
│                                                                                                                                               │
│ interface ChatOptions {                                                                                                                       │
│   prompt: string                                                                                                                              │
│   systemPrompt: string     // 剧本上下文                                                                                                      │
│   sessionId?: string       // 多轮对话                                                                                                        │
│   onChunk: (text: string) => void                                                                                                             │
│   onDone: (result: { sessionId: string; costUsd?: number }) => void                                                                           │
│   onError: (err: string) => void                                                                                                              │
│ }                                                                                                                                             │
│                                                                                                                                               │
│ export async function streamClaude(options: ChatOptions): Promise<ChildProcess>                                                               │
│                                                                                                                                               │
│ 实现要点：                                                                                                                                    │
│ - 使用 @tauri-apps/plugin-shell 的 Command.create('claude', [...])                                                                            │
│ - 参数：-p, --output-format stream-json, --system-prompt, --max-turns 3                                                                       │
│ - 如有 sessionId 则加 --resume <sessionId>                                                                                                    │
│ - stdout 按行解析 NDJSON，提取 content_block_delta 中的文本 chunk                                                                             │
│ - 返回 ChildProcess 用于中断（abort）                                                                                                         │
│                                                                                                                                               │
│ Web 模式降级：                                                                                                                                │
│ - 检测 isTauri()，非 Tauri 环境显示提示「请在桌面版中使用 AI 对话功能」                                                                       │
│ - 后续可通过后端 subprocess 支持 web 模式（不在本次范围）                                                                                     │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ Step 3：前端 — Store 扩展                                                                                                                     │
│                                                                                                                                               │
│ 修改 frontend/src/lib/store.ts                                                                                                                │
│                                                                                                                                               │
│ 新增状态和 actions：                                                                                                                          │
│                                                                                                                                               │
│ // 接口                                                                                                                                       │
│ interface ChatMessage {                                                                                                                       │
│   id: string                                                                                                                                  │
│   role: 'user' | 'assistant'                                                                                                                  │
│   content: string                                                                                                                             │
│   timestamp: number                                                                                                                           │
│ }                                                                                                                                             │
│                                                                                                                                               │
│ // 状态                                                                                                                                       │
│ chatMessages: ChatMessage[]                                                                                                                   │
│ isChatStreaming: boolean                                                                                                                      │
│ chatSessionId: string | null   // Claude CLI session ID，多轮复用                                                                             │
│                                                                                                                                               │
│ // Actions                                                                                                                                    │
│ addChatMessage: (msg: Omit<ChatMessage, 'id' | 'timestamp'>) => void                                                                          │
│ updateLastAssistantMessage: (content: string) => void  // 流式追加                                                                            │
│ clearChat: () => void                                                                                                                         │
│ setIsChatStreaming: (streaming: boolean) => void                                                                                              │
│ setChatSessionId: (id: string | null) => void                                                                                                 │
│                                                                                                                                               │
│ 更新 activePanel 类型，加入 'chat'。                                                                                                          │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ Step 4：前端 — ChatPanel 组件                                                                                                                 │
│                                                                                                                                               │
│ 新建 frontend/src/components/AIPanel/ChatPanel.tsx                                                                                            │
│                                                                                                                                               │
│ 布局（从上到下）：                                                                                                                            │
│                                                                                                                                               │
│ 1. 顶栏 — 「AI 对话」标题 + 清空按钮 + 上下文状态指示（绿点 = 已附加剧本上下文）                                                              │
│ 2. 消息列表 — 滚动区域                                                                                                                        │
│   - 用户消息：靠右，蓝色背景                                                                                                                  │
│   - AI 消息：靠左，灰色背景，支持流式追加                                                                                                     │
│   - 空状态：提示「输入问题，AI 将基于你的剧本上下文回答」                                                                                     │
│ 3. 输入区 — textarea + 发送按钮                                                                                                               │
│   - Enter 发送，Shift+Enter 换行                                                                                                              │
│   - 流式中显示「停止」按钮（调用 child.kill()）                                                                                               │
│                                                                                                                                               │
│ 发送流程：                                                                                                                                    │
│ 1. 从 store 收集上下文，构造 system prompt：                                                                                                  │
│ 你是一个专业的剧本创作助手。以下是用户正在创作的剧本上下文：                                                                                  │
│ 【剧本内容】{fountainContent 前 3000 字}                                                                                                      │
│ 【角色设定】{characters JSON}                                                                                                                 │
│ 【当前场景】{scene}                                                                                                                           │
│ 【风格】{style}                                                                                                                               │
│ {如有选中文本：【用户选中的文本】selection}                                                                                                   │
│ 请基于以上上下文，帮助用户讨论和改进剧本。用中文回答。                                                                                        │
│ 2. 添加用户消息到 store                                                                                                                       │
│ 3. 调用 streamClaude()，流式更新 assistant 消息                                                                                               │
│ 4. 完成后保存 sessionId 供下次 --resume 使用                                                                                                  │
│                                                                                                                                               │
│ 非 Tauri 环境显示提示信息，引导用户使用桌面版。                                                                                               │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ Step 5：前端 — 挂载 ChatPanel                                                                                                                 │
│                                                                                                                                               │
│ 修改 frontend/src/app/page.tsx                                                                                                                │
│                                                                                                                                               │
│ 1. import ChatPanel from '@/components/AIPanel/ChatPanel'                                                                                     │
│ 2. panelTabs 添加 { key: 'chat' as const, label: '对话' }                                                                                     │
│ 3. 面板内容区添加 {activePanel === 'chat' && <ChatPanel />}                                                                                   │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ 涉及的文件清单                                                                                                                                │
│                                                                                                                                               │
│ 新建                                                                                                                                          │
│                                                                                                                                               │
│ - frontend/src/lib/cli.ts — CLI 调用封装                                                                                                      │
│ - frontend/src/components/AIPanel/ChatPanel.tsx — 对话面板 UI                                                                                 │
│                                                                                                                                               │
│ 修改                                                                                                                                          │
│                                                                                                                                               │
│ - src-tauri/capabilities/default.json — 添加 claude spawn 权限                                                                                │
│ - frontend/src/lib/store.ts — chat 状态 + activePanel 类型                                                                                    │
│ - frontend/src/app/page.tsx — 挂载 ChatPanel + 新 tab                                                                                         │
│                                                                                                                                               │
│ ---                                                                                                                                           │
│ 验证                                                                                                                                          │
│                                                                                                                                               │
│ 1. cd frontend && npx tsc --noEmit — 前端编译无误                                                                                             │
│ 2. 确认 claude CLI 已安装并登录：claude --version                                                                                             │
│ 3. cd src-tauri && cargo tauri dev — 启动桌面版                                                                                               │
│ 4. 右侧面板出现「对话」标签，点击进入                                                                                                         │
│ 5. 输入消息，能收到流式回复                                                                                                                   │
│ 6. AI 回复体现对剧本上下文的理解（提到角色名、场景等）                                                                                        │
│ 7. 发送第二条消息，验证多轮对话（--resume）正常                                                                                               │
│ 8. 点击「停止」能中断生成                                                                                                                     │
│ 9. 非 Tauri（web）环境显示降级提示，不崩溃    

  ✔ Step 1: Tauri 权限配置 — 添加 claude spawn 权限                                                     
  ✔ Step 3: 修改 store.ts — 添加 chat 状态和 actions                                                                                             
  ◻ Step 6: TypeScript 编译验证                                                                                                                  
  ✔ Step 4: 新建 ChatPanel.tsx — 对话面板 UI 组件                                                                                                
  ✔ Step 2: 新建 frontend/src/lib/cli.ts — CLI 调用服务                                                                                          
  ✔ Step 5: 修改 page.tsx — 挂载 ChatPanel 和新 tab   