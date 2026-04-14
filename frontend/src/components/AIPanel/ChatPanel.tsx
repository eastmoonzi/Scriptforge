'use client'

import { useRef, useEffect, useState, useCallback } from 'react'
import { useStore } from '@/lib/store'
import { isTauri } from '@/lib/api'
import { streamClaude } from '@/lib/cli'

type ChildProcess = { kill: () => Promise<void> }

/** 从 store 收集剧本上下文，构造 system prompt */
function buildSystemPrompt(): string {
  const { fountainContent, characters, scene, style } = useStore.getState()

  const parts: string[] = [
    '你是一个专业的剧本创作助手。以下是用户正在创作的剧本上下文：',
  ]

  if (fountainContent) {
    parts.push(`【剧本内容】\n${fountainContent.slice(0, 3000)}`)
  }

  if (characters.length > 0) {
    const charJson = JSON.stringify(
      characters.map((c) => ({ name: c.name, personality: c.personality })),
      null,
      2,
    )
    parts.push(`【角色设定】\n${charJson}`)
  }

  if (scene) {
    parts.push(`【当前场景】\n${scene}`)
  }

  if (style && style !== 'default') {
    const styleNames: Record<string, string> = {
      suspense: '悬疑',
      comedy: '喜剧',
      realism: '现实主义',
    }
    parts.push(`【风格】${styleNames[style] ?? style}`)
  }

  // 如果编辑器有选中文本，也附加
  const editor = useStore.getState().editorInstance
  if (editor) {
    const { from, to } = editor.state.selection
    if (from !== to) {
      const selected = editor.state.doc.textBetween(from, to)
      if (selected.trim()) {
        parts.push(`【用户选中的文本】\n${selected}`)
      }
    }
  }

  parts.push('请基于以上上下文，帮助用户讨论和改进剧本。用中文回答。')

  return parts.join('\n\n')
}

export default function ChatPanel() {
  const {
    chatMessages,
    isChatStreaming,
    chatSessionId,
    addChatMessage,
    updateLastAssistantMessage,
    clearChat,
    setIsChatStreaming,
    setChatSessionId,
    setStatusMessage,
    fountainContent,
    characters,
  } = useStore()

  const [input, setInput] = useState('')
  const childRef = useRef<ChildProcess | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // 判断是否有剧本上下文
  const hasContext = fountainContent.trim().length > 0 || characters.length > 0

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isChatStreaming) return

    setInput('')
    addChatMessage({ role: 'user', content: text })

    // 添加空的 assistant 消息用于流式追加
    addChatMessage({ role: 'assistant', content: '' })
    setIsChatStreaming(true)
    setStatusMessage('AI 对话中...')

    let accumulated = ''

    try {
      const child = await streamClaude({
        prompt: text,
        systemPrompt: buildSystemPrompt(),
        sessionId: chatSessionId ?? undefined,
        onChunk: (chunk) => {
          accumulated += chunk
          updateLastAssistantMessage(accumulated)
        },
        onDone: (result) => {
          if (result.sessionId) {
            setChatSessionId(result.sessionId)
          }
          setIsChatStreaming(false)
          const costInfo = result.costUsd ? ` ($${result.costUsd.toFixed(4)})` : ''
          setStatusMessage(`对话完成${costInfo}`)
        },
        onError: (err) => {
          setIsChatStreaming(false)
          // 如果 assistant 消息为空，更新为错误提示
          if (!accumulated) {
            updateLastAssistantMessage(`发生错误：${err}`)
          }
          setStatusMessage(`对话出错: ${err}`)
        },
      })
      childRef.current = child
    } catch (err) {
      setIsChatStreaming(false)
      const msg = err instanceof Error ? err.message : '未知错误'
      updateLastAssistantMessage(`发生错误：${msg}`)
      setStatusMessage(`对话出错: ${msg}`)
    }
  }, [
    input, isChatStreaming, chatSessionId,
    addChatMessage, updateLastAssistantMessage,
    setIsChatStreaming, setChatSessionId, setStatusMessage,
  ])

  const handleStop = useCallback(async () => {
    await childRef.current?.kill()
    childRef.current = null
    setIsChatStreaming(false)
    setStatusMessage('已停止生成')
  }, [setIsChatStreaming, setStatusMessage])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // 非 Tauri 环境降级提示
  if (!isTauri()) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-4 space-y-3">
        <div className="text-3xl">💬</div>
        <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          AI 对话功能仅在桌面版中可用
        </p>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          请使用 Scriptforge 桌面应用，通过 Claude Code CLI 进行剧本讨论。需要先安装并登录 Claude Code。
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full -m-4">
      {/* 顶栏 */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-200 dark:border-zinc-700 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-zinc-600 dark:text-zinc-300">
            AI 对话
          </span>
          <span
            className={`w-2 h-2 rounded-full ${hasContext ? 'bg-green-500' : 'bg-zinc-300 dark:bg-zinc-600'}`}
            title={hasContext ? '已附加剧本上下文' : '无剧本上下文'}
          />
        </div>
        <button
          className="text-xs text-zinc-400 hover:text-red-500 transition-colors"
          onClick={clearChat}
          disabled={isChatStreaming}
          title="清空对话"
        >
          清空
        </button>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3 min-h-0">
        {chatMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-2 opacity-60">
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              输入问题，AI 将基于你的剧本上下文回答
            </p>
            <p className="text-xs text-zinc-400 dark:text-zinc-500">
              需要已安装并登录 Claude Code CLI
            </p>
          </div>
        ) : (
          chatMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words ${
                  msg.role === 'user'
                    ? 'bg-blue-500 text-white'
                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-800 dark:text-zinc-200'
                }`}
              >
                {msg.content || (
                  <span className="inline-flex items-center gap-1 text-zinc-400">
                    <span className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse" />
                    思考中...
                  </span>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区 */}
      <div className="border-t border-zinc-200 dark:border-zinc-700 px-3 py-2 shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            className="flex-1 text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-2 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none resize-none"
            rows={2}
            placeholder="输入问题... (Enter 发送, Shift+Enter 换行)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isChatStreaming}
          />
          {isChatStreaming ? (
            <button
              className="shrink-0 text-sm bg-red-500 hover:bg-red-600 text-white rounded-md px-3 py-2 transition-colors"
              onClick={handleStop}
            >
              停止
            </button>
          ) : (
            <button
              className="shrink-0 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-md px-3 py-2 transition-colors disabled:opacity-50"
              disabled={!input.trim()}
              onClick={handleSend}
            >
              发送
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
