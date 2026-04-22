'use client'

import { useStore } from '@/lib/store'
import { commitMemory } from '@/lib/api'

export default function SuggestionSlot() {
  const {
    pendingSuggestion,
    clearPendingSuggestion,
    fountainContent,
    setFountainContent,
    ragSessionId,
    apiKey,
    provider,
    characters,
  } = useStore()

  if (!pendingSuggestion) return null

  const { streaming, currentSpeaker, dialogues, plotGoal, reviewFeedback, error } = pendingSuggestion

  const handleInsert = async () => {
    if (!dialogues.length) return

    // 提交到 RAG 记忆（仅 Gemini）
    if (provider === 'gemini' && ragSessionId && apiKey) {
      try {
        await commitMemory({
          session_id: ragSessionId,
          characters: characters.map((c) => ({ name: c.name, personality: c.personality })),
          dialogues,
        })
      } catch {
        // 记忆写入失败不阻塞插入
      }
    }

    const fountain = dialogues.map((d) => `\n${d.speaker}\n${d.content}`).join('\n')
    setFountainContent(fountainContent + '\n' + fountain)
    clearPendingSuggestion()
  }

  return (
    <div className="mt-2 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-800/60 text-xs overflow-hidden">
      {/* 标题栏 */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-zinc-100 dark:bg-zinc-800 border-b border-zinc-200 dark:border-zinc-700">
        <span className="font-medium text-zinc-600 dark:text-zinc-300">
          {pendingSuggestion.mode === 'director' ? '导演模式预览' : '生成预览'}
        </span>
        {streaming && (
          <span className="flex items-center gap-1 text-blue-500">
            <span className="inline-block w-2 h-2 border border-blue-500 border-t-transparent rounded-full animate-spin" />
            {currentSpeaker || '生成中...'}
          </span>
        )}
      </div>

      {/* 剧情目标（导演模式） */}
      {plotGoal && (
        <div className="px-3 py-1.5 text-zinc-500 dark:text-zinc-400 italic border-b border-zinc-200 dark:border-zinc-700">
          目标：{plotGoal}
        </div>
      )}

      {/* 错误状态 */}
      {error && (
        <div className="px-3 py-2 text-red-500">{error}</div>
      )}

      {/* 对话预览 */}
      {!error && dialogues.length > 0 && (
        <div className="px-3 py-2 space-y-1 max-h-48 overflow-y-auto">
          {dialogues.map((d, i) => (
            <div key={i}>
              <span className="font-semibold text-zinc-700 dark:text-zinc-200 uppercase tracking-wide">{d.speaker}</span>
              <p className="text-zinc-600 dark:text-zinc-400 mt-0.5">{d.content}</p>
            </div>
          ))}
          {streaming && currentSpeaker && (
            <div>
              <span className="font-semibold text-blue-500 uppercase tracking-wide">{currentSpeaker}</span>
              <p className="text-zinc-400 italic mt-0.5">正在生成...</p>
            </div>
          )}
        </div>
      )}

      {/* 审稿反馈（导演模式） */}
      {reviewFeedback && (
        <div className="px-3 py-1.5 text-zinc-500 dark:text-zinc-400 italic border-t border-zinc-200 dark:border-zinc-700">
          审稿：{reviewFeedback}
        </div>
      )}

      {/* 操作按钮 */}
      {!streaming && (
        <div className="flex gap-2 px-3 py-2 border-t border-zinc-200 dark:border-zinc-700">
          <button
            onClick={handleInsert}
            disabled={!!error || !dialogues.length}
            className="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded py-1 transition-colors disabled:opacity-40"
          >
            插入到剧本
          </button>
          <button
            onClick={clearPendingSuggestion}
            className="flex-1 bg-zinc-200 dark:bg-zinc-700 hover:bg-zinc-300 dark:hover:bg-zinc-600 text-zinc-700 dark:text-zinc-200 rounded py-1 transition-colors"
          >
            丢弃
          </button>
        </div>
      )}
    </div>
  )
}
