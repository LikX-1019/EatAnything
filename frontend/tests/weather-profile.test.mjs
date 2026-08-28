import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'


test('首页展示按学校缓存的动态天气且天气失败不阻塞核心加载', () => {
  const home = readFileSync('src/pages/home/index.vue', 'utf8')
  const header = readFileSync('src/components/PageHeader.vue', 'utf8')
  const weatherStore = readFileSync('src/stores/useWeatherStore.ts', 'utf8')

  assert.match(home, /useWeatherStore/)
  assert.match(home, /void weatherStore\.loadForSchool\(schoolId, refresh\)/)
  assert.match(home, /:weather-data="weatherStore\.currentWeather"/)
  assert.doesNotMatch(header, /28°C 多云/)
  assert.match(header, /temperatureMin.*temperatureMax/)
  assert.match(header, /天气暂不可用/)
  assert.match(header, /Open-Meteo \/ CC BY 4\.0/)
  assert.match(weatherStore, /attemptedBySchool/)
  assert.match(weatherStore, /if \(!force && attemptedBySchool\.value\[schoolId\]\)/)
})


test('切换学校会刷新对应天气缓存', () => {
  const schools = readFileSync('src/pages/schools/index.vue', 'utf8')
  assert.match(schools, /weatherStore\.loadForSchool\(id, true\)/)
})


test('个人卡片将学校放在用户名右侧并把编辑提示放到统计区下方', () => {
  const profile = readFileSync('src/pages/profile/index.vue', 'utf8')
  const titleRow = profile.indexOf('class="identity-title-row"')
  const stats = profile.indexOf('class="stats"')
  const edit = profile.indexOf('class="edit-hint"')

  assert.ok(titleRow > 0)
  assert.match(profile.slice(titleRow, stats), /profile-name[\s\S]*profile-school/)
  assert.ok(edit > stats)
  assert.match(profile, /margin-left: 28rpx/)
  assert.match(profile, /\.edit-hint \{[^}]*margin: 14rpx auto 0;[^}]*text-align: center;/)
  assert.match(profile, /profile-slogan/)
})
