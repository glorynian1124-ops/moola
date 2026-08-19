# 前端功能 × 后端接口 对接矩阵（Phase 1）

> 目的：逐项评估前端原型（`prototype/`）所有功能与后端数据库能否一一对接。
> 结论速览：**数据类功能 12 项中 9 项可对接，3 项为纯 UI/占位；其余页面为本地/占位。**
> 更新（Phase 1 完成）：后端 API 蓝图 `app/web/api.py` + 统计聚合 `app/analyzer/stats.py` 已落地，
> 前端对接层 `prototype/api.js` 已实现并通过浏览器全链路验证（明细/记账/搜索/日历/删除）。

## 对接总原则

前端 `app.js` 的数据源是内存 `tx` 数组（`INITIAL_TX` 假数据），结构为：
```js
tx = [{ date: 'YYYY-MM-DD', items: [{ type, remark, money }] }]
```
后端 `models.list_transactions_grouped(month)` 返回**同构**数据（`{groups:[{date, items:[{id,type,remark,money}]}]}` + summary），
因此前端读侧几乎不用改，只把"填充 tx"换成 fetch；写侧（记账）调 API。

## 对接矩阵

| # | 前端功能（页面） | 所需数据 | 后端接口 | 状态 |
|---|-----------------|---------|---------|------|
| 1 | **明细页** 列表+概览+月份切换 | 按月分组账单+收支汇总 | `GET /api/transactions/group?month=` | ✅ 已对接 |
| 2 | **记账页** 新增/再记 | 分类列表；写入账单 | `GET /api/categories`；`POST /api/transactions` | ✅ 已对接（返回新 id） |
| 3 | **统计页** 柱状图/环形图/周月年 | 趋势聚合 + 分类占比 | `GET /api/stats/trend`、`GET /api/stats/category` | ✅ 已对接（数据源真实） |
| 4 | **日历页** 每日标记+当日账单 | 某月每日收支 | `GET /api/calendar?month=` + group 懒加载 | ✅ 已对接 |
| 5 | **搜索页** 关键词+排序 | 搜索账单/类别 | `GET /api/search?q=&mode=&sort=` | ✅ 已对接 |
| 6 | **年度统计** | 年度收支列表 | `GET /api/stats/year?y=`（或复用 report） | 🆕 待补 |
| 7 | **类别管理/新增类别** | 分类 CRUD | `GET/POST/PUT/DELETE /api/categories` | ⏳ 读已接（GET/POST），管理页待接 |
| 8 | **导入页** | 上传 CSV | `POST /api/import/wechat` / `alipay` | ✅ 接口已建（前端页未挂） |
| 9 | **账单统计/图表/自定义统计** | 分类占比 | 复用 `/api/stats/category` + `GET /api/report` | ✅ 数据源真实后自动生效 |
| 10 | **设置页** | 显示偏好 | `GET/PUT /api/settings`（🆕）或 `localStorage` | 🆕 或本地 |
| 11 | **账本管理** | 账本 CRUD | 暂无（MVP 单账本） | ➖ 占位 |
| 12 | **余额页** | 账户余额 | 无（CSV 无余额数据） | ➖ 占位（不接） |
| 13 | **经济简讯** | 订阅源/文章 | `GET /api/feeds` 等（Phase 3） | ⏳ Phase 3 |
| 14 | 会员/登录/注册/手势/指纹/主题/备份/关于/更多应用 | 无 | 纯 UI / localStorage / 占位 | ➖ 不接数据库 |

## 需要新增的后端接口（Phase 1）

| 接口 | 用途 | 数据来源 |
|------|------|---------|
| `GET /api/transactions/group?month=` | 明细页 | `models.list_transactions_grouped`（已有） |
| `GET /api/stats/trend?period=&cat=` | 统计柱状图 | 新增 `analyzer/stats.py` |
| `GET /api/stats/category?month=&cat=` | 统计环形图 | `report.by_category` / 新聚合 |
| `GET /api/calendar?month=` | 日历 | 每日收支聚合 |
| `GET /api/search?q=&mode=&sort=` | 搜索 | `models.search_transactions`（已有） |
| `GET/POST/PUT/DELETE /api/categories` | 类别管理 | `models.list_categories/add_category`（已有，补改删） |
| `POST /api/import/wechat|alipay` | 导入 | parser（已有） |
| `GET /api/settings` / `PUT /api/settings` | 设置 | user_settings 表（新增）或 localStorage |

## 实施进度（对接落地）

1. ✅ **后端 API 蓝图** `app/web/api.py`：transactions/group、stats/trend、stats/category、calendar、search、categories、import
2. ✅ **统计聚合** `app/analyzer/stats.py`：trend / category_share / daily_calendar
3. ✅ **CORS**：`app/web/app.py` 全局 after_request 头 + OPTIONS 预检放行
4. ✅ **前端对接** `prototype/api.js`（覆盖全局函数，不改渲染逻辑）：
   - 明细页：启动加载当前月+上月，`tx` 填充后端真实数据
   - 记账：`addTx` → `POST /api/transactions` 成功后本地插入（带 id）
   - 搜索：`runSearch` → `GET /api/search`（全库）
   - 日历：切月懒加载 + 列表日期跟随当前月
   - 删除：详情页捕获阶段 `DELETE /api/transactions/<id>`
   - 概览：动态取最近有数据月份
5. ✅ **浏览器全链路验证**：明细真实数据 / 统计饼图柱状图 / 搜索 / 记账入库 / 删除落库 / 日历跨月
6. ⏳ **待办**：类别管理页 CRUD、导入页挂接、年度统计接口、设置持久化

> 注：后端 API 单测（Python requests）全部 200；期间修复 2 个 500：`stats.py` 函数名 `calendar` 遮蔽标准库、`search_transactions` 参数绑定数不匹配。
