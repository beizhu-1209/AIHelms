export type ScopeDimension = 'department' | 'project'

export interface DeptTreeNode {
  id: number
  name: string
  parent_id?: number | null
  children?: DeptTreeNode[]
}

export interface ScopeOption {
  id: number
  name: string
}

export interface DepartmentMatch {
  node: DeptTreeNode
  path: string
}

export function flattenDepartmentTree(
  tree: DeptTreeNode[],
  parentPath: string[] = [],
): DepartmentMatch[] {
  return tree.flatMap((node) => {
    const pathParts = [...parentPath, node.name]
    return [
      { node, path: pathParts.join('/') },
      ...flattenDepartmentTree(node.children || [], pathParts),
    ]
  })
}

export function buildDepartmentPathMap(tree: DeptTreeNode[]): Map<number, string> {
  return new Map(flattenDepartmentTree(tree).map((item) => [item.node.id, item.path]))
}
