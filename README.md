# 律师工作台 3.0

给破产管理人律师用的法律工作台，以 skill 形态交付，装进 Claude Code 或 Codex 就能用。

一个案子在一台机器上的一个目录里长出来：材料、指南、模板、出好的文书都在这个目录里，工作台另用一张**图**记着这个案子有哪些节点、各自走到了哪一步。律师不背流程、不填表格，一句自由文本说要办哪件事就行。

## 装了能干什么

三件事，三句话。下面写的是律师实际打出去的那一串：Claude Code 里 `/名 …`，Codex 里 `$名 …`；装法不同，名字前面可能多一段 `loo0ng-skills:`，见下面的安装段。

**起手一个案子**：在一个空目录里打 `/setup-case`，一案一次。它把案件工作区的目录建起来，只问你一句：空图，还是用哪一份**预设图**起（随包出厂的与你自己存下的分两组列给你，选了就整份拷进来，连空白模板一起）。你起手前堆在目录里的东西一律当作待归档，末尾给你一张清单说每一件要归到哪，你说一句话拍板才搬。

**出一版文书**：新到的材料丢进 `待归档/`，打 `/doit 出一版 裁定确认无异议债权的申请`。一个对话办一份文书：它先把待归档里的东西各归各位，再读这个案子的材料、指南、空白模板与同模块里你已确认的文书，照该节点的官方模板**只写要改的那几处**，代码在模板原件上原地填、直接落盘。**填不了的槽与没把握的句子一律留黄**，收尾直接告诉你黄标在哪几处。黄色处你在 Word 里自己填最快，或者在对话里把事实给它、说一句重出。重出只动仍黄的地方与你点名的地方，你填过的一个字不碰。填完说一句「确认 <节点>」，哪个对话说都行。反过来也行：文书你自己写好了，交给它登记。

**问接下来做什么**：`/ask-loo0ng`。一张只读的地图，随时可以问，也可以一直不问。**第一行就是待拍板行**：哪几份文书黄色已清、还等你那一句确认，直接列出来。那是你最容易漏的一句。往下答你现在在哪、上一件完成的是什么、下一件该办哪个，给出往下的路与每一步的拍板点，最后把你下一句该打的那一串整个写出来。它自己不动任何东西。

你的案件材料只在你自己的机器上：工作台读写的是案件工作区那个目录，本仓库不收任何案件材料。

## 安装

<!-- install-block: route-choice；源：.agents/install-block.md -->
律师自行安装先走 skills.sh，下面按这个顺序列。开发者当前在 Claude Code 用插件，Codex 要用时走 skills.sh。**每个 agent 只选一条路线**，同一个 agent 两条都装，每件 skill 会出现两次；插件是只读的整包，skills.sh 安装的是可编辑的 skill 文件。
<!-- /install-block: route-choice -->

<details>
<summary><strong>律师安装首选：skills.sh（Codex、Claude Code 及其他 agent）</strong></summary>

<!-- install-block: skills-sh；源：.agents/install-block.md -->
律师那台 Mac 已走通的是公开仓库下的 skills.sh 安装；下面以 Codex 为例：

```bash
npx skills@latest add f4de01/loo0ng-skills -a codex
```

