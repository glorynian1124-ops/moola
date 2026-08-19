# Moola · Git 协作规范

> 适用对象：glorynian1124-ops（你） 与 suran6688aa-maker（协作者）
> 仓库：https://github.com/glorynian1124-ops/moola（私有）
> 分支策略：GitHub Flow 简化版（main + dev + feature 分支）

---

## 0. 核心理念（先读这段）

- **main 永远是"可运行的稳定版"**，任何人都不得直接往 main 推代码。
- 所有开发都在 `dev`（共用）或功能分支上做，确认没问题再合入 `main`。
- 每天开工前先 `git pull`，完工后及时 `git push`——**别攒改动**。
- 冲突不可怕，git 不会丢代码；遇到解决不了就找 AI（Copilot）帮忙。

---

## 1. 分支模型

```
main   ───────────────────────────────────── 稳定版（可运行、随时可展示）
   │
dev    ────────●────────●────────●──────── 共用开发线（两人都在这里合并日常改动）
   │        /         /        /
   └ feature/xxx ─────┘        ┘          功能分支（个人开发，开 PR 合入 dev）
```

| 分支 | 用途 | 谁能推 | 说明 |
|---|---|---|---|
| `main` | 稳定可运行版本 | 仅经 PR 审核后合入 | 直接 push 被禁止 |
| `dev` | 共用开发线 | 两人都可 push | 日常合并到此，保持基本可用 |
| `feature/xxx` | 单个功能/任务 | 各自创建 | 命名见下方，完成后 PR 合并到 dev |

---

## 2. 分支命名规范

```
feature/<功能名或任务名>
fix/<问题简述>
docs/<文档说明>
refactor/<重构说明>
```

示例：
- `feature/pie-chart-labels`（饼图标注）
- `feature/export-csv`（导出 CSV）
- `fix/month-bar-ticks`（修复月视图刻度）
- `docs/readme-update`

**小功能**（半小时内能完成的）也可以直接在一个 `dev` 上做，不必开分支。
**中大型改动**（涉及多文件、多人同时用到的文件）务必开 `feature/` 分支。

---

## 3. 提交信息规范（Conventional Commits）

格式：
```
<type>(<scope>): <简短描述>

<可选：详细说明>
```

| type | 含义 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `docs` | 只改文档 |
| `style` | 格式、样式（不影响逻辑） |
| `refactor` | 重构（不改功能） |
| `perf` | 性能优化 |
| `chore` | 杂项（依赖、配置等） |

示例：
```
feat(stat): 饼图新增彩色延伸线标注

- 每块扇区外沿延伸线 + 水平折线
- 占比 <2% 不显示标注
- 支持手指旋转
```

**要点**：
- 描述用中文，动词开头，简洁（≤50 字）
- 一个提交只做一件事；别把"加功能 + 改样式 + 删文件"混在一个提交里
- 如果改了 `prototype/` 前端，尽量在提交里说明"浏览器已自测无 JS 报错"

---

## 4. 日常工作流程

### 4.1 开工（每天第一次）
```bash
git checkout dev
git pull                        # 拉取别人今天的新改动
git checkout -b feature/my-task # 需要时开功能分支
```

### 4.2 做完一小步
```bash
git status                      # 看改了哪些
git add <具体文件>              # 只 add 本次要提交的文件，别用 git add -A 无脑全加
git commit -m "feat(...): ..."
```

### 4.3 中途同步（防冲突的关键）
```bash
# 在 feature 分支上，把 dev 的最新改动合进来（保持分支不过期）
git pull origin dev
```

### 4.4 收工推送
```bash
git push origin feature/my-task
# 然后在 GitHub 上开 PR：feature/my-task → dev
```

### 4.5 合入 main（稳定版）
main 已开启**分支保护**：不能直接 push，必须走 PR。
```bash
# 方式 A（推荐，走 PR）：
git checkout dev && git pull origin dev      # 确认 dev 是最新的可运行版本
git push origin dev
# 在 GitHub 上开 PR：dev → main，描述写明自测结果，合并
```

> 若你俩都信任彼此且想省事，也可以保留本地合并：
> ```bash
> git checkout main && git pull origin main
> git merge dev
> git push origin main      # 需要 main 保护规则允许 bypass 时才行
> ```

