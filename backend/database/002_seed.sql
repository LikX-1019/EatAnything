BEGIN;

INSERT INTO app_users (external_id, nickname, slogan, level)
VALUES ('demo-user', '干饭小能手', '干饭是第一生产力！', 3)
ON CONFLICT (external_id) DO UPDATE SET
    nickname = EXCLUDED.nickname,
    slogan = EXCLUDED.slogan,
    level = EXCLUDED.level;

INSERT INTO store_categories (name, sort_order) VALUES
    ('火锅', 10), ('川菜', 20), ('日料', 30), ('寿司', 40),
    ('西餐', 50), ('披萨', 60), ('饮品', 70), ('奶茶', 80),
    ('烤肉', 90), ('韩式', 100), ('甜品', 110), ('蛋糕', 120),
    ('汉堡', 130), ('面食', 140), ('清真', 150)
ON CONFLICT (name) DO UPDATE SET sort_order = EXCLUDED.sort_order;

INSERT INTO schools (school_code, name, city, district, address, latitude, longitude)
VALUES ('demo-school', '演示学校', '上海市', '杨浦区', '大学路 1 号', 31.303000, 121.513000)
ON CONFLICT (school_code) DO UPDATE SET
    name = EXCLUDED.name,
    city = EXCLUDED.city,
    district = EXCLUDED.district,
    address = EXCLUDED.address,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    status = 'active';

INSERT INTO stores (
    slug, name, description, city, district, address, area
) VALUES
    ('chongqing-old-hotpot', '重庆老火锅', '牛油锅底香气浓郁，适合朋友聚餐。', '上海市', '黄浦区', '中山南路18号', '黄浦校外区'),
    ('sakura-japanese', '樱花日料', '主打寿司、刺身和日式定食。', '上海市', '静安区', '南京西路120号', '静安校外区'),
    ('italian-pizza', '意享披萨', '现烤薄底披萨和经典意式小食。', '上海市', '徐汇区', '衡山路35号', '徐汇校外区'),
    ('tea-color', '茶颜悦色', '提供奶茶、果茶和轻甜点。', '上海市', '长宁区', '愚园路80号', '长宁校外区'),
    ('charcoal-bbq', '炭火烤肉工房', '炭火现烤，提供韩式烤肉组合。', '上海市', '杨浦区', '大学路66号', '大学路商圈'),
    ('sweet-workshop', '甜心工坊', '每日制作蛋糕、巧克力甜点和咖啡。', '上海市', '虹口区', '四川北路99号', '四川北路商圈'),
    ('american-burger', '美式汉堡屋', '手工牛肉汉堡，搭配薯条和汽水。', '上海市', '浦东新区', '世纪大道77号', '世纪大道商圈'),
    ('lanzhou-noodles', '兰州拉面', '清汤牛肉面，面条可选粗细。', '上海市', '普陀区', '长寿路88号', '长寿路商圈')
ON CONFLICT (slug) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    city = EXCLUDED.city,
    district = EXCLUDED.district,
    address = EXCLUDED.address,
    area = EXCLUDED.area;

UPDATE stores
SET school_id = (SELECT id FROM schools WHERE school_code = 'demo-school')
WHERE slug IN (
    'chongqing-old-hotpot', 'sakura-japanese', 'italian-pizza', 'tea-color',
    'charcoal-bbq', 'sweet-workshop', 'american-burger', 'lanzhou-noodles'
);

WITH links(store_slug, category_name) AS (
    VALUES
        ('chongqing-old-hotpot', '火锅'), ('chongqing-old-hotpot', '川菜'),
        ('sakura-japanese', '日料'), ('sakura-japanese', '寿司'),
        ('italian-pizza', '西餐'), ('italian-pizza', '披萨'),
        ('tea-color', '饮品'), ('tea-color', '奶茶'),
        ('charcoal-bbq', '烤肉'), ('charcoal-bbq', '韩式'),
        ('sweet-workshop', '甜品'), ('sweet-workshop', '蛋糕'),
        ('american-burger', '西餐'), ('american-burger', '汉堡'),
        ('lanzhou-noodles', '面食'), ('lanzhou-noodles', '清真')
)
INSERT INTO store_category_links (store_id, category_id)
SELECT s.id, c.id
FROM links l
JOIN stores s ON s.slug = l.store_slug
JOIN store_categories c ON c.name = l.category_name
ON CONFLICT DO NOTHING;

