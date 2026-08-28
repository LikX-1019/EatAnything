import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'


test('确认选店期间会阻止重复提交', () => {
  const home = readFileSync('src/pages/home/index.vue', 'utf8')
  assert.match(home, /const isConfirmingPick = ref\(false\)/)
  assert.match(home, /if \(isConfirmingPick\.value\) return/)
  assert.match(home, /:disabled="isConfirmingPick"/)
  assert.match(home, /isConfirmingPick \? '记录中…'/)
})


test('设置导航失败时会回退并保留返回个人页能力', () => {
  const profile = readFileSync('src/pages/profile/index.vue', 'utf8')
  const settings = readFileSync('src/pages/settings/index.vue', 'utf8')
  const header = readFileSync('src/components/PageHeader.vue', 'utf8')

  assert.match(profile, /function openSettings\(\)/)
  assert.match(profile, /uni\.navigateTo\(\{[\s\S]*uni\.redirectTo\(\{/)
  assert.match(profile, /item\.key === 'settings'/)
  assert.match(settings, /back-tab-fallback="\/pages\/profile\/index"/)
  assert.match(header, /backTabFallback/)
  assert.match(header, /uni\.switchTab\(/)
})


test('未读数失败不会阻塞个人资料页面', () => {
  const profile = readFileSync('src/pages/profile/index.vue', 'utf8')
  assert.match(profile, /void messageStore\.refreshUnread\(\)\.catch\(\(\) => undefined\)/)
  assert.doesNotMatch(profile, /await messageStore\.refreshUnread\(\)/)
})
