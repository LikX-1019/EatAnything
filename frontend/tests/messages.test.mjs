import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const read = path => readFile(new URL(`../${path}`, import.meta.url), 'utf8')

test('消息中心页面、API 与微信授权入口已注册', async () => {
  const [pages, api, settings, profile] = await Promise.all([
    read('src/pages.json'),
    read('src/api/messages.ts'),
    read('src/pages/settings/index.vue'),
    read('src/pages/profile/index.vue'),
  ])
  assert.match(pages, /pages\/messages\/index/)
  assert.match(pages, /pages\/messages\/detail/)
  assert.match(api, /\/me\/messages\/unread-count/)
  assert.match(api, /\/me\/announcements\/home/)
  assert.match(api, /page_size: params\.pageSize/)
  assert.match(api, /unread_only = params\.unreadOnly/)
  assert.match(api, /if \(params\.kind\) query\.kind = params\.kind/)
  assert.match(settings, /requestSubscribeMessage/)
  assert.match(profile, /messageStore\.unreadCount/)
})