---

## 5. 前后端分工（边界必须遵守）

**前后端彻底分家**，各自负责自己的目录，互不越界：

| 端 | 目录 | 负责人 |
|---|---|---|
| **前端** | `prototype/`（index.html / style.css / app.js / assets/） | **glorynian1124-ops**（你） |
| **后端** | `app/`、`apk_analysis/`、`data/`、`main.py`、`config.yaml` | **suran6688aa-maker**（朋友） |

规则：
1. **前端任务只动 `prototype/`，后端任务只动后端目录**，不越界。
2. 需要同时动前后端的改动（如数据字段变化）：先在 issue / 群里说明，各自在自己的职责范围内改。
3. 前端与后端通过**数据格式约定**衔接；`prototype/` 内示例数据格式以后端输出为准，改动前先与后端确认。
4. 两人都想改的文件（边界文件）：`requirements.txt`（依赖）、`README.md`、`GIT_GUIDE.md`、`AGENTS.md` —— 先打招呼再改。

> 这样你俩几乎永远不会"左脚踩右脚"：你改前端，他改后端，git 自动合并互不冲突。

---

## 6. 冲突处理

### 6.1 冲突长什么样
`git pull` 报 `CONFLICT`，文件里会出现：
```
<<<<<<< HEAD
你的代码
=======
对方的代码
>>>>>>> feature/other
```

### 6.2 解决步骤
```bash
git status                              # 看哪些文件冲突
# 打开冲突文件，手动保留正确的部分，删掉 <<<<<<< ======= >>>>>>>
git add <已解决的文件>
git commit -m "merge: 解决 xxx 冲突"
```

**解决不了就找 AI**（Copilot）：把冲突文件内容贴给我，我帮你合并。

### 6.3 重要提醒
- **不要用 `git checkout -- .` 或 `git reset --hard` 粗暴丢弃**，除非你确定不要对方或自己的改动
- 冲突是正常现象，证明两人都在推进，别慌

---

## 7. .gitignore 红线（已配置）

以下内容**绝不提交**（仓库已配置 `.gitignore`）：
- 虚拟环境：`.apk-venv/`、`.venv/`、`.venv-1/`（约 240MB）
- Python 缓存：`__pycache__/`、`*.pyc`
- IDE：`.vscode/`、`.idea/`
- 系统文件：`.DS_Store`、`Thumbs.db`

**如果误 add 了大文件**：
```bash
git rm -r --cached .apk-venv   # 从跟踪中移除（保留本地文件）
git commit -m "chore: 移除误提交的虚拟环境"
```

---

## 8. 命令速查表

| 操作 | 命令 |
|---|---|
| 看状态 | `git status` |
| 看改了什么 | `git diff` |
| 暂存单个文件 | `git add 文件名` |
| 提交 | `git commit -m "feat(...): 描述"` |
| 拉取最新 | `git pull origin dev` |
| 推送 | `git push origin 分支名` |
| 开新分支 | `git checkout -b feature/xxx` |
| 切分支 | `git checkout dev` |
| 合并 dev 到当前 | `git pull origin dev` |
| 看历史 | `git log --oneline -10` |
| 看当前分支 | `git branch -a` |

---

## 9. 推荐节奏（每轮任务）

1. **开工**：`git checkout dev && git pull` → 开 `feature/xxx`
2. **开发**：小步提交（一个功能一个 commit）
3. **同步**：中途 `git pull origin dev` 防冲突
4. **收工**：`git push` → GitHub 开 PR 到 `dev`
5. **稳定**：确认可运行后，由负责人在本地合并 `dev → main` 并推送
6. **善后**：合并后删除已完成的 feature 分支

---

## 10. 其他约定

- **PR 描述**：写清"改了什么 / 为什么 / 怎么测"，让搭档一眼看懂。
- **别 push 到别人的 feature 分支**：除非对方要求。
- **main 被锁**：不直接 push main；实在需要，先用 `git push origin main --force`？——**禁止 force push 到 main**。
- **出现疑问先 `git status` 看状态**，别乱敲命令。
