# Moola UI 原型（复刻「简约记账」）

> 本目录是纯静态高保真原型，从简约记账 APK（com.yhqx.account v1.8.9）解包资源中提取真实布局与图片还原。
> 双击 `index.html` 即可在浏览器打开，或用 `python3 -m http.server 8088` 起本地服务后用手机访问。
>
> 反解析成果位于仓库 `apk_analysis/output/`（布局蓝本、图片、资源表），脚本位于 `apk_analysis/step*.py`。

## 文件
- `index.html` —— 4 个主 Tab 页 + 9 个覆盖页（记账/日历/搜索/年度统计/私人信息/管理账本/编辑账本/类别管理/新增类别/会员）
- `style.css` —— 配色/字号/布局（全部从 APK 资源提取）
- `app.js` —— 交互逻辑（Tab 切换 / 计算器键盘 / 记账 / 统计图表 / 日历 / 搜索）
- `api.js` —— **后端对接适配层（Phase 1）**：把明细/统计/日历/搜索/记账/删除接入 Flask 5001 真实数据
- `assets/` —— 从 APK 提取的资源：`DINCond-Bold.otf` 金额字体 + `icons/` 真实图标（CSS mask 上色）

## 后端对接（Phase 1）

前端通过 `api.js` 与后端 Flask API（`python main.py web`，端口 5001）对接：

| 前端功能 | 后端接口 | 说明 |
|---------|---------|------|
| 明细页 / 首页概览 | `GET /api/transactions/group?month=` | 数据同构，直接替换内存假数据 |
| 记账（FAB → 完成） | `POST /api/transactions` | 入库成功返回新记录 id，本地同步 |
| 搜索 | `GET /api/search?q=&mode=&sort=` | 全库搜索（商家/备注/类别） |
| 日历（跨月） | `GET /api/transactions/group?month=` | 切月懒加载该月数据 |
| 详情删除 | `DELETE /api/transactions/<id>` | 捕获阶段先删后端，再本地刷新 |
| 统计 / 报表 | 基于已加载 `tx` | 数据源真实后自动生效 |

- **对接方式**：通过覆盖 `app.js` 的全局函数 + 捕获阶段监听器实现，**不改动渲染逻辑**；删除 `index.html` 里的 `<script src="api.js">` 即可还原为纯演示模式。
- **优雅降级**：后端未启动时自动回退到内存假数据（`INITIAL_TX`），前端照常演示。
- **CORS**：后端已加 `Access-Control-Allow-Origin: *`，前端 8088 静态页可直接 fetch。
- **注意事项**：`app.js` 顶部有几个写死的日期（如「今天」2026-08-18、月份选择 2026-08），属原型遗留硬编码，不影响真实数据展示。

## 复刻的页面与交互（对照简约记账）

| 页面 | 简约记账源布局 | 复刻要点 |
|------|-----------|---------|
| 明细（首页） | MainActivity (res_nK) | 靛蓝头 + 月份下拉 + 「本月支出」36sp 加粗大数字 + 收入/结余 + 日期分组账单列表 + 右下 FAB |
| 记账页 | NewAccountActivity (res_B8) | 「支出/收入」Tab + 14 类型网格 + 备注行 + 金额（红#cc0000）+ 今天/图片 + 计算器键盘（7 8 9 ⌫ / 4 5 6 ＋ / 1 2 3 － / 再记 0 . 完成） |
| 统计页 | AccountTypeStatisticActivity (res_kI1) | 支出/收入 Tab + 周/月/年 + 趋势柱状图(160dp) + 环形图(210dp) + 明细占比列表 |
| 日历页 | CalenderActivity (res_7V) | 月历（选中蓝 #108cd4、今天靛蓝）+ 账单绿点标记 + 当日账单列表 |
| 搜索页 | SearchActivity (res_92) | 账单/类别 Tab + 搜索框 + 搜索按钮 + 按时间/按金额排序 |
| 年度统计 | MonthStatisticActivity (res_4E) | 年度结余/收入/支出卡片 + 月份收支列表 |
| 我的 | ProfileActivity + res_tZ | 头像 + 昵称/会员状态 + 开通会员/云备份/类别管理/选项设置/记账提醒/导出/指纹/手势/主题/关于 |
| 管理账本 | ManageBooksActivity (res_0Y) | 账本列表（可勾选）+ 合并/取消 |
| 编辑账本 | EditBookActivity (res_Ms) | 账本名称/账本类型表单 + 保存 |
| 类别管理 | ManageAccountTypesActivity (res_sJ) | 支出/收入 Tab + 类别列表 + 导入/新增类别 |
| 新增类别 | NewAccountTypeActivity (res_bD) | 选择图标 + 类别名称 + 保存 |
| 会员 | PurchaseActivity (res_16) | 会员宣传页 |

## 关于加固
APK 的 `classes.dex` 为**梆梆加固壳**（MyWrapperProxyApplication + assets/t86 系列 libshellx），真实业务 dex 加密于 `assets/0OO00l111l1l`（3MB），需动态脱壳才能还原操作逻辑；本原型的交互逻辑依据 47 个解码布局 + 字符串资源推断实现。

## 关键规格（修改时参照）

### 颜色（从 colors.xml 提取）
| 用途 | 值 | 变量名 |
|------|-----|--------|
| 主色 | `#303f9f` | `--primary`（colorPrimary） |
| 页面背景 | `#eeeeee` | `--bg`（lighteclr） |
| 卡片白 | `#ffffff` | `--card` |
| 支出红 | `#cc0000` | `--expense`（记账页金额） |
| 主文字 | `#444444` | `--ink-main`（dark4） |
| 次文字 | `#666666` | `--ink-sub`（dark6） |
| 弱文字 | `#888888` / `#999999` | `--ink-muted` / `--ink-faint` |
| 分隔线 | `rgba(0,0,0,.09)` | `--sep`（sepcolor #18000000） |

### 字号（sp，约等于 px）
大金额 36 / 收入结余 21 / 列表类型 16 / 列表备注 14 / 列表金额 16 / Tab 13 / 计算器数字 19 / 金额输入 24 / 备注 15.5

### 尺寸（dp）
顶栏 50 / 概览区 140 / 列表项 min 60 / FAB 56 / 键盘每格 50 / 底部 Tab 58 / 统计趋势 150-160 / 饼图 210

## 已实现交互
- 底部 Tab 四页切换（明细/统计/图片/我的）
- FAB → 记账页 → 点类型 → 展开计算器 → 数字/小数点/删除/±切换收支 → 完成（记一笔并退出）/ 再记（连续记账）
- 金额支出显示红色、收入显示靛蓝
- 统计页周/月/年切换 + 环形图 + 明细

## 待替换
- 图标目前用 emoji/符号占位（简约记账原版是矢量 drawable，无法直接复用），后续换成统一 SVG
- ~~账单数据是 JS 里的假数据~~ ✅ 已通过 `api.js` 接入 Flask 后端真实数据（Phase 1 完成）
