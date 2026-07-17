import { ref } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { getDepartmentTree, getProjects } from '@aihelms/shared'

import { useScopeFilter } from '../src/views/efficiency/useScopeFilter'
import type { ScopeDimension } from '../src/components/scopePickerTypes'

vi.mock('@aihelms/shared', () => ({
  getDepartmentTree: vi.fn(),
  getProjects: vi.fn(),
}))

describe('useScopeFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getDepartmentTree).mockResolvedValue([])
  })

  it('should load projects after the first 100 results', async () => {
    const firstPageItems = Array.from({ length: 100 }, (_, index) => ({
      id: index + 1,
      name: `项目 ${index + 1}`,
    }))
    vi.mocked(getProjects)
      .mockResolvedValueOnce({
        items: firstPageItems,
        total: 101,
        page: 1,
        page_size: 100,
      } as Awaited<ReturnType<typeof getProjects>>)
      .mockResolvedValueOnce({
        items: [{ id: 101, name: '项目 101' }],
        total: 101,
        page: 2,
        page_size: 100,
      } as Awaited<ReturnType<typeof getProjects>>)
    const dimension = ref<ScopeDimension>('project')
    const scopeFilter = useScopeFilter(dimension, vi.fn())

    await scopeFilter.loadScopeOptions()

    expect(getProjects).toHaveBeenNthCalledWith(1, 1, 100)
    expect(getProjects).toHaveBeenNthCalledWith(2, 2, 100)
    expect(scopeFilter.projectOptions.value).toHaveLength(101)
    expect(scopeFilter.projectOptions.value[100]).toEqual({
      id: 101,
      name: '项目 101',
    })
  })
})
