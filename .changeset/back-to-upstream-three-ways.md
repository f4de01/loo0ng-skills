---
"loo0ng-skills": minor
---

三处回归上游 mattpocock/skills 的做法，仓库迁到 `f4de01/loo0ng-skills`（ADR-0021）：

- **发布链**改为 changesets/action：push 到 main 自动开 "chore: version skills" PR，合并即打 tag。`release.py`、`pack-offline.py` 与干跑流程删除，Release 不再附离线兜底包。
- **不再发 Codex 原生插件**：`.codex-plugin/` 删除。Codex 用户改用 `npx skills@latest add f4de01/loo0ng-skills`；skill 在 Codex 里显示为裸名。
- **`agents/openai.yaml` 改为手写**：frontmatter 去掉 `metadata` 块，`gen-openai-yaml.py` 删除。skill 名、入口、正文都没有变。

**Breaking:** 安装源换了仓库。请卸掉从 `lawyer-workbench-v3` 装的那份，按 README 从新仓库重装。
