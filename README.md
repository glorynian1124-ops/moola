# Moola · 简约记账（APK 复刻）

对 Android 应用「简约记账」（com.yhqx.account v1.8.9）的逆向分析与高保真 Web 复刻项目。

## 目录结构

```
├── prototype/           简约记账 Web 复刻前端（index.html / style.css / app.js / assets/）
│   ├── assets/          APK 提取的图标（白色 PNG，CSS mask 上色）与 DINCond 金额字体
│   └── index.html       33 个页面 + 约 20 个弹窗/底部面板
├── apk_analysis/        APK 逆向分析脚本（androguard）与产物
│   ├── step1_basic.py … step18_moreicons.py   逐步分析脚本
│   └── output/          分析结果（Manifest、资源映射、图标、布局蓝本等）
├── app/                 应用代码（模型 / 分析器 / 数据解析 / Web 服务）
├── data/                示例数据
├── main.py              入口
└── config.yaml          配置
```

## 运行前端复刻

直接用浏览器打开 `prototype/index.html` 即可（纯静态页面，无需构建）。

> 提示：`assets/icons/*.png` 为白色透明图标，页面通过 CSS `mask` 着色显示。

## 环境

- APK 分析需 Python 3 + `androguard`、`Pillow`（见 `requirements.txt`）
- 虚拟环境已加入 `.gitignore`，请勿提交

## 协作

- 分支：`main`
- 提交前请确保 `prototype/` 页面在浏览器中无 JS 报错