WITH image_links(store_slug, object_key) AS (
    VALUES
        ('chongqing-old-hotpot', 'stores/chongqing-old-hotpot/cover.jpg'),
        ('sakura-japanese', 'stores/sakura-japanese/cover.jpg'),
        ('italian-pizza', 'stores/italian-pizza/cover.jpg'),
        ('tea-color', 'stores/tea-color/cover.jpg'),
        ('charcoal-bbq', 'stores/charcoal-bbq/cover.jpg'),
        ('sweet-workshop', 'stores/sweet-workshop/cover.jpg'),
        ('american-burger', 'stores/american-burger/cover.jpg'),
        ('lanzhou-noodles', 'stores/lanzhou-noodles/cover.jpg')
)
INSERT INTO store_images (store_id, media_id, is_primary, sort_order)
SELECT s.id, m.id, TRUE, 0
FROM image_links l
JOIN stores s ON s.slug = l.store_slug
JOIN media_objects m ON m.object_key = l.object_key
ON CONFLICT (store_id, media_id) DO UPDATE SET is_primary = TRUE, sort_order = 0;

WITH favorites(store_slug, created_at) AS (
    VALUES
        ('chongqing-old-hotpot', NOW() - INTERVAL '20 days'),
        ('sakura-japanese', NOW() - INTERVAL '16 days'),
        ('sweet-workshop', NOW() - INTERVAL '3 days')
)
INSERT INTO user_favorites (user_id, store_id, created_at)
SELECT u.id, s.id, f.created_at
FROM favorites f
JOIN app_users u ON u.external_id = 'demo-user'
JOIN stores s ON s.slug = f.store_slug
ON CONFLICT (user_id, store_id) DO UPDATE SET
    created_at = EXCLUDED.created_at;

WITH seed_reviews(store_slug, rating, content, visited_at) AS (
    VALUES
        ('chongqing-old-hotpot', 5, '锅底很香，辣度刚刚好，聚餐氛围也不错。', CURRENT_DATE - 18),
        ('sakura-japanese', 5, '食材新鲜，摆盘精致，推荐寿司拼盘。', CURRENT_DATE - 15),
        ('italian-pizza', 4, '饼底酥脆，芝士很足，出餐速度快。', CURRENT_DATE - 8)
)
INSERT INTO reviews (user_id, store_id, rating, content, visited_at)
SELECT u.id, s.id, sr.rating, sr.content, sr.visited_at
FROM seed_reviews sr
JOIN app_users u ON u.external_id = 'demo-user'
JOIN stores s ON s.slug = sr.store_slug
ON CONFLICT (user_id, store_id) DO UPDATE SET
    rating = EXCLUDED.rating,
    content = EXCLUDED.content,
    visited_at = EXCLUDED.visited_at,
    status = 'published';

WITH events(event_key, store_slug, action, occurred_at) AS (
    VALUES
        ('seed-random-sakura', 'sakura-japanese', 'random_pick', NOW() - INTERVAL '2 hours'),
        ('seed-view-hotpot', 'chongqing-old-hotpot', 'store_view', NOW() - INTERVAL '1 day'),
        ('seed-random-pizza', 'italian-pizza', 'random_pick', NOW() - INTERVAL '4 days')
)
INSERT INTO activity_history (event_key, user_id, store_id, action, occurred_at)
SELECT e.event_key, u.id, s.id, e.action, e.occurred_at
FROM events e
JOIN app_users u ON u.external_id = 'demo-user'
JOIN stores s ON s.slug = e.store_slug
ON CONFLICT (event_key) DO UPDATE SET
    store_id = EXCLUDED.store_id,
    action = EXCLUDED.action,
    occurred_at = EXCLUDED.occurred_at;

COMMIT;
