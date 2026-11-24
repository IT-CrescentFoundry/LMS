import type { TreeNode } from '../../types/organisation'

export interface ChartNode {
  node: TreeNode
  children: ChartNode[]
}

/** Builds the forest (units whose parent is missing become roots, never dropped). */
export function buildForest(nodes: readonly TreeNode[]): ChartNode[] {
  const byId = new Map<string, ChartNode>(nodes.map((node) => [node.public_id, { node, children: [] }]))
  const roots: ChartNode[] = []
  for (const entry of byId.values()) {
    const parent = entry.node.parent_id ? byId.get(entry.node.parent_id) : undefined
    if (parent && parent !== entry) parent.children.push(entry)
    else roots.push(entry)
  }
  const sort = (list: ChartNode[]) => {
    list.sort((a, b) => a.node.name.localeCompare(b.node.name))
    list.forEach((item) => sort(item.children))
  }
  sort(roots)
  return roots
}
