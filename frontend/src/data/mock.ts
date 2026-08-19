import type { FeedComment, HistoryItem, ReviewItem } from '../types'

export const mockReviews: ReviewItem[] = [
  { id: 1, storeId: 1, rating: 5, content: '锅底很香，辣度刚刚好，中午去出餐也很快。', date: '8月5日' },
  { id: 2, storeId: 4, rating: 5, content: '食材新鲜，摆盘精致，推荐三文鱼饭。', date: '7月28日' },
  { id: 3, storeId: 5, rating: 4, content: '离图书馆很近，复习间隙过来很方便。', date: '7月19日' }
]

export const mockHistory: HistoryItem[] = [
  { id: 1, storeId: 1, action: '到店打卡', date: '今天 12:28' },
  { id: 2, storeId: 2, action: '随机抽取', date: '今天 11:52' },
  { id: 3, storeId: 4, action: '提交评价', date: '昨天 18:34' }
]

export const feedComments: FeedComment[] = [
  { id: 1, storeId: 1, user: '匿名同学', content: '锅底很香，一个人吃也很方便。', time: '2分钟前' },
  { id: 2, storeId: 2, user: '小王同学', content: '出餐很快，牛肉面分量足。', time: '8分钟前' },
  { id: 3, storeId: 5, user: '干饭王', content: '下午没课，顺路来一杯。', time: '12分钟前' }
]
