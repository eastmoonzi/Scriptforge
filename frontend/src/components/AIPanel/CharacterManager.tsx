'use client'

import { useState } from 'react'
import { useStore } from '@/lib/store'

export default function CharacterManager() {
  const characters = useStore((s) => s.characters)
  const addCharacter = useStore((s) => s.addCharacter)
  const removeCharacter = useStore((s) => s.removeCharacter)
  const updateCharacter = useStore((s) => s.updateCharacter)
  const [newName, setNewName] = useState('')
  const [newPersonality, setNewPersonality] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)

  const handleAdd = () => {
    if (!newName.trim()) return
    addCharacter({ name: newName.trim(), personality: newPersonality.trim() })
    setNewName('')
    setNewPersonality('')
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
        角色管理
      </h3>

      {/* Character list */}
      <div className="space-y-2">
        {characters.map((char) => (
          <div
            key={char.id}
            className="group rounded-lg border border-zinc-200 dark:border-zinc-700 p-3 hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
          >
            {editingId === char.id ? (
              <div className="space-y-2">
                <input
                  className="w-full text-sm bg-transparent border-b border-zinc-300 dark:border-zinc-600 focus:border-blue-500 outline-none pb-1"
                  value={char.name}
                  onChange={(e) => updateCharacter(char.id, { name: e.target.value })}
                />
                <textarea
                  className="w-full text-xs bg-transparent border border-zinc-300 dark:border-zinc-600 rounded p-1.5 focus:border-blue-500 outline-none resize-none"
                  rows={2}
                  value={char.personality}
                  onChange={(e) => updateCharacter(char.id, { personality: e.target.value })}
                />
                <button
                  className="text-xs text-blue-500 hover:text-blue-600"
                  onClick={() => setEditingId(null)}
                >
                  完成
                </button>
              </div>
            ) : (
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-sm truncate">{char.name}</div>
                  <div className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 line-clamp-2">
                    {char.personality || '未设置人设'}
                  </div>
                </div>
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0">
                  <button
                    className="text-xs text-zinc-400 hover:text-blue-500 p-1"
                    onClick={() => setEditingId(char.id)}
                    title="编辑"
                  >
                    ✎
                  </button>
                  <button
                    className="text-xs text-zinc-400 hover:text-red-500 p-1"
                    onClick={() => removeCharacter(char.id)}
                    title="删除"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add new character */}
      <div className="space-y-2 pt-2 border-t border-zinc-200 dark:border-zinc-700">
        <input
          className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-1.5 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          placeholder="角色名"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
        />
        <input
          className="w-full text-sm bg-zinc-50 dark:bg-zinc-800 rounded-md px-3 py-1.5 border border-zinc-200 dark:border-zinc-700 focus:border-blue-500 outline-none"
          placeholder="性格/人设描述"
          value={newPersonality}
          onChange={(e) => setNewPersonality(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
        />
        <button
          className="w-full text-sm bg-blue-500 hover:bg-blue-600 text-white rounded-md py-1.5 transition-colors disabled:opacity-50"
          disabled={!newName.trim()}
          onClick={handleAdd}
        >
          + 添加角色
        </button>
      </div>
    </div>
  )
}
