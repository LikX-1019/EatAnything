import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'

test('生产前端不再引用用户可见 Mock 动态', () => {
  const home = readFileSync('src/pages/home/index.vue', 'utf8')
  assert.doesNotMatch(home, /data\/mock|feedComments/)
  assert.equal(existsSync('src/data/mock.ts'), false)
})

test('管理端页面和独立 Token 已存在', () => {
  assert.equal(existsSync('src/pages/admin/login.vue'), true)
  assert.equal(existsSync('src/pages/admin/stores.vue'), true)
  const token = readFileSync('src/auth/admin-token.ts', 'utf8')
  assert.match(token, /ADMIN_ACCESS_TOKEN_STORAGE_KEY/)
})
