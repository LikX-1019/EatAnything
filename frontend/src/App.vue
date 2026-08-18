<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'

const CHEESE_FONT_URL = 'https://cdn.jsdelivr.net/npm/@fontpkg/xiao-ke-nai-lao-ti-shang-yong-mian-fei-qing-ke-zi-ti@1.0.0/%E5%B0%8F%E5%8F%AF%E5%A5%B6%E9%85%AA%E4%BD%93.ttf'

function loadMiniProgramFont() {
  // #ifdef MP-WEIXIN
  uni.loadFontFace({
    global: true,
    scopes: ['webview'],
    family: 'ZQKNLT',
    source: `url("${CHEESE_FONT_URL}")`,
    success: () => console.info('小可奶酪体加载成功'),
    fail: (error) => console.warn('小可奶酪体加载失败，已回退系统字体', error)
  })
  // #endif
}

onLaunch(() => {
  console.info('校园吃什么已启动')
  loadMiniProgramFont()
})
</script>

<style>
/* #ifdef H5 */
@import url("https://fontsapi.zeoseven.com/242/main/result.css");

@font-face {
  font-family: "Cheese Local";
  src: local("小可奶酪体 商用免费@庆科字体"), local("小可奶酪体"), local("ZQKNLT Regular"), local("ZQKNLT");
  font-display: swap;
}
/* #endif */

page {
  --brand: #e8755f;
  --brand-deep: #7d4d35;
  --brand-soft: #f9dcd2;
  --coral: #ef7d72;
  --amber: #e9a541;
  --green: #79a66e;
  --green-soft: #dceacd;
  --ink: #493424;
  --muted: #8a7463;
  --line: #dfcdb4;
  --surface: #fffdf6;
  --page: #f8f0df;
  --paper-shadow: 0 8rpx 20rpx rgba(111, 79, 43, .12), 0 2rpx 4rpx rgba(111, 79, 43, .08);
  --hand-font: "ZQKNLT", "Cheese Local", "小可奶酪体", "Kaiti SC", "STKaiti", "KaiTi", "PingFang SC", cursive;
  background: var(--page);
  color: var(--ink);
  background-image:
    radial-gradient(circle at 18% 12%, rgba(182, 134, 79, .055) 0 1rpx, transparent 2rpx),
    radial-gradient(circle at 80% 34%, rgba(182, 134, 79, .045) 0 1rpx, transparent 2rpx),
    linear-gradient(rgba(255,255,255,.28), rgba(255,255,255,.28));
  background-size: 20rpx 22rpx, 27rpx 31rpx, auto;
  font-family: var(--hand-font);
  font-size: 32rpx;
}

/* #ifdef H5 */
body { font-family: "ZQKNLT", "Cheese Local", "小可奶酪体", "Kaiti SC", "STKaiti", "KaiTi", "PingFang SC", cursive; }
html[data-app-font="system"] body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif;
}
/* #endif */
.system-font { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", Arial, sans-serif; }

view, text, image, button, input, textarea, scroll-view { box-sizing: border-box; }
button, input, textarea { font-family: inherit; }
button { display: flex; align-items: center; justify-content: center; margin: 0; padding: 0; line-height: normal; background: transparent; text-align: center; }
button::after { border: 0; }
.page-shell { min-height: 100vh; padding-bottom: calc(164rpx + env(safe-area-inset-bottom)); }
.tap-active { opacity: 0.72; }
.single-line { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.content-width { width: min(100%, 1040rpx); margin: 0 auto; }
</style>
