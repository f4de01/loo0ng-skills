---
"loo0ng-skills": patch
---

七件 skill 搬回它们的正式位置：办案主线六件（`setup-case`、`doit`、`ask-loo0ng`、`graph`、`domain`、`filing`）在 `skills/engineering/`，离了案子也能单独用的 `to-docx` 在 `skills/productivity/`。

**插件路线重新装得到东西**：`/plugin install loo0ng-skills@loo0ng-marketplace` 之后七件齐活、彼此调得通，不再是一个空包。装了插件的机器 `claude plugin update` 一次就收到整套。用 `npx skills@latest add f4de01/loo0ng-skills -a codex -a claude-code` 的照旧，一条命令装到两个 harness。

**你的打法一个字不变**：`/setup-case`、`/doit`、`/ask-loo0ng` 三个入口的名字与跟在后面的那句话都照旧，另外四件仍然是说一句话就到。已经起手的案件工作区不受任何影响——图、两份视图、文书、归档索引一字不动。

七页面向人的说明（`docs/engineering/*.md` 与 `docs/productivity/to-docx.md`）照重做后的工作流全新写过：预设图两处两归属、差量填模板、留黄与重出、审查报告降为留痕，旧页描述的那一套已经不在了。
