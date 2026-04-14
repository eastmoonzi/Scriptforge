'use client'

import { useStore } from '@/lib/store'

export default function StatusBar() {
  const { sceneCount, pageCount, isSaved, model, statusMessage, isGenerating } = useStore()

  return (
    <div className="h-7 flex items-center justify-between px-4 border-t border-zinc-200 dark:border-zinc-700 bg-zinc-50 dark:bg-zinc-900 text-xs text-zinc-500 dark:text-zinc-400 select-none shrink-0">
      <div className="flex items-center gap-4">
        <span>第 {sceneCount} 场</span>
        <span>{pageCount} 页</span>
        <span>{isSaved ? '已保存' : '未保存'}</span>
      </div>
      <div className="flex items-center gap-4">
        {isGenerating && (
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            生成中
          </span>
        )}
        <span>{statusMessage}</span>
        <span>{model}</span>
      </div>
    </div>
  )
}
