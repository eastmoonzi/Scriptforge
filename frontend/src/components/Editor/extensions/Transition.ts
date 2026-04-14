import { Node, mergeAttributes } from '@tiptap/core'
import { InputRule } from '@tiptap/core'

export const Transition = Node.create({
  name: 'transition',
  group: 'block',
  content: 'text*',

  parseHTML() {
    return [{ tag: 'p.fountain-transition' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['p', mergeAttributes({ class: 'fountain-transition' }, HTMLAttributes), 0]
  },

  addInputRules() {
    return [
      // Lines ending with TO: → transition
      new InputRule({
        find: /^([A-Z\s]+TO:)\s?$/,
        handler: ({ state, range, match }) => {
          const text = match[1]
          const tr = state.tr.delete(range.from, range.to)
          tr.replaceWith(range.from, range.from, this.type.create({}, state.schema.text(text)))
        },
      }),
    ]
  },
})
