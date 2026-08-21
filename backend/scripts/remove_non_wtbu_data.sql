-- 删除武汉工商学院以外的演示业务数据。
-- 执行前必须先备份数据库；整个过程在单个事务中完成。

BEGIN;

DO $$
BEGIN
    IF (SELECT COUNT(*) FROM schools WHERE school_code = 'wtbu') <> 1 THEN
        RAISE EXCEPTION '安全检查失败：wtbu 学校不存在或编码不唯一';
    END IF;
END $$;

CREATE TEMP TABLE cleanup_media_ids (
    id BIGINT PRIMARY KEY
) ON COMMIT DROP;

INSERT INTO cleanup_media_ids (id)
SELECT si.media_id
FROM store_images si
JOIN stores st ON st.id = si.store_id
JOIN schools sc ON sc.id = st.school_id
WHERE sc.school_code <> 'wtbu'
UNION
SELECT ri.media_id
FROM review_images ri
JOIN reviews r ON r.id = ri.review_id
LEFT JOIN stores st ON st.id = r.store_id
LEFT JOIN schools sc ON sc.id = st.school_id
LEFT JOIN app_users u ON u.id = r.user_id
LEFT JOIN schools usc ON usc.id = u.school_id
WHERE sc.school_code IS DISTINCT FROM 'wtbu'
   OR usc.school_code IS DISTINCT FROM 'wtbu'
UNION
SELECT ci.photo_media_id
FROM check_ins ci
LEFT JOIN stores st ON st.id = ci.store_id
LEFT JOIN schools sc ON sc.id = st.school_id
LEFT JOIN app_users u ON u.id = ci.user_id
LEFT JOIN schools usc ON usc.id = u.school_id
WHERE sc.school_code IS DISTINCT FROM 'wtbu'
   OR usc.school_code IS DISTINCT FROM 'wtbu'
UNION
SELECT u.avatar_media_id
FROM app_users u
LEFT JOIN schools sc ON sc.id = u.school_id
WHERE u.avatar_media_id IS NOT NULL
  AND sc.school_code IS DISTINCT FROM 'wtbu'
UNION
SELECT mo.id
FROM media_objects mo
JOIN app_users u ON u.id = mo.owner_user_id
LEFT JOIN schools sc ON sc.id = u.school_id
WHERE sc.school_code IS DISTINCT FROM 'wtbu'
ON CONFLICT (id) DO NOTHING;

DELETE FROM stores st
USING schools sc
WHERE st.school_id = sc.id
  AND sc.school_code <> 'wtbu';

DELETE FROM app_users u
WHERE NOT EXISTS (
    SELECT 1
    FROM schools sc
    WHERE sc.id = u.school_id
      AND sc.school_code = 'wtbu'
);

DELETE FROM school_areas sa
USING schools sc
WHERE sa.school_id = sc.id
  AND sc.school_code <> 'wtbu';

DELETE FROM schools
WHERE school_code <> 'wtbu';

DELETE FROM media_objects mo
USING cleanup_media_ids cleanup
WHERE mo.id = cleanup.id
  AND NOT EXISTS (SELECT 1 FROM store_images si WHERE si.media_id = mo.id)
  AND NOT EXISTS (SELECT 1 FROM review_images ri WHERE ri.media_id = mo.id)
  AND NOT EXISTS (SELECT 1 FROM check_ins ci WHERE ci.photo_media_id = mo.id)
  AND NOT EXISTS (SELECT 1 FROM app_users u WHERE u.avatar_media_id = mo.id);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM schools WHERE school_code <> 'wtbu') THEN
        RAISE EXCEPTION '清理失败：仍存在非 wtbu 学校';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM stores st
        JOIN schools sc ON sc.id = st.school_id
        WHERE sc.school_code <> 'wtbu'
    ) THEN
        RAISE EXCEPTION '清理失败：仍存在非 wtbu 店铺';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM app_users u
        LEFT JOIN schools sc ON sc.id = u.school_id
        WHERE sc.school_code IS DISTINCT FROM 'wtbu'
    ) THEN
        RAISE EXCEPTION '清理失败：仍存在非 wtbu 用户';
    END IF;
END $$;

COMMIT;
