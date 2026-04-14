'use client'

import { useStore } from '@/lib/store'

export default function OutlineNavigator() {
  const outlineItems = useStore((s) => s.outlineItems)
  const editorInstance = useStore((s) => s.editorInstance)

  const scrollToItem = (index: number) => {
    if (!editorInstance) return

    // Find the matching node in the editor document
    let nodeIndex = 0
    let targetPos = 0
    editorInstance.state.doc.descendants((node, pos) => {
      if (node.type.name === 'sceneHeading' || node.type.name === 'heading') {
        if (nodeIndex === index) {
          targetPos = pos
          return false // stop iteration
        }
        nodeIndex++
      }
    })

    if (targetPos > 0) {
      editorInstance.chain().focus().setTextSelection(targetPos + 1).run()
      // Scroll the editor view to the position
      const domNode = editorInstance.view.domAtPos(targetPos + 1)
      if (domNode?.node instanceof HTMLElement) {
        domNode.node.scrollIntoView({ behavior: 'smooth', block: 'center' })
      } else if (domNode?.node?.parentElement) {
        domNode.node.parentElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
        大纲 / 场景导航
      </h3>

      {outlineItems.length === 0 ? (
        <p className="text-xs text-zinc-400 dark:text-zinc-500 italic">
          在编辑器中使用 INT./EXT. 添加场景，或用 # 添加章节标题
        </p>
      ) : (
        <div className="space-y-0.5">
          {outlineItems.map((item, idx) => (
            <button
              key={item.id}
              className="w-full text-left text-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded px-2 py-1 transition-colors truncate"
              style={{ paddingLeft: `${(item.level - 1) * 12 + 8}px` }}
              title={item.text}
              onClick={() => scrollToItem(idx)}
            >
              <span className="text-zinc-400 mr-1.5">
                {item.type === 'section' ? '#' : '▸'}
              </span>
              {item.text}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
