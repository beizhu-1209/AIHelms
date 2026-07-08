import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { fileURLToPath } from 'node:url'
import process from 'node:process'

const uiRoot = dirname(fileURLToPath(new URL('..', import.meta.url)))
const repoRoot = dirname(uiRoot)
const localeRoots = [
  join(uiRoot, 'packages/shared/src/i18n/locales'),
  join(uiRoot, 'packages/web/src/locales'),
  join(uiRoot, 'packages/admin/src/locales'),
]
const locales = ['zh-CN', 'en-US']

const backendLocaleFiles = {
  'zh-CN': join(repoRoot, 'apps/i18n/locales/zh-CN.json'),
  'en-US': join(repoRoot, 'apps/i18n/locales/en-US.json'),
}

function listJsonFiles(dir) {
  if (!existsSync(dir)) return []
  return readdirSync(dir)
    .filter((name) => name.endsWith('.json') && statSync(join(dir, name)).isFile())
    .sort()
}

function readJson(file) {
  return JSON.parse(readFileSync(file, 'utf8'))
}

function readKeys(file) {
  return Object.keys(readJson(file)).sort()
}

function findCjkValues(file) {
  const parsed = readJson(file)
  const cjkPattern = /[\u3400-\u9fff]/
  return Object.entries(parsed)
    .filter(([, value]) => typeof value === 'string' && cjkPattern.test(value))
    .map(([key, value]) => `${key}: ${value}`)
}

function reportCjkValues(file, label, locale) {
  const cjkValues = findCjkValues(file)
  if (!cjkValues.length) return false

  console.error(`[i18n] CJK text found in ${locale} locale for ${label}`)
  for (const item of cjkValues.slice(0, 20)) {
    console.error(`  ${item}`)
  }
  if (cjkValues.length > 20) {
    console.error(`  ...and ${cjkValues.length - 20} more`)
  }
  return true
}

function diffKeys(baseKeys, compareKeys) {
  const compare = new Set(compareKeys)
  return baseKeys.filter((key) => !compare.has(key))
}

let hasError = false

for (const root of localeRoots) {
  if (!existsSync(root)) continue

  const [baseLocale, compareLocale] = locales
  const baseDir = join(root, baseLocale)
  const compareDir = join(root, compareLocale)
  const files = new Set([...listJsonFiles(baseDir), ...listJsonFiles(compareDir)])

  for (const file of files) {
    const baseFile = join(baseDir, file)
    const compareFile = join(compareDir, file)
    const label = relative(uiRoot, join(root, file))

    if (!existsSync(baseFile) || !existsSync(compareFile)) {
      console.error(`[i18n] Missing locale file for ${label}`)
      hasError = true
      continue
    }

    const baseKeys = readKeys(baseFile)
    const compareKeys = readKeys(compareFile)
    const missingInCompare = diffKeys(baseKeys, compareKeys)
    const missingInBase = diffKeys(compareKeys, baseKeys)

    if (missingInCompare.length || missingInBase.length) {
      console.error(`[i18n] Key mismatch in ${label}`)
      if (missingInCompare.length) {
        console.error(`  Missing in ${compareLocale}: ${missingInCompare.join(', ')}`)
      }
      if (missingInBase.length) {
        console.error(`  Missing in ${baseLocale}: ${missingInBase.join(', ')}`)
      }
      hasError = true
    }

    if (reportCjkValues(compareFile, label, compareLocale)) {
      hasError = true
    }
  }
}


const [backendBaseLocale, backendCompareLocale] = locales
const backendBaseFile = backendLocaleFiles[backendBaseLocale]
const backendCompareFile = backendLocaleFiles[backendCompareLocale]

if (existsSync(backendBaseFile) || existsSync(backendCompareFile)) {
  if (!existsSync(backendBaseFile) || !existsSync(backendCompareFile)) {
    console.error('[i18n] Missing backend locale file')
    hasError = true
  } else {
    const baseKeys = readKeys(backendBaseFile)
    const compareKeys = readKeys(backendCompareFile)
    const missingInCompare = diffKeys(baseKeys, compareKeys)
    const missingInBase = diffKeys(compareKeys, baseKeys)

    if (missingInCompare.length || missingInBase.length) {
      console.error('[i18n] Key mismatch in apps/i18n/locales')
      if (missingInCompare.length) {
        console.error(`  Missing in ${backendCompareLocale}: ${missingInCompare.join(', ')}`)
      }
      if (missingInBase.length) {
        console.error(`  Missing in ${backendBaseLocale}: ${missingInBase.join(', ')}`)
      }
      hasError = true
    }

    if (reportCjkValues(backendCompareFile, 'apps/i18n/locales', backendCompareLocale)) {
      hasError = true
    }
  }
}

if (hasError) {
  process.exit(1)
}

console.log('[i18n] Locale keys are consistent.')
