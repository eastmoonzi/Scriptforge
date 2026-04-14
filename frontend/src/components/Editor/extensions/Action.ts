import { Node, mergeAttributes } from '@tiptap/core'
import { InputRule } from '@tiptap/core'

export const Action = Node.create({
  name: 'action',
  group: 'block',
  content: 'text*',

  parseHTML() {
    return [{ tag: 'p.fountain-action' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['p', mergeAttributes({ class: 'fountain-action' }, HTMLAttributes), 0]
  },

  addInputRules() {
    return [
      // Force action with ! prefix
      new InputRule({
        find: /^!(.+)$/,
        handler: ({ state, range, match }) => {
          const text = match[1]
          const tr = state.tr.delete(range.from, range.to)
          tr.replaceWith(range.from, range.from, this.type.create({}, state.schema.text(text)))
        },
      }),
    ]
  },
})
