import { refreshEfficiencyData } from '@aihelms/shared'

/** Efficiency 模块共享格式化函数 */

export function formatCost(val: number): string {
  if (val === 0) return '¥0'
  if (Math.abs(val) >= 10000) return `¥${(val / 10000).toFixed(4)}万`
  if (Math.abs(val) >= 1) return `¥${val.toFixed(4)}`
  return `¥${val.toFixed(4)}`
}

export function formatCostShort(val: number): string {
  if (val === 0) return '¥0'
  if (Math.abs(val) >= 10000) return `¥${(val / 10000).toFixed(1)}万`
  if (Math.abs(val) >= 1000) return `¥${(val / 1000).toFixed(1)}k`
  return `¥${val.toFixed(0)}`
}

export function formatNumber(val: number): string {
  if (Math.abs(val) >= 1_000_000) return `${(val / 1_000_000).toFixed(2)}M`
  if (Math.abs(val) >= 10_000) return `${(val / 10_000).toFixed(2)}万`
  return val.toLocaleString()
}

export function formatChange(val: number | null | undefined): string {
  if (val === null || val === undefined) return '--'
  const sign = val > 0 ? '+' : ''
  return `${sign}${val.toFixed(1)}%`
}

export interface DatePreset {
  key: string
  label: string
}

export const DATE_PRESETS: DatePreset[] = [
  { key: 'today', label: '今日' },
  { key: '7d', label: '本周' },
  { key: 'month', label: '本月' },
  { key: 'last_month', label: '上月' },
  { key: '30d', label: '近30天' },
  { key: '90d', label: '本季' },
]

export function presetToRange(key: string): { start: string; end: string } {
  const t = new Date()
  const today = t.toISOString().slice(0, 10)
  if (key === 'today') return { start: today, end: today }
  if (key === '7d') {
    return {
      start: new Date(t.getTime() - 6 * 86400000).toISOString().slice(0, 10),
      end: today,
    }
  }
  if (key === 'month') {
    return {
      start: new Date(t.getFullYear(), t.getMonth(), 1).toISOString().slice(0, 10),
      end: today,
    }
  }
  if (key === 'last_month') {
    return {
      start: new Date(t.getFullYear(), t.getMonth() - 1, 1).toISOString().slice(0, 10),
      end: new Date(t.getFullYear(), t.getMonth(), 0).toISOString().slice(0, 10),
    }
  }
  if (key === '30d') {
    return {
      start: new Date(t.getTime() - 29 * 86400000).toISOString().slice(0, 10),
      end: today,
    }
  }
  if (key === '90d') {
    return {
      start: new Date(t.getTime() - 89 * 86400000).toISOString().slice(0, 10),
      end: today,
    }
  }
  return { start: today, end: today }
}

export async function submitEfficiencyRefresh(scope: string): Promise<void> {
  const refresh = await refreshEfficiencyData(scope)
  if (!['queued', 'running'].includes(refresh.update_status || '') || !refresh.task_id) {
    throw new Error(refresh.reason || '刷新任务提交失败')
  }
}


export function keepRefreshIndicator(ms = 8000): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}
