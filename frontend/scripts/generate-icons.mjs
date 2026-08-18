import { mkdir, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const sourceDir = resolve(root, 'node_modules/lucide-static/icons')
const outputDir = resolve(root, 'src/static/tabbar')
const iconNames = ['house', 'store', 'heart', 'user-round']
const activeColors = {
  house: '#e46f5c',
  store: '#c77b36',
  heart: '#63a66b',
  'user-round': '#df852f'
}

const activeHouseSvg = `
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24">
  <path d="M3 10.6 12 3l9 7.6" fill="#f3a18f" stroke="#c85d4d" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M5.2 10v10h13.6V10" fill="#ffe4a6" stroke="#c85d4d" stroke-width="1.7" stroke-linejoin="round"/>
  <path d="M10 20v-6h4v6" fill="#e79b4c" stroke="#a85d3b" stroke-width="1.35" stroke-linejoin="round"/>
  <path d="M7.4 6.8V4.6h2.2v.4" fill="none" stroke="#c85d4d" stroke-width="1.5" stroke-linecap="round"/>
</svg>`

await mkdir(outputDir, { recursive: true })

for (const iconName of iconNames) {
  const source = await readFile(resolve(sourceDir, `${iconName}.svg`), 'utf8')
  for (const variant of [
    { suffix: '', color: '#8e735e' },
    { suffix: '-active', color: activeColors[iconName] }
  ]) {
    const svg = iconName === 'house' && variant.suffix === '-active'
      ? activeHouseSvg
      : source
        .replace(/stroke="currentColor"/g, `stroke="${variant.color}"`)
        .replace('<svg ', '<svg width="64" height="64" ')
    await sharp(Buffer.from(svg)).resize(64, 64).png().toFile(
      resolve(outputDir, `${iconName}${variant.suffix}.png`)
    )
  }
}

console.info(`Generated ${iconNames.length * 2} tab bar icons.`)
