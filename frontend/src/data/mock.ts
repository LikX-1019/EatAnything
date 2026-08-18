import type { FeedComment, HistoryItem, ReviewItem, SchoolItem, StoreItem } from '../types'

const food = (name: string) => `/static/images/foods/${name}.jpg`

export const mockSchools: SchoolItem[] = [
  { id: 'demo-university', name: '示例大学', areas: [{ id: 'east-campus', name: '东校区' }, { id: 'west-campus', name: '西校区' }, { id: 'new-campus', name: '新校区' }] },
  { id: 'city-tech', name: '城市理工大学', areas: [{ id: 'main-campus', name: '主校区' }, { id: 'science-park', name: '科教园校区' }] },
  { id: 'normal-college', name: '师范学院', areas: [{ id: 'old-campus', name: '老校区' }, { id: 'new-town', name: '新校区' }, { id: 'university-town', name: '大学城校区' }] }
]

export const mockStores: StoreItem[] = [
  { id: 1, schoolId: 'demo-university', areaId: 'east-campus', name: '重庆老火锅', category: '川菜 · 火锅', address: '生活街 18 号', image: food('hotpot'), eaten: true, favorite: true, score: 4.9 },
  { id: 2, schoolId: 'demo-university', areaId: 'east-campus', name: '兰州拉面', category: '面食 · 清真', address: '第一食堂东门', image: food('lanzhou-noodles'), eaten: true, favorite: false, score: 4.6 },
  { id: 3, schoolId: 'demo-university', areaId: 'east-campus', name: '炭火烤肉工坊', category: '烤肉 · 韩式', address: '商业街二楼', image: food('korean-bbq'), eaten: true, favorite: false, score: 4.5 },
  { id: 4, schoolId: 'demo-university', areaId: 'west-campus', name: '樱花日料', category: '日料 · 寿司', address: '生活街 20 号', image: food('sushi'), eaten: true, favorite: true, score: 4.8 },
  { id: 5, schoolId: 'demo-university', areaId: 'west-campus', name: '茶颜悦色', category: '饮品 · 奶茶', address: '图书馆西侧', image: food('bubble-tea'), eaten: false, favorite: true, score: 4.7 },
  { id: 6, schoolId: 'demo-university', areaId: 'west-campus', name: '意享披萨', category: '西餐 · 披萨', address: '教学楼南门', image: food('pizza'), eaten: false, favorite: false, score: 4.6 },
  { id: 7, schoolId: 'demo-university', areaId: 'new-campus', name: '美式汉堡屋', category: '西餐 · 汉堡', address: '学生中心一楼', image: food('cheeseburger'), eaten: false, favorite: true, score: 4.4 },
  { id: 8, schoolId: 'demo-university', areaId: 'new-campus', name: '甜心工坊', category: '甜品 · 蛋糕', address: '商业街 9 号', image: food('chocolate-cake'), eaten: false, favorite: false, score: 4.8 },
  { id: 9, schoolId: 'city-tech', areaId: 'main-campus', name: '校园小火锅', category: '火锅 · 单人锅', address: '二食堂三楼', image: food('hotpot'), eaten: false, favorite: false, score: 4.7 },
  { id: 10, schoolId: 'city-tech', areaId: 'main-campus', name: '工大拌面', category: '面食 · 小吃', address: '宿舍区入口', image: food('lanzhou-noodles'), eaten: false, favorite: false, score: 4.5 },
  { id: 11, schoolId: 'city-tech', areaId: 'science-park', name: '科教园咖喱饭', category: '简餐 · 咖喱', address: '创新中心一楼', image: food('rice-bowl'), eaten: false, favorite: false, score: 4.6 },
  { id: 12, schoolId: 'normal-college', areaId: 'old-campus', name: '师院烤肉饭', category: '简餐 · 烤肉饭', address: '老食堂一楼', image: food('korean-bbq'), eaten: false, favorite: false, score: 4.6 },
  { id: 13, schoolId: 'normal-college', areaId: 'new-town', name: '新城寿司铺', category: '日料 · 寿司', address: '生活广场 12 号', image: food('sushi'), eaten: false, favorite: false, score: 4.7 },
  { id: 14, schoolId: 'normal-college', areaId: 'university-town', name: '大学城披萨', category: '西餐 · 披萨', address: '共享商业街', image: food('pizza'), eaten: false, favorite: false, score: 4.5 }
]

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
