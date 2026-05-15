type ToastType = 'success' | 'error' | 'warning' | 'info'

function showToast(message: string, type: ToastType = 'info', duration = 4000) {
  window.dispatchEvent(
    new CustomEvent('aihelms-toast', {
      detail: { message, type, duration },
    })
  )
}

export const toast = {
  success(message: string, duration?: number) {
    showToast(message, 'success', duration)
  },
  error(message: string, duration?: number) {
    showToast(message, 'error', duration)
  },
  warning(message: string, duration?: number) {
    showToast(message, 'warning', duration)
  },
  info(message: string, duration?: number) {
    showToast(message, 'info', duration)
  },
}