用 Claude Code 就把 `-a codex` 换成 `-a claude-code`；两边都用可同时指定，但已装本插件的 agent 不再用这条。安装器让你挑 skill 与安装范围。**安装源须是公开仓库**：现场私有仓库下失败三次，转 public 后装上，记录见[现场实测结论](https://github.com/f4de01/loo0ng-skills/blob/main/docs/实测/mac-20260909/结论.md)。这次成功是口述记录，没有保存本轮退出码与报错原文。
<!-- /install-block: skills-sh -->

</details>

<details>
<summary><strong>Claude Code 插件：需要整包安装时选（开发者当前用法）</strong></summary>

<!-- install-block: claude-plugin；源：.agents/install-block.md -->
本仓尚无官方市场上架入口，自建市场是当前提供的插件安装路线，因此保留给需要插件的用户。在 Claude Code 会话里：

```
/plugin marketplace add f4de01/loo0ng-skills
/plugin install loo0ng-skills@loo0ng-marketplace
```

装上后 skill 名带 `loo0ng-skills:` 前缀，例如 `/loo0ng-skills:ask-loo0ng`。开发机已验证这条路线；上述律师 Mac 的现场记录未验证公开仓库下的插件安装，不能把 skills.sh 的成功当作插件安装的证据。

`owner/repo` 形式只取默认分支；要装某个分支，用 `https://github.com/f4de01/loo0ng-skills.git#<branch>`。安装源同样须是公开仓库，私有仓库凭本机凭据安装仅在开发机上验过。
<!-- /install-block: claude-plugin -->

</details>

<details>
<summary><strong>开发者本机：junction</strong></summary>

<!-- install-block: local-junction；源：.agents/install-block.md -->
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1
```

维护者的开发脚本，照上游 `link-skills.sh`，不是安装路线：把 `skills/<bucket>/<name>/` 逐条以 junction 挂到 `~/.claude/skills/` 与 `~/.codex/skills/`（Codex 0.154 起的根；旧根 `~/.agents/skills/` 还在只提醒一句，不再往里挂），顺手设 `core.hooksPath` 启用隐私钩子。开发机照上游「一个 harness 只装一条路」：Claude Code 侧装了本插件就不挂 `~/.claude/skills/`（脚本自己判断），那一侧用 `claude plugin update loo0ng-skills@loo0ng-marketplace` 更新，skill 名带 `loo0ng-skills:` 命名空间；Codex 侧要用就走上面的 skills.sh，装了它就别再挂 junction。只在改名、增删 skill 后重跑。
<!-- /install-block: local-junction -->

</details>

## 桌面卡片（可选）

<!-- install-block: desktop-card；源：.agents/install-block.md -->
桌面卡片是另一个仓库的东西：一张常驻桌面的卡片，同时看住在办的多个案件，每案显示当前模块、进度、下一个要办的节点。它只读每个案件工作区的 `图视图.json`，一个字节都不写；装不装都不影响这里的七件 skill。

安装命令、它要的宿主、设置文件怎么写，都在它自己的 README：[loo0ng-widget](https://github.com/f4de01/loo0ng-widget)。

装过之后不用第二次配置：起手一个新案件时，`setup-case` 把这个案件的上级目录加进卡片的根目录列表（`~/.loo0ng/卡片设置.json`），卡片下一轮扫描就看得见它；已经在列表里就一个字不动，那份设置不在就整步不做。不想要这一步，起手时给 CLI 加 `--no-card`。

卡片只认当前的图格式。更早的版本起手、至今没被引擎重写过的工作区，它会列在「读不出」里：那种图没有升级路径，从预设图重新起手即可。
<!-- /install-block: desktop-card -->

## Skill 清单

七件，按桶列出，每件另有一页面向人的说明 `docs/<bucket>/<name>.md`。

### Engineering

办案主线的 skill，对应上游的「daily code work」：只在有 `图.json` 的案件工作区里工作的那些。

#### User-invoked

三件，律师打名字触发（Claude Code 里 `/名 …`，Codex 里 `$名 …`），只做编排，模型不会自己调用：

- **[setup-case](./skills/engineering/setup-case/SKILL.md)** 起手：把当前目录长成案件工作区，一案一次。[说明](./docs/engineering/setup-case.md)
- **[doit](./skills/engineering/doit/SKILL.md)** 办节点：一个对话办一个节点，出一版、重出、登记自写、确认、不适用。[说明](./docs/engineering/doit.md)
- **[ask-loo0ng](./skills/engineering/ask-loo0ng/SKILL.md)** 问路：只读的地图，第一行是待拍板行。[说明](./docs/engineering/ask-loo0ng.md)

#### Model-invoked

三件，由模型够到，律师无需记名：

- **[graph](./skills/engineering/graph/SKILL.md)** 图引擎：`图.json` 的唯一写入口，写完重算两份视图。[说明](./docs/engineering/graph.md)
- **[domain](./skills/engineering/domain/SKILL.md)** 预设图的家：出厂与个人两处两归属，解析、列出、另存、导入。[说明](./docs/engineering/domain.md)
- **[filing](./skills/engineering/filing/SKILL.md)** 归档：把文件搬进材料、参考/模板、参考/指南三格，并维护归档索引。[说明](./docs/engineering/filing.md)

### Productivity

离了案子也能单独用的工具，对应上游的「daily non-code workflow tools」。

#### User-invoked

暂无。

#### Model-invoked

一件，由模型够到，律师无需记名：

- **[to-docx](./skills/productivity/to-docx/SKILL.md)** 填模板：把 DOCX 打成带编号的清单，按差量原地施加。[说明](./docs/productivity/to-docx.md)

## 给开发者

七件 skill 在 Claude Code 与 Codex 两个 harness 上都能触发。

硬边界两条写在 `AGENTS.md`：案件材料永不进本仓库，办案会话对本仓库只读。词汇以 `CONTEXT.md` 为准，决策记在 `docs/adr/`，结构不变量与长约定在 `AGENTS.md` 与 `docs/agents/`。

### 维护

登记步骤见 [登记约定](./.agents/registration.md)，校验命令与测试命令见 [校验与测试](./.agents/testing.md)，发布与安装约定见 [发布与分发](./.agents/release.md)。发布链照上游 mattpocock/skills：每次修改写一张 changeset，推到 `main` 后 `.github/workflows/release.yml` 里的 changesets/action 自动开一个 "chore: version skills" 的 PR，合并即打 tag；`package.json` 的版本由 `scripts/sync-plugin-version.mjs` 抄进 `.claude-plugin/plugin.json`，版本记录在 `CHANGELOG.md`。测试与 eval 仍然全部本地跑（ADR-0015 2026-09-12 附注）。

发完一版要装到律师那台机器上时，照 `docs/交付/现场清单.md` 现场做，结果填 `docs/交付/记录表.md`：那是开发者本人在那台机器前的四段（装、跑得动填模板脚本的环境、起手一个案子、跑通一个节点），断网可用。交到律师手上让他自己照着走的那一份是 `docs/交付/律师上手指南.md`：装 skill、装桌面卡片、起手第一个案子、办完第一个节点，一条线走到底。

## 许可

代码与文档按 [MIT](LICENSE) 授权。`skills/engineering/domain/assets/预设图/<名>/` 下的官方模板原件与指引手册原文是第三方文件，不在 MIT 的覆盖范围内，各依其自身来源的条款：范围说明在 `LICENSE` 末尾。
