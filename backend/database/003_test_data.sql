BEGIN;

INSERT INTO app_users (external_id, nickname, slogan, level, school_id)
SELECT 'test-user', '测试体验官', '用真实数据验证每一餐。', 5, id
FROM schools
WHERE school_code = 'demo-school'
ON CONFLICT (external_id) DO UPDATE SET
    nickname = EXCLUDED.nickname,
    slogan = EXCLUDED.slogan,
    level = EXCLUDED.level,
    school_id = EXCLUDED.school_id,
    status = 'active';

WITH seed_stores(store_code, name, description, city, district, address) AS (
    VALUES
        ('campus-night-canteen', '校园夜宵档', '现炒小菜和暖胃砂锅，适合晚课后的深夜加餐。', '上海市', '杨浦区', '大学路 128 号'),
        ('riverbank-coffee', '江畔咖啡实验室', '手冲咖啡、巴斯克蛋糕和安静的靠窗座位。', '上海市', '杨浦区', '政立路 48 号'),
        ('northeast-dumpling', '东北饺子馆', '每日现包的三鲜饺子和锅包肉，份量充足。', '上海市', '杨浦区', '国定路 210 号'),
        ('siam-kitchen', '暹罗小馆', '冬阴功、咖喱鸡和泰式奶茶，酸辣开胃。', '上海市', '杨浦区', '四平路 1140 号'),
        ('green-bowl-salad', '青柠轻食碗', '可自选谷物、蛋白质和酱汁的健康轻食。', '上海市', '杨浦区', '淞沪路 77 号'),
        ('sichuan-grilled-fish', '川味烤鱼社', '麻辣烤鱼搭配小龙虾，适合多人晚餐。', '上海市', '杨浦区', '翔殷路 580 号')
)
INSERT INTO stores (store_code, school_id, area_id, name, description, city, district, address)
SELECT ss.store_code, sc.id, sa.id, ss.name, ss.description, ss.city, ss.district, ss.address
FROM seed_stores ss
JOIN schools sc ON sc.school_code = 'demo-school'
JOIN school_areas sa ON sa.school_id = sc.id AND sa.area_code = 'demo-campus'
ON CONFLICT (store_code) DO UPDATE SET
    school_id = EXCLUDED.school_id,
    area_id = EXCLUDED.area_id,
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    city = EXCLUDED.city,
    district = EXCLUDED.district,
    address = EXCLUDED.address,
    status = 'active';

WITH links(store_slug, category_name) AS (
    VALUES
        ('campus-night-canteen', '川菜'), ('campus-night-canteen', '面食'),
        ('riverbank-coffee', '甜品'), ('riverbank-coffee', '饮品'),
        ('northeast-dumpling', '面食'), ('northeast-dumpling', '清真'),
        ('siam-kitchen', '川菜'), ('siam-kitchen', '饮品'),
        ('green-bowl-salad', '西餐'), ('green-bowl-salad', '饮品'),
        ('sichuan-grilled-fish', '川菜'), ('sichuan-grilled-fish', '火锅')
)
INSERT INTO store_category_links (store_id, category_id)
SELECT s.id, c.id
FROM links l
JOIN stores s ON s.store_code = l.store_slug
JOIN store_categories c ON c.name = l.category_name
ON CONFLICT DO NOTHING;

WITH favorites(user_external_id, store_slug, created_at) AS (
    VALUES
        ('demo-user', 'riverbank-coffee', NOW() - INTERVAL '6 days'),
        ('demo-user', 'sichuan-grilled-fish', NOW() - INTERVAL '2 days'),
        ('test-user', 'campus-night-canteen', NOW() - INTERVAL '10 days'),
        ('test-user', 'green-bowl-salad', NOW() - INTERVAL '1 day')
)
INSERT INTO user_favorites (user_id, store_id, created_at)
SELECT u.id, s.id, f.created_at
FROM favorites f
JOIN app_users u ON u.external_id = f.user_external_id
JOIN stores s ON s.store_code = f.store_slug
ON CONFLICT (user_id, store_id) DO UPDATE SET created_at = EXCLUDED.created_at;

WITH test_reviews(user_external_id, store_slug, rating, content, visited_at) AS (
    VALUES
        ('demo-user', 'riverbank-coffee', 5, '咖啡香气很足，下午在这里学习很舒服。', CURRENT_DATE - 6),
        ('demo-user', 'sichuan-grilled-fish', 4, '鱼肉新鲜，三个人吃一份刚刚好。', CURRENT_DATE - 2),
        ('test-user', 'campus-night-canteen', 5, '晚课结束十分钟就能吃到热乎的砂锅。', CURRENT_DATE - 10),
        ('test-user', 'green-bowl-salad', 4, '食材搭配清爽，鸡胸肉分量足。', CURRENT_DATE - 1),
        ('test-user', 'siam-kitchen', 5, '冬阴功汤酸辣平衡，值得再来。', CURRENT_DATE - 4)
)
INSERT INTO reviews (user_id, store_id, rating, content, visited_at)
SELECT u.id, s.id, r.rating, r.content, r.visited_at
FROM test_reviews r
JOIN app_users u ON u.external_id = r.user_external_id
JOIN stores s ON s.store_code = r.store_slug
ON CONFLICT (user_id, store_id) DO UPDATE SET
    rating = EXCLUDED.rating,
    content = EXCLUDED.content,
    visited_at = EXCLUDED.visited_at,
    status = 'published';

WITH events(event_key, user_external_id, store_slug, action, occurred_at) AS (
    VALUES
        ('test-view-coffee', 'demo-user', 'riverbank-coffee', 'store_view', NOW() - INTERVAL '30 minutes'),
        ('test-random-night-canteen', 'demo-user', 'campus-night-canteen', 'random_pick', NOW() - INTERVAL '5 hours'),
        ('test-view-salad', 'test-user', 'green-bowl-salad', 'store_view', NOW() - INTERVAL '1 day'),
        ('test-random-thai', 'test-user', 'siam-kitchen', 'random_pick', NOW() - INTERVAL '3 days')
)
INSERT INTO activity_history (event_key, user_id, store_id, action, occurred_at)
SELECT e.event_key, u.id, s.id, e.action, e.occurred_at
FROM events e
JOIN app_users u ON u.external_id = e.user_external_id
JOIN stores s ON s.store_code = e.store_slug
ON CONFLICT (event_key) DO UPDATE SET
    user_id = EXCLUDED.user_id,
    store_id = EXCLUDED.store_id,
    action = EXCLUDED.action,
    occurred_at = EXCLUDED.occurred_at;

COMMIT;
