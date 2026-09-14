---
"loo0ng-skills": patch
---

仓库布局改成严格照上游 mattpocock/skills 分桶（无票，ADR-0009 的 2026-09-13 附注）：七件 skill 从 `skills/<name>/` 搬进 `skills/productivity/<name>/`，另建 engineering、misc、in-progress、deprecated 四个空桶各带 `README.md`，`skills/README.md` 删除；根 `README.md` 与桶 `README.md` 的条目把名字链接到 `SKILL.md`；每件新增一页 `docs/productivity/<name>.md`。`.claude-plugin/plugin.json` 的七条路径跟着改，`.codex-plugin/plugin.json` 不变。`gen-openai-yaml.py` 递归找 `SKILL.md`，`pack-offline.py` 按 plugin.json 里的路径取目录、包内仍平铺 `skills/<name>/`，`link-skills.ps1` 照上游跳过 `deprecated/` 与 `misc/`，`privacy-check.py` 守的领域图前缀改为新路径。skill 名、入口、装到律师机上的形状都没变。
