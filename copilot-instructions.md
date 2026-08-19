# VS Code Copilot 项目指令

本仓库的 AI 协作纪律位于 **`AGENTS.md`**（通用，推荐优先阅读）与 **`GIT_GUIDE.md`**（人类版）。

请在仓库中执行任何代码改动前，**阅读并遵守 `AGENTS.md` 的 Git 纪律**，重点：

1. **分支**：基于 `dev` 开发，不直接 push `main`，较大改动开 `feature/<name>`。
2. **提交**：遵循 Conventional Commits，中文描述，一个提交一件事，禁止无脑 `git add -A`。
3. **流程**：开工先 `git pull origin dev`；收工 `git push origin <分支>` 并提示是否开 PR。
4. **红线**：禁止 force push 共享分支、禁止 `git reset --hard` 丢弃他人改动、禁止提交虚拟环境/缓存。
5. **冲突**：手动解决后提交，不粗暴回退。

详见 @AGENTS.md。
