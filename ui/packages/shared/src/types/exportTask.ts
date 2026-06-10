export interface ExportOptionItem {
  key: string
  label: string
}

export interface ExportTask {
  id: number
  task_name: string
  source: string
  export_type: string
  status: string
  created_by: string
  created_at: string
  started_at: string | null
  finished_at: string | null
  canceled_at: string | null
  file_name: string | null
  file_size: number | null
  row_count: number
  error_message: string
  retry_of_task_id: number | null
  download_url: string | null
  can_retry: boolean
  can_cancel: boolean
}

export interface ExportTaskListResult {
  items: ExportTask[]
  total: number
  page: number
  page_size: number
  sources: ExportOptionItem[]
  statuses: ExportOptionItem[]
  retention_days: number
}

export interface ExportTaskQuery {
  page?: number
  page_size?: number
  source?: string
  status?: string
}

export type ExportTaskParams = Record<string, string | number | boolean | null | undefined>

export interface CreateExportTaskParams {
  source: string
  export_type: string
  task_name?: string
  params?: ExportTaskParams
}

export interface CleanupExportTaskResult {
  deleted_tasks: number
  deleted_files: number
  retention_days: number
}
