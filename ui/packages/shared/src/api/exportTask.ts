import { request } from './request'
import { toast } from '../utils/toast'
import type {
  CleanupExportTaskResult,
  CreateExportTaskParams,
  ExportTask,
  ExportTaskListResult,
  ExportTaskQuery,
} from '../types/exportTask'

function getToken(): string | null {
  return localStorage.getItem('aihelms_token')
}

function parseFilename(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1])
  const match = disposition.match(/filename="?([^";]+)"?/)
  return match?.[1] || fallback
}

export function getExportTasks(query: ExportTaskQuery = {}): Promise<ExportTaskListResult> {
  return request<ExportTaskListResult>('/api/v1/export-tasks', { params: { ...query } })
}

export async function createExportTask(params: CreateExportTaskParams): Promise<ExportTask> {
  const task = await request<ExportTask>('/api/v1/export-tasks', { method: 'POST', body: params })
  toast.success(`导出任务「${task.task_name}」已创建，请到资源审计 > 导出任务下载表格`, 12000, {
    actionLabel: '去下载',
    actionPath: '/admin/export-tasks',
  })
  return task
}

export function cancelExportTask(taskId: number): Promise<ExportTask> {
  return request<ExportTask>(`/api/v1/export-tasks/${taskId}/cancel`, { method: 'POST' })
}

export function retryExportTask(taskId: number): Promise<ExportTask> {
  return request<ExportTask>(`/api/v1/export-tasks/${taskId}/retry`, { method: 'POST' })
}

export function cleanupExportTasks(retentionDays = 7): Promise<CleanupExportTaskResult> {
  return request<CleanupExportTaskResult>('/api/v1/export-tasks/cleanup', {
    method: 'POST',
    body: { retention_days: retentionDays },
  })
}

export async function downloadExportTask(task: ExportTask): Promise<void> {
  const token = getToken()
  const response = await fetch(`/api/v1/export-tasks/${task.id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    let message = '下载失败'
    try {
      const data = (await response.json()) as { message?: string; detail?: string }
      message = data.message || data.detail || message
    } catch {
      /* ignore */
    }
    throw new Error(message)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = parseFilename(response.headers.get('Content-Disposition'), task.file_name || 'export.csv')
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
