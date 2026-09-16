# 发布与分发

准备 changeset、发布版本、选择安装路线或验证开发分支时读本篇。发布前检查见 [testing.md](./testing.md)，登记步骤见 [registration.md](./registration.md)。文中代码路径均相对仓库根目录。

## 发布

改名、改功能都是一次发布，只在开发者维护时做（ADR-0009）。发布链照上游（ADR-0021）：

1. 每次会让律师感知的修改，写一张 changeset（`npm run changeset`，或手写 `.changeset/<slug>.md`：frontmatter 是 `"loo0ng-skills": patch|minor`，正文是给律师看的一段话，会原样进 `CHANGELOG.md`）。改文档、脚本、测试不写。
2. 推到 `main`。`.github/workflows/release.yml` 里的 changesets/action 发现有待消费的 changeset，跑 `npm run version`（`changeset version` 结算版本与 `CHANGELOG.md`，再 `node scripts/sync-plugin-version.mjs` 把版本抄进 `.claude-plugin/plugin.json`），开一个 "chore: version skills" 的 PR；后续再进 changeset 它自动更新。
3. 读那个 PR 的 diff（就是 CHANGELOG 的预览），顺了就合并。合并后 action 再跑一次，这次没有 changeset 了，执行 `npx changeset tag` 打出 `v<version>`。
4. `plugin.json` 的 version 变了，装了插件的机器才会收到更新；skills.sh 路线要律师自己 `npx skills update`。

级别照上游用法：patch 是修 bug、措辞、单件行为微调；minor 是新增或毕业 skill、改名（正文以 **Breaking:** 开头，说明无别名需重装）；major 上游没用过。

本地也能跑同一条链（`npm run version` → 提交 → `npx changeset tag`），但 CI 是常态。仓库设置里 Actions 的 "Allow GitHub Actions to create and approve pull requests" 必须勾上，否则开不了 PR。

上 CI 的只有发布这一条路：ADR-0015 的 2026-09-12 附注把「全部本地不做 CI」的射程划回测试那一层，脚本层单测、两侧 eval 仍然全部本地跑。离线兜底包不再随 Release 附带（ADR-0021）；要给断网的律师机装，直接拷 `skills/engineering/` 下的六个目录与 `skills/productivity/to-docx/`。

## 分发事实（#18，2026-09-05 实测）

- **开发机两条路各 harness 择一，不同装**（照上游 install-block「The two routes are exclusive」；2026-09-14 去前缀后定）：Claude Code 侧装插件（`loo0ng-skills:<name>`，`/loo` 加 tab 聚齐七件），Codex 侧要用就走 skills.sh（裸名，与律师机同形；2026-09-14 起开发机暂不装，`~/.agents/skills/` 里不留 junction）。`link-skills.ps1` 是维护者的开发脚本，见到已装插件就只挂 Codex 那个目录；Codex 侧装了 skills.sh 的拷贝就别再跑它。裸名去了 `loo0ng-` 前缀之后，junction 路线在 Claude Code 列表里与四十多件别的 skill 混在一起、tab 补不出来，插件命名空间顶替了原来 name 里的前缀。
- junction 路线：两个 harness 都扫到；Claude Code 会话内热加载；Codex 显示裸名 `<name>`（仓库不再带 `.codex-plugin/plugin.json`，ADR-0021）。
- 插件路线：`claude plugin marketplace add` 与 `codex plugin marketplace add … --ref` 对私有仓库都吃本机凭据，缓存是整仓库拷贝。**这条只在开发机上成立**，别当分发口径，见下面「安装源必须是公开仓库」。
- 本机验证插件路线不必推分支：`claude plugin marketplace add <本仓库绝对路径>` 再 `claude plugin install loo0ng-skills@loo0ng-marketplace`，`claude -p "/loo0ng-skills:<name>"` 可触发；验完 `claude plugin uninstall` 与 `claude plugin marketplace remove loo0ng-marketplace`（#24）。
- skills.sh：`npx skills@latest add owner/repo` 只取默认分支，分支名含 `/` 时解析失败。
- junction 与插件同装时 Codex 清单同名两条、不合并；Claude Code 靠 `plugin:` 前缀分开。

## 安装源必须是公开仓库（#94，2026-09-09 律师机现场）

私有仓库在律师那台 mac 上一条安装路都没走通，最后是把本仓库转成 public 才装上的（`docs/实测/mac-20260909/结论.md`）。上面分发事实里那条「对私有仓库都吃本机凭据」只在开发机上验过，**不是分发面的口径**，别拿它去现场。

这是一条约束，不是一处笔误：它把将来任何「把主仓库转私有」的设想框住了。真要藏开发内容，就得拆出一个公开的分发仓库，而那要付三样代价：

1. **两仓同步**：`skills/` 与两份插件清单得有一条机械的搬运，人手搬迟早漏。
2. **登记不变量跨仓库**：`AGENTS.md` 结构不变量 1 的几处登记（`skills/<bucket>/<name>/`、桶 README、`.claude-plugin/plugin.json`、根 `README.md`、docs 页）会落在两个仓库里，[校验与测试](./testing.md) 中的命令不再是在一个工作副本上跑得完的。
3. **入口显示名可能从裸名变成带前缀**：Codex 显示裸名还是 `loo0ng-skills:<名>`，取决于装到 `~/.agents/skills/` 的那个目录上面找不找得到一份 Codex 插件清单（本仓库已不带，ADR-0021）（`docs/交付/现场清单.md` 1.5 的实测）。律师那台机器走的是路 A，直接拷目录，现在看见的是**裸名**；拆出分发仓库之后若改走那个仓库的插件市场装，同一件 skill 就显示成 `loo0ng-skills:<名>`，`ask-loo0ng` 的入口表、打法段与教律师打的那一串跟着都要改。
