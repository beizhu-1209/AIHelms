import { createRenderer, nextTick } from 'vue'

// A Vue component host for unit tests; it does not launch a browser or emulate CSS.
export interface RenderNode {
  tag: string
  text: string
  props: Record<string, unknown>
  children: RenderNode[]
  parent: RenderNode | null
}

export function createNode(tag: string, text = ''): RenderNode {
  return { tag, text, props: {}, children: [], parent: null }
}

function removeNode(node: RenderNode): void {
  if (node.parent) {
    const index = node.parent.children.indexOf(node)
    if (index >= 0) node.parent.children.splice(index, 1)
    node.parent = null
  }
}

function insertNode(node: RenderNode, parent: RenderNode, anchor: RenderNode | null = null): void {
  removeNode(node)
  const index = anchor ? parent.children.indexOf(anchor) : -1
  if (index < 0) parent.children.push(node)
  else parent.children.splice(index, 0, node)
  node.parent = parent
}

export const renderer = createRenderer<RenderNode, RenderNode>({
  createElement: (tag) => createNode(tag),
  createText: (text) => createNode('#text', text),
  createComment: (text) => createNode('#comment', text),
  setText: (node, text) => { node.text = text },
  setElementText: (node, text) => {
    node.text = text
    node.children = []
  },
  parentNode: (node) => node.parent,
  nextSibling: (node) => {
    if (!node.parent) return null
    return node.parent.children[node.parent.children.indexOf(node) + 1] ?? null
  },
  insert: insertNode,
  remove: removeNode,
  patchProp: (node, key, _previous, value) => { node.props[key] = value },
  insertStaticContent: (content, parent, anchor) => {
    const node = createNode('#static', content)
    insertNode(node, parent, anchor)
    return [node, node]
  },
})

export function findNode(root: RenderNode, matches: (node: RenderNode) => boolean): RenderNode | undefined {
  if (matches(root)) return root
  for (const child of root.children) {
    const match = findNode(child, matches)
    if (match) return match
  }
  return undefined
}

export function nodeText(node: RenderNode): string {
  if (node.tag === '#comment') return ''
  return node.text + node.children.map(nodeText).join('')
}

export async function flushUpdates(): Promise<void> {
  await new Promise<void>(resolve => setImmediate(resolve))
  await nextTick()
}

export async function clickNode(node: RenderNode): Promise<void> {
  if (node.props.disabled) return
  const handler = node.props.onClick
  if (typeof handler !== 'function') throw new Error('Selected node has no click handler')
  handler()
  await flushUpdates()
}
