import { Node, mergeAttributes } from '@tiptap/core'
import { InputRule } from '@tiptap/core'

export const Dialogue = Node.create({
  name: 'dialogue',
  group: 'block',
  content: 'text*',

  parseHTML() {
    return [{ tag: 'p.fountain-dialogue' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['p', mergeAttributes({ class: 'fountain-dialogue' }, HTMLAttributes), 0]
  },

  addInputRules() {
    return [
      // No auto-trigger — dialogue is set via Tab cycling or programmatic insertion
    ]
  },
})
