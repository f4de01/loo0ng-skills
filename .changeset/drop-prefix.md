---
"loo0ng-skills": minor
---

**Breaking:** 六件 skill 去掉 `loo0ng-` 前缀，改名为 `setup-case`、`doit`、`graph`、`domain`、`filing`、`to-docx`；路由仍叫 `ask-loo0ng`。打法随之变短：Claude Code 里 `/doit 出一版 …`，Codex 里 `$doit 出一版 …`（插件路线装的带 `loo0ng-skills:` 前缀，补全按子串命中）。没有别名：装了旧名的机器请卸掉旧的七件，按 README 重装；已起手的案件工作区里 `AGENTS.md` 指针块记的入口名要照新名改一次，图与文书都不受影响。

仓库布局同时按上游的桶义修正：办案主线六件从 `skills/productivity/` 搬进 `skills/engineering/`，`to-docx` 留在 `productivity/`（ADR-0009 附注「分桶修正」）。装到机器上的形状不受桶影响。
