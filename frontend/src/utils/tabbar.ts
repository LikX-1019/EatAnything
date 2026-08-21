interface CustomTabBarInstance {
  data?: { selected?: number }
  setData: (data: { selected: number }) => void
}

interface TabBarPageInstance {
  getTabBar?: () => CustomTabBarInstance | undefined
}

/**
 * 微信自定义 tabBar 会在多个 tab 页面之间复用，页面显示时主动校正选中项，
 * 避免组件保留上一个页面的高亮状态。
 */
export function syncTabBarSelected(selected: number): void {
  // #ifdef MP-WEIXIN
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as unknown as TabBarPageInstance | undefined
  const tabBar = currentPage?.getTabBar?.()
  if (tabBar && tabBar.data?.selected !== selected) tabBar.setData({ selected })
  // #endif
}
