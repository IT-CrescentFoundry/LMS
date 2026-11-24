import type { TreeNode } from '../types/organisation'

/** Units in tree order with their depth (for indented options). */
export function flattenTree(nodes: readonly TreeNode[]): { node: TreeNode; depth: number }[] {
  const children = new Map<string | null, TreeNode[]>()
  const ids = new Set(nodes.map((n) => n.public_id))
  for (const node of nodes) {
    const parent = node.parent_id !== null && ids.has(node.parent_id) ? node.parent_id : null
    const list = children.get(parent) ?? []
    list.push(node)
    children.set(parent, list)
  }
  for (const list of children.values()) list.sort((a, b) => a.name.localeCompare(b.name))
  const out: { node: TreeNode; depth: number }[] = []
  const visit = (parent: string | null, depth: number, seen: Set<string>) => {
    for (const node of children.get(parent) ?? []) {
      if (seen.has(node.public_id)) continue
      seen.add(node.public_id)
      out.push({ node, depth })
      visit(node.public_id, depth + 1, seen)
    }
  }
  visit(null, 0, new Set())
  return out
}
