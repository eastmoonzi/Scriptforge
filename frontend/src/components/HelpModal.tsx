'use client'

import { useStore } from '@/lib/store'
import { X } from 'lucide-react'

export default function HelpModal() {
  const { showHelp, setShowHelp } = useStore()

  if (!showHelp) return null

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
      onClick={() => setShowHelp(false)}
    >
      <div
        className="bg-white dark:bg-zinc-800 rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-5 py-3 border-b border-zinc-200 dark:border-zinc-700 flex justify-between items-center">
          <h2 className="text-sm font-semibold">Fountain 格式速查 & 快捷键</h2>
          <button
            className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
            onClick={() => setShowHelp(false)}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(80vh-48px)] p-5 space-y-6">
          {/* Fountain format reference */}
          <section>
            <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">
              Fountain 格式
            </h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left border-b border-zinc-200 dark:border-zinc-700">
                  <th className="pb-1.5 pr-4 font-medium text-zinc-500 dark:text-zinc-400 w-28">元素</th>
                  <th className="pb-1.5 font-medium text-zinc-500 dark:text-zinc-400">输入方式</th>
                </tr>
              </thead>
              <tbody className="text-zinc-700 dark:text-zinc-300">
                {fountainRows.map((row) => (
                  <tr key={row.element} className="border-b border-zinc-100 dark:border-zinc-700/50">
                    <td className="py-1.5 pr-4 font-medium">{row.element}</td>
                    <td className="py-1.5">
                      <code className="text-xs bg-zinc-100 dark:bg-zinc-700 px-1 py-0.5 rounded">
                        {row.syntax}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {/* Keyboard shortcuts */}
          <section>
            <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-2">
              快捷键
            </h3>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left border-b border-zinc-200 dark:border-zinc-700">
                  <th className="pb-1.5 pr-4 font-medium text-zinc-500 dark:text-zinc-400 w-40">快捷键</th>
                  <th className="pb-1.5 font-medium text-zinc-500 dark:text-zinc-400">功能</th>
                </tr>
              </thead>
              <tbody className="text-zinc-700 dark:text-zinc-300">
                {shortcutRows.map((row) => (
                  <tr key={row.keys} className="border-b border-zinc-100 dark:border-zinc-700/50">
                    <td className="py-1.5 pr-4">
                      <kbd className="text-xs bg-zinc-100 dark:bg-zinc-700 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-600 font-mono">
                        {row.keys}
                      </kbd>
                    </td>
                    <td className="py-1.5">{row.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      </div>
    </div>
  )
}

const fountainRows = [
  { element: '场景标题', syntax: 'INT. / EXT. / INT./EXT. + 空格' },
  { element: '强制场景标题', syntax: '. 前缀（如 .闪回）' },
  { element: '角色名', syntax: '全大写英文 / 中文名（前一行留空）' },
  { element: '强制角色名', syntax: '@ 前缀（如 @旁白）' },
  { element: '对白', syntax: '紧跟角色名的下一行' },
  { element: '括号注释', syntax: '（文字） 或 (文字)' },
  { element: '动作描述', syntax: '普通文本，或 ! 前缀强制' },
  { element: '转场', syntax: '全大写 + TO: 结尾' },
  { element: '居中', syntax: '>文字<' },
  { element: '章节标题', syntax: '# / ## / ###' },
  { element: '分页符', syntax: '===' },
]

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.userAgent)
const mod = isMac ? '\u2318' : 'Ctrl'

const shortcutRows = [
  { keys: 'Tab', description: '循环切换元素类型' },
  { keys: `${mod}+S`, description: '保存' },
  { keys: `${mod}+E`, description: '导出 .fountain' },
  { keys: `${mod}+Shift+E`, description: '导出 PDF' },
  { keys: `${mod}+D`, description: '切换主题' },
  { keys: `${mod}+Enter`, description: '切换到 AI 面板' },
  { keys: `${mod}+1/2/3/4`, description: '切换面板标签' },
  { keys: `F1 / ${mod}+/`, description: '打开本帮助' },
]
