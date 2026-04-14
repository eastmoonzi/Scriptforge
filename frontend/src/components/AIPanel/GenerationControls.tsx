'use client'

import { useRef } from 'react'
import { useStore } from '@/lib/store'
import { generateNext, generateScene, polishText, streamGenerate } from '@/lib/api'

export default function GenerationControls() {
  const {
    scene, characters, style, apiKey, model, provider, isGenerating, useDirectorMode,
    setIsGenerating, setStatusMessage, setFountainContent, fountainContent,
    editorInstance, toggleDirectorMode,
  } = useStore()
  const abortRef = useRef<(() => void) | null>(null)

  const charParams = characters.map((c) => ({ name: c.name, personality: c.personality }))

  const handleGenerateNext = async () => {
    if (!apiKey) {
      setStatusMessage('请先设置 API Key')
      return
    }
    setIsGenerating(true)
    setStatusMessage('正在生成...')

    const params = {
      scene,
      characters: charParams,
      style,
      context: fountainContent.slice(-2000),
      api_key: apiKey,
      model,
      provider,
    }

    // Try SSE streaming first, fall back to standard request
    let streamingText = ''
    let currentSpeaker = ''
    const abort = streamGenerate(
      params,
      (chunk) => {
        try {
          const data = JSON.parse(chunk)
          if (data.content === '[DONE]') {
            // Speaker finished
            return
          }
          if (data.speaker !== currentSpeaker) {
            currentSpeaker = data.speaker
            streamingText += `\n${data.speaker}\n`
          }
          streamingText += data.content
          setFountainContent(fountainContent + '\n' + streamingText)
        } catch {
          // Non-JSON chunk, append as-is
          streamingText += chunk
        }
      },
      () => {
        setStatusMessage('生成完成')
        setIsGenerating(false)
      },
      async () => {
        // SSE failed — fall back to standard request
        try {
          const result = await generateNext(params)
          const fountain = result.dialogues
            .map((d) => `\n${d.speaker}\n${d.content}`)
            .join('\n')
          setFountainContent(fountainContent + '\n' + fountain)
          setStatusMessage('生成完成')
        } catch (err) {
          setStatusMessage(`生成失败: ${err instanceof Error ? err.message : '未知错误'}`)
        } finally {
          setIsGenerating(false)
        }
      },
    )
    abortRef.current = abort
  }

  const handleGenerateScene = async () => {
    if (!apiKey) {
      setStatusMessage('请先设置 API Key')
      return
    }
    setIsGenerating(true)
    setStatusMessage('正在续写整场戏...')
    try {
      const result = await generateScene({
        scene,
        characters: charParams,
        style,
        plot_goal: '',
        api_key: apiKey,
        model,
        provider,
      })
      setFountainContent(fountainContent + '\n\n' + result.content)
      setStatusMessage('续写完成')
    } catch (err) {
      setStatusMessage(`续写失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handlePolish = async () => {
    if (!apiKey) {
      setStatusMessage('请先设置 API Key')
      return
    }

    // If editor has a selection, polish just that; otherwise last 500 chars
    let textToPolish: string
    let replaceStart: number
    let hasSelection = false

    if (editorInstance) {
      const { from, to } = editorInstance.state.selection
      if (from !== to) {
        textToPolish = editorInstance.state.doc.textBetween(from, to)
        replaceStart = from
        hasSelection = true
      } else {
        textToPolish = fountainContent.slice(-500)
        replaceStart = -1
      }
    } else {
      textToPolish = fountainContent.slice(-500)
      replaceStart = -1
    }

    if (!textToPolish.trim()) return

    setIsGenerating(true)
    setStatusMessage('正在润色...')
    try {
      const result = await polishText({
        text: textToPolish,
        style,
        instruction: '润色这段剧本对白，使其更生动自然',
        api_key: apiKey,
        model,
        provider,
      })

      if (hasSelection && editorInstance) {
        // Replace selected text in editor
        const { from, to } = editorInstance.state.selection
        editorInstance.chain().focus().deleteRange({ from: replaceStart, to }).insertContentAt(replaceStart, result.content).run()
      } else {
        // Replace last 500 chars
        const polished = fountainContent.slice(0, -500) + result.content
        setFountainContent(polished)
      }
      setStatusMessage('润色完成')
    } catch (err) {
      setStatusMessage(`润色失败: ${err instanceof Error ? err.message : '未知错误'}`)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
        AI 生成控制
      </h3>

      <div className="space-y-2">
        <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">Provider</label>
        <select
          className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-1.5 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          value={provider}
          onChange={(e) => useStore.getState().setProvider(e.target.value as 'gemini' | 'deepseek')}
        >
          <option value="gemini">Google Gemini</option>
          <option value="deepseek">DeepSeek</option>
        </select>
      </div>

      <div className="space-y-2">
        <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">API Key</label>
        <input
          type="password"
          className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-1.5 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          placeholder={provider === 'deepseek' ? 'DeepSeek API Key' : 'Gemini API Key'}
          value={apiKey}
          onChange={(e) => useStore.getState().setApiKey(e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">模型</label>
        <select
          className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-1.5 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          value={model}
          onChange={(e) => useStore.getState().setModel(e.target.value)}
        >
          {provider === 'deepseek' ? (
            <>
              <option value="deepseek-chat">DeepSeek V3 (deepseek-chat)</option>
              <option value="deepseek-reasoner">DeepSeek R1 (deepseek-reasoner)</option>
            </>
          ) : (
            <>
              <option value="gemini-2.0-flash-exp">Gemini 2.0 Flash (实验)</option>
              <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro</option>
              <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
            </>
          )}
        </select>
      </div>

      {/* Director mode toggle */}
      <label className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400 cursor-pointer">
        <input
          type="checkbox"
          className="accent-blue-500"
          checked={useDirectorMode}
          onChange={toggleDirectorMode}
        />
        导演模式（编剧→导演→角色→审稿）
      </label>

      <div className="space-y-2 pt-2">
        <button
          className="w-full flex items-center justify-center gap-2 text-sm bg-emerald-500 hover:bg-emerald-600 text-white rounded-md py-2 transition-colors disabled:opacity-50"
          disabled={isGenerating}
          onClick={handleGenerateNext}
        >
          <span>▶</span> 生成下一段
        </button>
        <button
          className="w-full flex items-center justify-center gap-2 text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-md py-2 transition-colors disabled:opacity-50"
          disabled={isGenerating}
          onClick={handleGenerateScene}
        >
          <span>▶</span> 续写整场戏
        </button>
        <button
          className="w-full flex items-center justify-center gap-2 text-sm bg-violet-500 hover:bg-violet-600 text-white rounded-md py-2 transition-colors disabled:opacity-50"
          disabled={isGenerating}
          onClick={handlePolish}
        >
          <span>✎</span> 润色{editorInstance?.state.selection.from !== editorInstance?.state.selection.to ? '选中文本' : '最后段落'}
        </button>
      </div>

      {isGenerating && (
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          生成中...
          <button
            className="text-red-400 hover:text-red-500 ml-auto"
            onClick={() => { abortRef.current?.(); setIsGenerating(false); setStatusMessage('已取消') }}
          >
            取消
          </button>
        </div>
      )}
    </div>
  )
}
