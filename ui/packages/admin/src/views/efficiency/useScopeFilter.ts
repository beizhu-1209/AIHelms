import { computed, ref } from 'vue'
import { getDepartmentTree, getProjects } from '@aihelms/shared'
import { buildDepartmentPathMap } from '../../components/scopePickerTypes'

import type { Ref } from 'vue'
import type { DeptTreeNode, ScopeDimension, ScopeOption } from '../../components/scopePickerTypes'

const SCOPE_PAGE_SIZE = 100

export function useScopeFilter(dimension: Ref<ScopeDimension>, handleConfirmed: () => void) {
  const isScopePickerOpen = ref(false)
  const selectedScopeIds = ref<number[]>([])
  const departmentTree = ref<DeptTreeNode[]>([])
  const projectOptions = ref<ScopeOption[]>([])

  const selectedScopeLabel = computed(() => {
    const label = dimension.value === 'project' ? '项目' : '部门'
    if (selectedScopeIds.value.length === 0) return `全部${label}`
    if (selectedScopeIds.value.length > 1) return `已选${selectedScopeIds.value.length}个${label}`
    const selectedId = selectedScopeIds.value[0]
    if (dimension.value === 'project') {
      return projectOptions.value.find((item) => item.id === selectedId)?.name || `已选1个${label}`
    }
    return buildDepartmentPathMap(departmentTree.value).get(selectedId) || `已选1个${label}`
  })

  async function loadScopeOptions() {
    try {
      const [departments, projects] = await Promise.all([getDepartmentTree(), loadAllProjects()])
      departmentTree.value = departments as DeptTreeNode[]
      projectOptions.value = projects
    } catch {
      departmentTree.value = []
      projectOptions.value = []
    }
  }

  async function loadAllProjects(): Promise<ScopeOption[]> {
    const firstPage = await getProjects(1, SCOPE_PAGE_SIZE)
    const projects = firstPage.items.map((project) => ({ id: project.id, name: project.name }))
    const pageCount = Math.ceil(firstPage.total / SCOPE_PAGE_SIZE)
    for (let page = 2; page <= pageCount; page += 1) {
      const result = await getProjects(page, SCOPE_PAGE_SIZE)
      projects.push(...result.items.map((project) => ({ id: project.id, name: project.name })))
    }
    return projects
  }

  function handleScopeConfirm(ids: number[]) {
    selectedScopeIds.value = ids
    handleConfirmed()
  }

  function resetScopeSelection() {
    selectedScopeIds.value = []
    isScopePickerOpen.value = false
  }

  return {
    departmentTree,
    handleScopeConfirm,
    isScopePickerOpen,
    loadScopeOptions,
    projectOptions,
    resetScopeSelection,
    selectedScopeIds,
    selectedScopeLabel,
  }
}
