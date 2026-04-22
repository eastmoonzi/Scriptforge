'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import { useStore } from '@/lib/store'
import { useAutoSave, restoreFromLocal } from '@/lib/autosave'
import { useKeyboardShortcuts } from '@/lib/shortcuts'
import { isTauri, waitForBackend } from '@/lib/api'
import MenuBar from '@/components/MenuBar'
import StatusBar from '@/components/StatusBar'
import HelpModal from '@/components/HelpModal'
import CharacterManager from '@/components/AIPanel/CharacterManager'
import SceneSettings from '@/components/AIPanel/SceneSettings'
import GenerationControls from '@/components/AIPanel/GenerationControls'
import LLMConfig from '@/components/AIPanel/LLMConfig'
import OutlineNavigator from '@/components/AIPanel/OutlineNavigator'
import ChatPanel from '@/components/AIPanel/ChatPanel'
import EvaluationPanel from '@/components/AIPanel/EvaluationPanel'

// TipTap must be client-only (no SSR)
const FountainEditor = dynamic(() => import('@/components/Editor/FountainEditor'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full text-zinc-400 text-sm">
      加载编辑器...
    </div>
  ),
})

const panelTabs = [
  { key: 'characters' as const, label: '角色' },
  { key: 'scene' as const, label: '场景' },
  { key: 'generation' as const, label: 'AI' },
  { key: 'outline' as const, label: '大纲' },
  { key: 'chat' as const, label: '对话' },
  { key: 'evaluation' as const, label: '评测' },
]

export default function Home() {
  const { isDarkMode, activePanel, setActivePanel } = useStore()
  const [backendReady, setBackendReady] = useState(!isTauri())

  // Restore saved state on mount
  useEffect(() => { restoreFromLocal() }, [])

  // Wait for sidecar backend in Tauri environment
  useEffect(() => {
    if (isTauri()) {
      waitForBackend(30, 1000).then((ok) => {
        setBackendReady(ok)
        if (!ok) {
          useStore.getState().setStatusMessage('后端启动失败，部分功能不可用')
        }
      })
    }
  }, [])

  // Auto-save every 5s when dirty
  useAutoSave()

  // Global keyboard shortcuts
  useKeyboardShortcuts()

  return (
    <div className={`${isDarkMode ? 'dark' : ''} h-full flex flex-col`}>
      {!backendReady ? (
        <div className="flex-1 flex items-center justify-center bg-zinc-50 dark:bg-zinc-900">
          <div className="text-center space-y-4">
            <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto" />
            <p className="text-sm text-zinc-500 dark:text-zinc-400">正在启动后端服务...</p>
          </div>
        </div>
      ) : (
        <>
          <MenuBar />

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Left: Fountain Editor */}
        <div className="flex-1 min-w-0">
          <FountainEditor />
        </div>

        {/* Right: AI Panel */}
        <div className="w-80 border-l border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 flex flex-col shrink-0">
          {/* LLM Config — persistent across tabs */}
          <LLMConfig />

          {/* Panel tabs */}
          <div className="flex border-b border-zinc-200 dark:border-zinc-700 shrink-0">
            {panelTabs.map((tab) => (
              <button
                key={tab.key}
                className={`flex-1 text-xs py-2 transition-colors ${
                  activePanel === tab.key
                    ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-500 font-medium'
                    : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'
                }`}
                onClick={() => setActivePanel(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Panel content */}
          <div className="flex-1 overflow-y-auto p-4">
            {activePanel === 'characters' && <CharacterManager />}
            {activePanel === 'scene' && <SceneSettings />}
            {activePanel === 'generation' && <GenerationControls />}
            {activePanel === 'outline' && <OutlineNavigator />}
            {activePanel === 'chat' && <ChatPanel />}
            {activePanel === 'evaluation' && <EvaluationPanel />}
          </div>
        </div>
      </div>

      <StatusBar />
        </>
      )}
      <HelpModal />
    </div>
  )
}
