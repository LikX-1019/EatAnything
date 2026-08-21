BEGIN;

-- 这里只初始化跨学校复用的基础分类，不再创建演示学校或演示店铺。
-- 武汉工商学院业务数据由 scripts/seed_wtbu_demo.py 幂等维护。
INSERT INTO store_categories (name, sort_order) VALUES
    ('火锅', 10),
    ('川菜', 20),
    ('日料', 30),
    ('寿司', 40),
    ('西餐', 50),
    ('披萨', 60),
    ('饮品', 70),
    ('奶茶', 80),
    ('烤肉', 90),
    ('韩式', 100),
    ('甜品', 110),
    ('蛋糕', 120),
    ('汉堡', 130),
    ('面食', 140),
    ('清真', 150),
    ('自选餐', 160),
    ('盖饭', 170),
    ('川湘菜', 180),
    ('韩餐', 190),
    ('饺子', 200),
    ('轻食', 210)
ON CONFLICT (name) DO UPDATE SET
    sort_order = EXCLUDED.sort_order;

COMMIT;
