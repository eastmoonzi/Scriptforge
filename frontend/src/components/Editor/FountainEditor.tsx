'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { SceneHeading, Character, Dialogue, Parenthetical, Action, Transition } from './extensions'
import { useStore } from '@/lib/store'
import { useCallback, useEffect, useRef } from 'react'
import { extractOutline, parseFountain, tokensToTipTapDoc } from '@/lib/fountain'

/**
 * Serialize TipTap editor content to Fountain plain text.
 * Preserves node types by mapping them to proper Fountain formatting.
 */
function editorToFountain(editor: ReturnType<typeof useEditor>): string {
  if (!editor) return ''

  const lines: string[] = []
  editor.state.doc.forEach((node) => {
    const text = node.textContent

    switch (node.type.name) {
      case 'sceneHeading':
        lines.push('', text, '')
        break
      case 'character':
        lines.push('', text)
        break
      case 'dialogue':
        lines.push(text)
        break
      case 'parenthetical':
        lines.push(text)
        break
      case 'action':
        lines.push('', text)
        break
      case 'transition':
        lines.push('', text, '')
        break
      case 'heading': {
        const level = node.attrs.level || 1
        lines.push('#'.repeat(level) + ' ' + text)
        break
      }
      case 'horizontalRule':
        lines.push('', '===', '')
        break
      default:
        if (text) lines.push(text)
        break
    }
  })

  return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim()
}

export default function FountainEditor() {
  const setFountainContent = useStore((s) => s.setFountainContent)
  const setOutlineItems = useStore((s) => s.setOutlineItems)
  const setEditorInstance = useStore((s) => s.setEditorInstance)
  const fountainContent = useStore((s) => s.fountainContent)
  const lastExternalContent = useRef<string>('')

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
      }),
      Placeholder.configure({
        placeholder: '开始书写你的剧本...\n\nINT. 场景 - 时间\n\n角色名\n对白内容',
      }),
      SceneHeading,
      Character,
      Dialogue,
      Parenthetical,
      Action,
      Transition,
    ],
    editorProps: {
      attributes: {
        class: 'fountain-editor prose prose-sm max-w-none focus:outline-none min-h-full px-16 py-8',
      },
    },
    onUpdate: ({ editor }) => {
      const text = editorToFountain(editor)
      lastExternalContent.current = text
      setFountainContent(text)
      setOutlineItems(extractOutline(text))
    },
  })

  // Store editor instance for use by other components
  useEffect(() => {
    if (editor) {
      setEditorInstance(editor)
    }
    return () => setEditorInstance(null)
  }, [editor, setEditorInstance])

  // When external content changes (file import, AI generation), parse into TipTap doc
  useEffect(() => {
    if (!editor) return
    if (fountainContent === lastExternalContent.current) return
    if (!fountainContent) return

    lastExternalContent.current = fountainContent
    const tokens = parseFountain(fountainContent)
    const doc = tokensToTipTapDoc(tokens)

    try {
      editor.commands.setContent(doc)
    } catch {
      // Fallback: set as plain text
      editor.commands.setContent(fountainContent)
    }
  }, [editor, fountainContent])

  // Keyboard shortcut: Tab to cycle element types
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!editor) return
      if (e.key === 'Tab' && !e.shiftKey) {
        e.preventDefault()
        const nodeType = editor.state.selection.$head.parent.type.name
        const cycle: Record<string, string> = {
          paragraph: 'sceneHeading',
          action: 'sceneHeading',
          sceneHeading: 'character',
          character: 'dialogue',
          dialogue: 'parenthetical',
          parenthetical: 'action',
        }
        const next = cycle[nodeType] || 'paragraph'
        editor.chain().focus().setNode(next as never).run()
      }
    },
    [editor],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <div className="h-full overflow-y-auto bg-white dark:bg-zinc-900 fountain-page">
      <EditorContent editor={editor} />
    </div>
  )
}
