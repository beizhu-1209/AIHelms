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

export function formatBigToken(n: number): string {
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(n)
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
  { key: 'today', label: '今天' },
  { key: 'yesterday', label: '昨天' },
  { key: '7d', label: '本周' },
  { key: 'month', label: '本月' },
  { key: 'last_month', label: '上月' },
  { key: '30d', label: '近30天' },
  { key: '90d', label: '本季' },
]

function formatLocalDate(value: Date): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function presetToRange(key: string): { start: string; end: string } {
  const t = new Date()
  const today = formatLocalDate(t)
  if (key === 'today') return { start: today, end: today }
  if (key === 'yesterday') {
    const yesterday = new Date(t)
    yesterday.setDate(t.getDate() - 1)
    const date = formatLocalDate(yesterday)
    return { start: date, end: date }
  }
  if (key === '7d') {
    const start = new Date(t)
    start.setDate(t.getDate() - 6)
    return {
      start: formatLocalDate(start),
      end: today,
    }
  }
  if (key === 'month') {
    return {
      start: formatLocalDate(new Date(t.getFullYear(), t.getMonth(), 1)),
      end: today,
    }
  }
  if (key === 'last_month') {
    return {
      start: formatLocalDate(new Date(t.getFullYear(), t.getMonth() - 1, 1)),
      end: formatLocalDate(new Date(t.getFullYear(), t.getMonth(), 0)),
    }
  }
  if (key === '30d') {
    const start = new Date(t)
    start.setDate(t.getDate() - 29)
    return {
      start: formatLocalDate(start),
      end: today,
    }
  }
  if (key === '90d') {
    const start = new Date(t)
    start.setDate(t.getDate() - 89)
    return {
      start: formatLocalDate(start),
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
