Component({
  data: {
    selected: 0,
    fontClass: 'cheese-font',
    tabs: [
      { pagePath: '/pages/home/index', text: '首页', iconPath: '/static/tabbar/house.png', selectedIconPath: '/static/tabbar/house-active.png' },
      { pagePath: '/pages/stores/index', text: '所有店铺', iconPath: '/static/tabbar/store.png', selectedIconPath: '/static/tabbar/store-active.png' },
      { pagePath: '/pages/eaten/index', text: '吃过的店铺', iconPath: '/static/tabbar/heart.png', selectedIconPath: '/static/tabbar/heart-active.png' },
      { pagePath: '/pages/profile/index', text: '我的', iconPath: '/static/tabbar/user-round.png', selectedIconPath: '/static/tabbar/user-round-active.png' }
    ]
  },
  lifetimes: {
    attached: function () {
      this.syncSelected()
    }
  },
  pageLifetimes: {
    show: function () {
      this.syncSelected()
    }
  },
  methods: {
    syncSelected: function () {
      var pages = getCurrentPages()
      var currentPage = pages[pages.length - 1]
      var route = '/' + ((currentPage && currentPage.route) || 'pages/home/index')
      var selected = -1
      for (var index = 0; index < this.data.tabs.length; index += 1) {
        if (this.data.tabs[index].pagePath === route) {
          selected = index
          break
        }
      }
      var fontClass = 'cheese-font'
      try {
        fontClass = wx.getStorageSync('eat-anything:font-preference') === 'system' ? 'system-font' : 'cheese-font'
      } catch (error) {
        // 本地偏好读取失败时继续使用默认手写字体。
      }
      var nextData = {}
      if (selected >= 0 && selected !== this.data.selected) nextData.selected = selected
      if (fontClass !== this.data.fontClass) nextData.fontClass = fontClass
      if (Object.keys(nextData).length) this.setData(nextData)
    },
    switchTab: function (event) {
      var selected = Number(event.currentTarget.dataset.index)
      var pagePath = this.data.tabs[selected].pagePath
      if (selected === this.data.selected) return
      var previous = this.data.selected
      this.setData({ selected: selected })
      wx.switchTab({
        url: pagePath,
        fail: function () {
          this.setData({ selected: previous })
          this.syncSelected()
        }.bind(this),
        complete: function () {
          this.syncSelected()
        }.bind(this)
      })
    }
  }
})
