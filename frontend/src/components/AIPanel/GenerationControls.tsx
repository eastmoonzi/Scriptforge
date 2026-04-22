'use client'

import { useRef } from 'react'
import { useStore } from '@/lib/store'
import { notify } from '@/lib/notify'
import { generateNext, generateScene, polishText, streamGenerate, generateDirector } from '@/lib/api'
import SuggestionSlot from './SuggestionSlot'
import { Play, Pencil, ChevronDown, BookOpen } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Button } from '@/components/ui/Button'

export default function GenerationControls() {
  const {
    scene, characters, style, apiKey, model, provider, customBaseUrl, isGenerating, useDirectorMode,
    setIsGenerating, setStatusMessage, setFountainContent, fountainContent,
    editorInstance, toggleDirectorMode, getOrCreateRagSessionId,
    setPendingSuggestion, appendSuggestionChunk, clearPendingSuggestion,
  } = useStore()
  const abortRef = useRef<(() => void) | null>(null)

  const charParams = characters.map((c) => ({ name: c.name, personality: c.personality }))

  const handleGenerateNext = async () => {
    if (!apiKey) {
      notify('请先设置 API Key', 'warning')
      return
    }
    clearPendingSuggestion()
    setIsGenerating(true)
    setStatusMessage('正在生成...')

    const baseUrl = provider === 'custom' && customBaseUrl ? { base_url: customBaseUrl } : {}

    // 导演模式走独立接口
    if (useDirectorMode) {
      setPendingSuggestion({ mode: 'director', streaming: true, currentSpeaker: '', dialogues: [] })
      try {
        setStatusMessage('导演模式生成中...')
        const result = await generateDirector({
          scene,
          characters: charParams,
          context: fountainContent.slice(-2000),
          model,
          provider,
          session_id: getOrCreateRagSessionId(),
          ...baseUrl,
        })
        const feedback = (result.review as Record<string, unknown>)?.feedback as string ?? ''
        setPendingSuggestion({
          mode: 'director',
          streaming: false,
          currentSpeaker: '',
          dialogues: result.dialogues,
          plotGoal: result.plot_goal,
          reviewFeedback: feedback || undefined,
        })
        notify(`导演模式完成｜目标：${result.plot_goal}`, 'success')
      } catch (err) {
        const msg = err instanceof Error ? err.message : '未知错误'
        setPendingSuggestion({ mode: 'director', streaming: false, currentSpeaker: '', dialogues: [], error: msg })
        notify(`导演模式失败: ${msg}`, 'error')
      } finally {
        setIsGenerating(false)
      }
      return
    }

    const sessionId = getOrCreateRagSessionId()
    const params = {
      scene,
      characters: charParams,
      style,
      context: fountainContent.slice(-2000),
      model,
      provider,
      session_id: sessionId,
      commit_memory: false,
      ...baseUrl,
    }

    setPendingSuggestion({ mode: 'next', streaming: true, currentSpeaker: '', dialogues: [] })

    // Try SSE streaming first, fall back to standard request
    const abort = streamGenerate(
      params,
      (chunk) => {
        try {
          const data = JSON.parse(chunk)
          if (data.error) {
            setPendingSuggestion({ mode: 'next', streaming: false, currentSpeaker: '', dialogues: [], error: data.error })
            notify(`生成失败: ${data.error}`, 'error')
            setIsGenerating(false)
            return
          }
          if (data.content === '[DONE]') return
          appendSuggestionChunk(data.speaker, data.content)
        } catch {
          // 非 JSON chunk 忽略
        }
      },
      () => {
        useStore.setState((s) => ({
          pendingSuggestion: s.pendingSuggestion ? { ...s.pendingSuggestion, streaming: false } : null,
        }))
        notify('生成完成，请预览后插入', 'success')
        setIsGenerating(false)
      },
      async () => {
        // SSE 失败 — 降级到普通请求
        try {
          const result = await generateNext(params)
          setPendingSuggestion({ mode: 'next', streaming: false, currentSpeaker: '', dialogues: result.dialogues })
          notify('生成完成，请预览后插入', 'success')
        } catch (err) {
          const msg = err instanceof Error ? err.message : '未知错误'
          setPendingSuggestion({ mode: 'next', streaming: false, currentSpeaker: '', dialogues: [], error: msg })
          notify(`生成失败: ${msg}`, 'error')
        } finally {
          setIsGenerating(false)
        }
      },
    )
    abortRef.current = abort
  }

  const handleGenerateScene = async () => {
    if (!apiKey) {
      notify('请先设置 API Key', 'warning')
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
        model,
        provider,
        ...(provider === 'custom' && customBaseUrl ? { base_url: customBaseUrl } : {}),
      })
      setFountainContent(fountainContent + '\n\n' + result.content)
      notify('续写完成', 'success')
    } catch (err) {
      notify(`续写失败: ${err instanceof Error ? err.message : '未知错误'}`, 'error')
    } finally {
      setIsGenerating(false)
    }
  }

  const handlePolish = async () => {
    if (!apiKey) {
      notify('请先设置 API Key', 'warning')
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
        model,
        provider,
        ...(provider === 'custom' && customBaseUrl ? { base_url: customBaseUrl } : {}),
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
      notify('润色完成', 'success')
    } catch (err) {
      notify(`润色失败: ${err instanceof Error ? err.message : '未知错误'}`, 'error')
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="space-y-3">
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

      <div className="pt-2">
        <div className="flex gap-0">
          <Button
            variant="accent"
            className="flex-1 rounded-r-none"
            disabled={isGenerating}
            onClick={handleGenerateNext}
          >
            <Play className="w-4 h-4" />
            生成下一段
          </Button>
          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <Button
                variant="accent"
                className="rounded-l-none border-l border-emerald-700 px-1.5"
                disabled={isGenerating}
              >
                <ChevronDown className="w-3.5 h-3.5" />
              </Button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content
                className="bg-white dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-md shadow-lg py-1 min-w-[160px] z-50"
                sideOffset={2}
                align="end"
              >
                <DropdownMenu.Item
                  className="text-xs px-3 py-2 outline-none cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700 data-[highlighted]:bg-zinc-100 dark:data-[highlighted]:bg-zinc-700 flex items-center gap-2"
                  onSelect={() => handleGenerateScene()}
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  续写整场戏
                </DropdownMenu.Item>
                <DropdownMenu.Item
                  className="text-xs px-3 py-2 outline-none cursor-pointer hover:bg-zinc-100 dark:hover:bg-zinc-700 data-[highlighted]:bg-zinc-100 dark:data-[highlighted]:bg-zinc-700 flex items-center gap-2"
                  onSelect={() => handlePolish()}
                >
                  <Pencil className="w-3.5 h-3.5" />
                  {editorInstance?.state.selection.from !== editorInstance?.state.selection.to ? '润色选中文本' : '润色最后段落'}
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>

      {isGenerating && (
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <span className="inline-block w-3 h-3 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          生成中...
          <button
            className="text-red-400 hover:text-red-500 ml-auto"
            onClick={() => {
              abortRef.current?.()
              setIsGenerating(false)
              clearPendingSuggestion()
              notify('已取消', 'info')
            }}
          >
            取消
          </button>
        </div>
      )}

      <SuggestionSlot />
    </div>
  )
}
