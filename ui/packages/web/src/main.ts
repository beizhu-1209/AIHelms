import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createI18nInstance, detectInitialLocale, useBranding } from '@aihelms/shared'
import { messages } from './locales'
import './style.css'

const app = createApp(App)
const i18n = createI18nInstance(detectInitialLocale(), messages)
const { refresh: refreshBranding, applyToDocument } = useBranding()
void refreshBranding().then(applyToDocument)
app.use(i18n)
app.use(router)
app.mount('#app')
