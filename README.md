# 律师工作台 3.0

给破产管理人律师用的法律工作台，以 skill 形态交付，装进 Claude Code 或 Codex 就能用。

一个案子在一台机器上的一个目录里长出来：材料、指南、模板、出好的文书都在这个目录里，工作台另用一张**图**记着这个案子有哪些节点、各自走到了哪一步。律师不背流程、不填表格，一句自由文本说要办哪件事就行。

## 装了能干什么

三件事，三句话。下面写的是律师实际打出去的那一串：Claude Code 里 `/名 …`，Codex 里 `$名 …`；装法不同，名字前面可能多一段 `loo0ng-skills:`，见下面的安装段。

**起手一个案子**：在一个空目录里打 `/setup-case`，一案一次。它把案件工作区的目录建起来，这个案子的图三选一（空图、整份「破产」领域图的 12 模块 72 节点、或开发者交付的定制图）；你起手前放好的本案指引它整读一遍，末尾给你一张清单，你说一句话拍板才作数。

**出一版文书**：新到的材料丢进 `收件箱/`，打 `/doit 出一版 裁定确认无异议债权的申请`。一个对话办一份文书：它先把收件箱里的东西各归各位，再读这个案子的材料、指南、空白模板与你过往的文书，照该节点的官方模板出一份 DOCX，缺的槽与没把握的句子标黄，附一份审查报告（写明生成依据、存疑之处、要你裁定的地方）。你在 WPS 里看完说一句「确认」，这一份就完成了。反过来也行：文书你自己写好了，交给它登记。

**问接下来做什么**：`/ask-loo0ng`。一张只读的地图，随时可以问，也可以一直不问。它答你现在在哪、上一件完成的是什么、下一件该办哪个，给出往下的路与每一步的拍板点，最后把你下一句该打的那一串整个写出来。它自己不动任何东西。

你的案件材料只在你自己的机器上：工作台读写的是案件工作区那个目录，本仓库不收任何案件材料。

## 安装

两条路二选一：插件是只读的整包订阅，skills.sh 把 skill 文件拷进你的项目由你改。两条都装，每件 skill 会出现两次。

<details>
<summary><strong>Claude Code：插件</strong></summary>

本仓库自成单插件市场（`.claude-plugin/marketplace.json`），在会话里：

```
/plugin marketplace add f4de01/loo0ng-skills
/plugin install loo0ng-skills@loo0ng-marketplace
```

`owner/repo` 形式只取默认分支；要装某个分支，用 `https://github.com/f4de01/loo0ng-skills.git#<branch>`。**安装源须是公开仓库**：「私有仓库凭本机 gh 或 git 凭据克隆」只在开发机上验过，律师那台 mac 上私有仓库一条都没走通，本仓库为此转成了 public（`docs/实测/mac-20260909/结论.md`）。装上后 skill 名带 `loo0ng-skills:` 前缀，例如 `/loo0ng-skills:ask-loo0ng`。**改造期间（ADR-0022）插件清单为空**：七件都在 `in-progress/`，这条路装到的是空包，请走下面 skills.sh 单件装，或留在 0.4.0。

</details>

<details>
<summary><strong>Codex 及其他 agent：skills.sh</strong></summary>

```bash
npx skills@latest add f4de01/loo0ng-skills -a codex -a claude-code
```

**安装源同样须是公开仓库**：律师那台 mac 上这一条对私有仓库失败过三次，转 public 之后才装上（`docs/实测/mac-20260909/结论.md`）。安装器让你挑 skill 与目标 agent；`-a` 可重复，一次装到两个 harness。

</details>

<details>
<summary><strong>开发者本机：junction</strong></summary>

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1
```

维护者的开发脚本，照上游 `link-skills.sh`，不是安装路线：把 `skills/<bucket>/<name>/` 逐条以 junction 挂到 `~/.claude/skills/` 与 `~/.agents/skills/`，顺手设 `core.hooksPath` 启用隐私钩子。开发机照上游「一个 harness 只装一条路」：Claude Code 侧装了本插件就不挂 `~/.claude/skills/`（脚本自己判断），那一侧用 `claude plugin update loo0ng-skills@loo0ng-marketplace` 更新，skill 名带 `loo0ng-skills:` 命名空间；Codex 侧要用就走上面的 skills.sh，装了它就别再挂 junction。只在改名、增删 skill 后重跑。

</details>

## Skill 清单

七件 skill 目前全部住 `skills/in-progress/`，逐件重做、改完一件毕业一件（ADR-0022）；名单与分工见 [skills/in-progress/README.md](./skills/in-progress/README.md)。毕业后的归属照上游分桶：办案主线六件住 `skills/engineering/`，离了案子也能单独用的 `to-docx` 住 `skills/productivity/`（各桶的清单在 `skills/<bucket>/README.md`），每件另有一页面向人的说明 `docs/<bucket>/<name>.md`。

按谁能触发分两组。**User-invoked** 三件（`setup-case`、`doit`、`ask-loo0ng`）律师打名字触发：Claude Code 里是 `/名 …`，Codex 里是 `$名 …`，只做编排，模型不会自己调用。**Model-invoked** 四件（`graph`、`domain`、`filing`、`to-docx`）由模型够到，律师无需记名。

## 给开发者

七件 skill 在 Claude Code 与 Codex 两个 harness 上都能触发。

硬边界两条写在 `AGENTS.md`：案件材料永不进本仓库，办案会话对本仓库只读。词汇以 `CONTEXT.md` 为准，决策记在 `docs/adr/`，结构不变量与长约定在 `AGENTS.md` 与 `docs/agents/`。

### 维护

登记步骤、校验命令与测试命令见 `docs/agents/skills.md`。发布链照上游 mattpocock/skills：每次修改写一张 changeset，推到 `main` 后 `.github/workflows/release.yml` 里的 changesets/action 自动开一个 "chore: version skills" 的 PR，合并即打 tag；`package.json` 的版本由 `scripts/sync-plugin-version.mjs` 抄进 `.claude-plugin/plugin.json`，版本记录在 `CHANGELOG.md`。测试与 eval 仍然全部本地跑（ADR-0015 2026-09-12 附注）。

发完一版要装到律师那台机器上时，照 `docs/交付/现场清单.md` 现场做，结果填 `docs/交付/记录表.md`：那是开发者本人在那台机器前的四段（装、跑得动转换器的环境、起手一个案子、跑通一个节点），断网可用。

## 许可

代码与文档按 [MIT](LICENSE) 授权。`skills/<bucket>/domain/assets/<领域>/` 下的官方模板原件与指引手册原文是第三方文件，不在 MIT 的覆盖范围内，各依其自身来源的条款：范围说明在 `LICENSE` 末尾。
