# Moola 项目 · AI 代理协作纪律（Agent Guidelines）

> 本文件会被 AI 编码代理（Copilot、Claude Code 等）自动读取。**任何被要求在仓库中改代码的 agent 都必须先理解并遵守本规范。**
> 仓库：glorynian1124-ops/moola（私有）｜协作者：glorynian1124-ops、suran6688aa-maker

---

## 1. 项目简介

「简约记账」APK 的逆向分析与高保真 Web 复刻。

- `prototype/` —— 前端复刻（`index.html` / `style.css` / `app.js` + `assets/`），**纯静态，直接用浏览器打开即可运行**。
- `apk_analysis/` —— APK 逆向分析脚本（androguard）与产物。
- `app/` —— 后端应用代码（模型 / 分析器 / 数据解析 / Web 服务）。
- `data/`、`main.py`、`config.yaml`、`requirements.txt` —— 数据与入口。
- `GIT_GUIDE.md` —— 人类协作规范；`AGENTS.md`（本文件）是给 agent 的可执行版本。

---

## 2. Git 分支纪律（必须遵守）

**分支模型：双分支（GitHub Flow 简化版）**

| 分支 | 含义 | 规则 |
|---|---|---|
| `main` | 稳定可运行版 | **禁止 agent 直接 push**；只能通过 PR 合入 |
| `dev` | 共用开发线 | 日常改动、功能合入都进这里 |
| `feature/xxx` | 功能/任务分支 | 从 `dev` 开出，完成后 PR → `dev` |

**Agent 开工前**：
1. `git checkout dev && git pull origin dev` —— 永远基于最新的 dev 开发。
2. 需要较大改动时创建 `feature/<name>` 分支，不要直接改 dev 上的公共文件。
3. **绝对不要** `git push` 到 `main`，也不要 `--force` 推送任何分支（除非用户明确要求且确认安全）。

---

## 3. 提交规范（必须遵守）

格式：`<type>(<scope>): <中文描述>`

- `feat` 新功能 / `fix` 修复 / `docs` 文档 / `style` 样式 / `refactor` 重构 / `perf` 性能 / `chore` 杂项

示例：`feat(stat): 饼图新增彩色延伸线标注`

规则：
- 描述用中文、动词开头、≤50 字。
- **一个提交只做一件事**；不要混合"功能 + 样式 + 删文件"。
- 改完 `prototype/` 后，若执行了浏览器验证，在提交说明里写明"浏览器已自测"。

---

## 4. 工作流程（agent 执行顺序）

1. `git status` 先看工作区状态，**永远不要覆盖他人未推送的改动**。
2. 改代码前确认当前分支（`git branch --show-current`）；若不在 dev/feature 上，先切走。
3. 只 `git add` 与本次任务相关的文件，**禁止无脑 `git add -A`**。
4. `git commit -m "<type>(<scope>): 描述"`。
5. 中途 `git pull origin dev`（在 feature 分支上把 dev 最新合入）防冲突。
6. 收工 `git push origin <当前分支>`，并在需要时提示用户开 PR（feature → dev，或 dev → main）。
7. 遇到冲突：手动保留双方正确内容，删除 `<<<<<<<` / `=======` / `>>>>>>>` 标记后再提交。**禁止 `git reset --hard` / `git checkout -- .` 粗暴丢弃。**

---

## 5. 文件分工（避免冲突）

- **glorynian1124-ops** 优先：`prototype/`（index.html / style.css / app.js）。
- **suran6688aa-maker** 优先：`app/`、`apk_analysis/`、`data/`、`main.py`。
- 高风险同改文件：`prototype/index.html`、`prototype/style.css`、`prototype/app.js`、`requirements.txt`。**同一文件同一区域，同一时间只允许一方修改。**

---

## 6. 红线（禁止）

- ❌ push 到 `main`（除非通过 PR 机制）。
- ❌ `git push --force` 到共享分支。
- ❌ 提交虚拟环境 `.apk-venv/` `.venv/` `.venv-1/`、`__pycache__/`、`.vscode/`。
- ❌ 用 `git reset --hard` / `git rm` 等方式丢弃他人改动。
- ❌ 大范围 `git add -A` 把无关文件带入提交。
- ✅ 不确定时先 `git status` / `git log` 查看，或询问用户。

---

## 7. 前端验证约定

改 `prototype/` 时，若环境支持，请尽量在浏览器（或等价工具）中验证：
- 页面无 JS 报错（`get_errors` / 浏览器控制台）。
- 新增/修改的交互可正常触发。

---

*本规范为项目级指令，随仓库同步到所有协作者。改动规范文件（AGENTS.md / GIT_GUIDE.md）需经用户确认后再提交。*
