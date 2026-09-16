# 三处回归上游：发布链换成 changesets/action，不发 Codex 原生插件，openai.yaml 手写；仓库迁到 loo0ng-skills

3.0 照 Matt Pocock 的 skill 体系搭，但在三处有意偏离了上游，各有当时的理由：`workflow_dispatch` 干跑加 `scripts/release.py` 两道闸加离线兜底包的发布链（#96，ADR-0015 附注）；`.codex-plugin/plugin.json` 单一路径递归扫描（#18）；frontmatter 的 `metadata` 块加 `scripts/gen-openai-yaml.py` 生成器（#26、#29）。2026-09-13 决定三处全部回归上游，以"和上游同构"为唯一标准，减少维护面。

## Decision

- **发布链**：`.github/workflows/release.yml` 原样用上游的 changesets/action：push 到 `main` 自动开 "chore: version skills" PR，合并即 `npx changeset tag`。`scripts/release.py`、`scripts/pack-offline.py`、`scripts/sync-plugin-version.py` 与各自的 `tests/` 删除；`scripts/sync-plugin-version.mjs` 从上游原样抄，只同步 `.claude-plugin/plugin.json`（`package-lock.json` 的版本不再同步，照上游）。`.changeset/config.json` 用 `@changesets/changelog-github`，CHANGELOG 带 PR 链接。离线兜底包不再随 Release 附带；要它时从 git 历史取回 `pack-offline.py` 单独跑。
- **不发 Codex 原生插件**：删 `.codex-plugin/`。理由与上游 ADR-0002 相同：Codex 清单只收单一路径，分桶后会把 `in-progress/` 一并装出去。Codex 用户走 skills.sh。Codex 里的显示名因此固定为裸名 `<name>`。
- **openai.yaml 手写**：删 `metadata` 块与生成器。`interface.display_name` 等于 `name`（#29 的实测仍成立，只是改由人守），`interface.short_description` 写中文。frontmatter 只用上游四个键。两端双旗一致由 `scripts/check-skill.sh` 守。
- **迁到新仓库 `f4de01/loo0ng-skills`**：完整 git 历史随行；`lawyer-workbench-v3` 原地保留，未关的 issue 在那边继续，关完再 archive。测试用户统一删掉旧版重装新版。

## Invariants this creates

- 仓库里没有第二份插件清单：分发清单只有 `.claude-plugin/plugin.json`。
- `agents/openai.yaml` 是源文件，不是生成物；`display_name` 与 `name` 相等由 `check-skill.sh` 守。
- 发版只有一条路：changeset → Version PR → 合并 → tag。没有手动干跑一说；想预览 CHANGELOG 就看 PR 的 diff。
- 四个检查脚本（`check-skill`、`check-wiring`、`check-stale`、`check-release`）随仓库走，`AGENTS.md` 结构不变量 6 要求提交前跑。

## Superseded

- ADR-0009 附注里"不发 Codex 插件 → 到那时再定"：现在定了。
- ADR-0015 2026-09-12 附注里描述的发布 workflow 形态。
- `.agents/registration.md` 与 `.agents/release.md` 里关于 `metadata`、生成器、`release.py`、`pack-offline.py`、`.codex-plugin` 的段落已同步改写。

## 2026-09-15 附注：对照上游后维持显示名等于调用名（#55）

已核对上游 `mattpocock/skills@959a8e9` 的 `skills/engineering/ask-matt/agents/openai.yaml`：`interface.display_name` 为 `"Ask Matt"`，采用人读名。本仓经裁定仍维持七件 skill 的 `display_name` 等于 `name`：律师按 `$doit` 等调用名找入口，显示名与调用名一致可少记一套对应关系；中文功能说明由 `short_description` 承担。这是对照上游之后保留的差异，七件 YAML 与现有命名约定不变。
