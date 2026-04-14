import { Node, mergeAttributes } from '@tiptap/core'
import { InputRule } from '@tiptap/core'

export const SceneHeading = Node.create({
  name: 'sceneHeading',
  group: 'block',
  content: 'text*',

  addAttributes() {
    return {
      location: { default: 'INT.' },
    }
  },

  parseHTML() {
    return [{ tag: 'h3.fountain-scene-heading' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['h3', mergeAttributes({ class: 'fountain-scene-heading' }, HTMLAttributes), 0]
  },

  addInputRules() {
    return [
      // INT. or EXT. at start of line → scene heading
      new InputRule({
        find: /^(INT\.|EXT\.|INT\.\/EXT\.|I\/E\.)\s(.+)$/,
        handler: ({ state, range, match }) => {
          const attrs = { location: match[1] }
          const nodeType = this.type
          const text = match[1] + ' ' + match[2]
          const tr = state.tr.delete(range.from, range.to)
          tr.replaceWith(range.from, range.from, nodeType.create(attrs, state.schema.text(text)))
        },
      }),
    ]
  },
})
