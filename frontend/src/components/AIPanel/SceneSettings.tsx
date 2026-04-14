'use client'

import { useStore } from '@/lib/store'

export default function SceneSettings() {
  const scene = useStore((s) => s.scene)
  const setScene = useStore((s) => s.setScene)
  const style = useStore((s) => s.style)
  const setStyle = useStore((s) => s.setStyle)

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
        场景设定
      </h3>

      <textarea
        className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-2 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none resize-none"
        rows={4}
        placeholder="描述你的场景背景..."
        value={scene}
        onChange={(e) => setScene(e.target.value)}
      />

      <div>
        <label className="block text-xs text-zinc-500 dark:text-zinc-400 mb-1">风格模板</label>
        <select
          className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-1.5 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          value={style}
          onChange={(e) => setStyle(e.target.value as typeof style)}
        >
          <option value="default">默认</option>
          <option value="suspense">悬疑</option>
          <option value="comedy">喜剧</option>
          <option value="realism">现实主义</option>
        </select>
      </div>
    </div>
  )
}
