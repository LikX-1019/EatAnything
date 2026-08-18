Component({
  data: {
    selected: 0,
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
      if (selected >= 0 && selected !== this.data.selected) this.setData({ selected })
    },
    switchTab: function (event) {
      var selected = Number(event.currentTarget.dataset.index)
      var pagePath = this.data.tabs[selected].pagePath
      if (selected === this.data.selected) return
      this.setData({ selected })
      wx.switchTab({ url: pagePath })
    }
  }
})
