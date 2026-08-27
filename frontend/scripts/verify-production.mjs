import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

const root = process.cwd()
const forbidden = [
  '121.43.97.186',
  'VITE_DEV_LOGIN_ENABLED=true',
  'data/mock',
  'feedComments',
]

function walk(directory) {
  if (!existsSync(directory)) return []
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    return entry.isDirectory() ? walk(path) : [path]
  })
}

const targets = [...walk(join(root, 'src')), ...walk(join(root, 'dist', 'build'))]
const failures = []
for (const file of targets) {
  if (!/\.(?:ts|vue|js|json|html|css|wxss|wxml|map)$/.test(file)) continue
  const content = readFileSync(file, 'utf8')
  for (const marker of forbidden) {
    if (content.includes(marker)) failures.push(`${relative(root, file)} 包含禁止内容：${marker}`)
  }
  if (content.includes('localhost') || content.includes('127.0.0.1')) failures.push(`${relative(root, file)} 包含本地地址`)
}
if (failures.length) {
  console.error(failures.join('\n'))
  process.exit(1)
}
console.log(`生产产物检查通过：扫描 ${targets.length} 个文件`)
