import { Node, mergeAttributes } from '@tiptap/core'
import { InputRule } from '@tiptap/core'

export const Parenthetical = Node.create({
  name: 'parenthetical',
  group: 'block',
  content: 'text*',

  parseHTML() {
    return [{ tag: 'p.fountain-parenthetical' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['p', mergeAttributes({ class: 'fountain-parenthetical' }, HTMLAttributes), 0]
  },

  addInputRules() {
    return [
      // Opening paren at start of line in dialogue context
      new InputRule({
        find: /^\((.+)\)\s?$/,
        handler: ({ state, range, match }) => {
          const text = '(' + match[1] + ')'
          const tr = state.tr.delete(range.from, range.to)
          tr.replaceWith(range.from, range.from, this.type.create({}, state.schema.text(text)))
        },
      }),
    ]
  },
})
