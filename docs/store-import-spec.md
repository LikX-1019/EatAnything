# 店铺批量导入规范

## 1. 适用范围

管理员通过 `POST /api/v1/admin/stores/import` 导入 CSV 或 XLSX 文件。导入采用单事务原子写入：只有全部文件级和行级校验通过后才执行新增或更新；任意一行失败时整批不写入。

## 2. 文件要求

| 项目 | 规则 |
| --- | --- |
| 文件类型 | `.csv`、`.xlsx` |
| 文件大小 | 不超过 5 MB |
| 数据行数 | 1–1000 行，不含表头 |
| CSV 编码 | UTF-8，可带 BOM；分隔符为英文逗号 |
| XLSX 工作表 | 读取第一个可见工作表；首行为表头 |
| 表头 | 必须与字段名和顺序完全一致；未知列、缺失列或重复列均拒绝导入 |
| 空行 | 完全空白的行忽略；部分填写的行按正常数据校验 |
| 公式与宏 | 不执行公式或宏；公式单元格视为非法值 |

## 3. 字段定义

| 字段 | 必填 | 类型/长度 | 示例 | 规则 |
| --- | --- | --- | --- | --- |
| `storeCode` | 是 | 字符串，2–100 | `wtbu-south-001` | 仅允许小写字母、数字、`-`、`_`；去除首尾空格并转为小写；对应数据库 `stores.store_code` |
| `schoolCode` | 是 | 字符串，2–64 | `wtbu` | 必须是系统中已启用的学校编码 |
| `areaCode` | 是 | 字符串，2–64 | `south-canteen` | 必须是该学校下已启用的区域编码 |
| `name` | 是 | 字符串，1–100 | `重庆老火锅` | 去除首尾空格后不能为空 |
| `category` | 是 | 字符串，1–50 | `川菜 · 火锅` | MVP 使用单个展示文本，不拆分标签 |
| `address` | 是 | 字符串，1–200 | `中山路88号` | 仅作为文字展示，不导入经纬度或距离 |
| `imageUrl` | 条件必填 | HTTP(S) URL，最长 2048 | `http://127.0.0.1:9000/eat-anything/stores/001.jpg` | `active` 店铺最终必须有图片；更新已有店铺时留空表示保留原图片 |
| `status` | 是 | 枚举 | `active` | 仅允许 `active`、`hidden`、`closed` |

字段值中的前后空格在校验前去除。`score`、评价数量、收藏状态、吃过状态、创建时间和更新时间均为系统字段，不能导入。

## 4. 新增与更新规则

1. 系统对 `storeCode` 执行去空格和小写标准化后匹配 `stores.store_code`。
2. 数据库中不存在该编码时执行新增。
3. 数据库中已存在且未归档时执行覆盖更新。
4. 数据库中已关闭时允许管理员更新；重新上架需显式将状态改为 `active`。
5. 同一文件中标准化后出现重复编码时返回 `DUPLICATE_STORE_CODE_IN_FILE`。
6. 更新已有店铺时，学校、区域、`name`、`category`、`address`、`status` 使用导入值覆盖；空 `imageUrl` 保留旧图片，非空值覆盖旧图片。
7. 新增或更新为 `active` 时，导入值或已有数据中必须存在有效图片，否则返回 `ACTIVE_STORE_IMAGE_REQUIRED`。
8. 成功导入不会修改店铺评分、评价、收藏、吃过和历史数据。

## 5. 校验顺序

1. 校验管理员 Token 和权限。
2. 校验文件大小与 MIME/扩展名。
3. 解析工作表或 CSV 编码。
4. 校验表头、数据行数和禁止的公式单元格。
5. 标准化字段值并执行逐行字段校验。
6. 校验文件内重复编码和数据库归档/冲突状态。
7. 任意错误时返回全部可发现的行错误，不开启写事务。
8. 全部通过后在单个数据库事务中按 `storeCode` 新增或更新。
9. 返回新增数、更新数和每行处理结果。

## 6. 成功响应示例

```json
{
  "data": {
    "totalRows": 3,
    "createdCount": 2,
    "updatedCount": 1,
    "items": [
      { "row": 2, "storeCode": "cq-hotpot-001", "storeId": "st_01", "action": "created" },
      { "row": 3, "storeCode": "jp-sushi-001", "storeId": "st_02", "action": "updated" },
      { "row": 4, "storeCode": "tea-001", "storeId": "st_03", "action": "created" }
    ]
  },
  "requestId": "req_01JXYZ"
}
```

## 7. 校验失败示例

HTTP 状态为 `422`，没有任何数据写入：

```json
{
  "error": {
    "status": 422,
    "code": "IMPORT_VALIDATION_FAILED",
    "message": "导入文件包含 3 个错误，未写入任何店铺",
    "details": [
      {
        "row": 3,
        "field": "storeCode",
        "code": "DUPLICATE_STORE_CODE_IN_FILE",
        "message": "店铺编码 cq-hotpot-001 在文件中重复"
      },
      {
        "row": 5,
        "field": "imageUrl",
        "code": "ACTIVE_STORE_IMAGE_REQUIRED",
        "message": "active 店铺必须提供图片"
      },
      {
        "row": 8,
        "field": "status",
        "code": "INVALID_ENUM_VALUE",
        "message": "仅允许 active、hidden、closed"
      }
    ]
  },
  "requestId": "req_01JXYZ"
}
```

## 8. 其他错误

| HTTP 状态 | 业务码 | 场景 |
| --- | --- | --- |
| 400 | `INVALID_ARGUMENT` | 未提交文件或 multipart 字段名不是 `file` |
| 401 | `AUTH_REQUIRED` | Token 缺失或失效 |
| 403 | `FORBIDDEN` | 当前账号不是管理员 |
| 409 | `RESOURCE_VERSION_CONFLICT` | 校验通过后提交时店铺数据被其他请求并发修改，事务回滚 |
| 413 | `FILE_TOO_LARGE` | 文件超过 5 MB |
| 415 | `UNSUPPORTED_FILE_TYPE` | 文件不是 CSV/XLSX、MIME 不匹配或文件无法解析 |
| 422 | `IMPORT_VALIDATION_FAILED` | 表头或至少一行数据不符合规则 |
| 429 | `RATE_LIMITED` | 导入频率超过限制 |
| 500 | `INTERNAL_ERROR` | 未预期服务端错误，事务必须回滚 |

## 9. 示例 CSV

```csv
storeCode,schoolCode,areaCode,name,category,address,imageUrl,status
wtbu-south-001,wtbu,south-canteen,南区一品香自选餐,自选餐,南区食堂一层01号,https://cdn.example.com/stores/rice.jpg,active
wtbu-north-001,wtbu,north-canteen,北区老坛酸菜鱼,川湘菜,北区食堂一层01号,https://cdn.example.com/stores/fish.jpg,active
wtbu-north-002,wtbu,north-canteen,韩式石锅拌饭,韩餐,北区食堂一层02号,,hidden
```
