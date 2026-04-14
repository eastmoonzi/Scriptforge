import { Node, mergeAttributes } from '@tiptap/core'
import { InputRule } from '@tiptap/core'

export const Character = Node.create({
  name: 'character',
  group: 'block',
  content: 'text*',

  addAttributes() {
    return {
      dual: { default: false },
    }
  },

  parseHTML() {
    return [{ tag: 'p.fountain-character' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['p', mergeAttributes({ class: 'fountain-character' }, HTMLAttributes), 0]
  },

  addInputRules() {
    return [
      // ALL-CAPS English name (2+ chars) or Chinese character name (2-6 chars)
      // Triggers after typing a name on a new line (following blank line)
      new InputRule({
        find: /^(@?[A-Z\u4e00-\u9fff][A-Z\s\u4e00-\u9fff]{1,20})\n$/,
        handler: ({ state, range, match }) => {
          const text = match[1].replace(/^@/, '')
          const tr = state.tr.delete(range.from, range.to)
          tr.replaceWith(range.from, range.from, this.type.create({}, state.schema.text(text)))
        },
      }),
    ]
  },
})
