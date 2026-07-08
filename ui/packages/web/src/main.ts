import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createI18nInstance, detectInitialLocale } from '@aihelms/shared'
import { messages } from './locales'
import './style.css'

const app = createApp(App)
const i18n = createI18nInstance(detectInitialLocale(), messages)
app.use(i18n)
app.use(router)
app.mount('#app')
