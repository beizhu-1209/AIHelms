type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastOptions {
  actionLabel?: string
  actionPath?: string
}

function showToast(message: string, type: ToastType = 'info', duration = 4000, options: ToastOptions = {}) {
  window.dispatchEvent(
    new CustomEvent('aihelms-toast', {
      detail: { message, type, duration, ...options },
    })
  )
}

export const toast = {
  success(message: string, duration?: number, options?: ToastOptions) {
    showToast(message, 'success', duration, options)
  },
  error(message: string, duration?: number) {
    showToast(message, 'error', duration)
  },
  warning(message: string, duration?: number) {
    showToast(message, 'warning', duration)
  },
  info(message: string, duration?: number, options?: ToastOptions) {
    showToast(message, 'info', duration, options)
  },
}
