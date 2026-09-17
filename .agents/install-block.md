改安装文案先改这里，再往外抄。

# 安装文案

两条安装路线按律师的使用顺序排列：skills.sh 在前，Claude Code 插件在后。junction 是维护者的开发脚本；现场路 B 是 skills.sh 的本地来源兜底，路 C 是离线拷贝，均不另算产品安装路线。

## 消费方

复制 `<canonical-block>` 内的全文，保留命令、措辞与链接；标签本身不复制。消费方用 HTML 注释标出同名块与本文件的路径。共用链接用绝对地址，使两处正文逐字一致。

| 块名 | 消费方 |
| --- | --- |
| `route-choice` | `README.md` 的安装首段 |
| `skills-sh` | `README.md` 的首个 details；`docs/交付/现场清单.md` 的 1.1 |
| `claude-plugin` | `README.md` 的第二个 details |
| `local-junction` | `README.md` 的第三个 details |
| `skills-sh-local` | `docs/交付/现场清单.md` 的 1.2 |
| `desktop-card` | `README.md` 的「桌面卡片（可选）」一节 |

`docs/engineering/` 与 `docs/productivity/` 的 skill 说明页一段都不抄，保持不写安装命令。现场清单的七件全选、失败记录、安装后检查与离线拷贝仍由清单自持；它面向 Codex，不抄 Claude Code 插件段。后续 changeset 若需要说明当前安装方式，也从对应块取原文。

**桌面卡片的安装命令不抄进本仓库。** 它住在另一个公开仓库，命令、宿主要求与设置文件的写法以那边的 README 为正本；这边只给一个链接和一句「它读什么」。两个仓库各写一份同一条命令，迟早有一份先改、另一份不知道。`docs/交付/律师上手指南.md` 也不抄：它让律师叫 Codex 去读卡片仓库的 README 再装，只把 skills.sh 那一条命令摘进去当兜底（形状同 `docs/交付/记录表.md` 的 I1）。

<canonical-block name="route-choice">

律师自行安装先走 skills.sh，下面按这个顺序列。开发者当前在 Claude Code 用插件，Codex 要用时走 skills.sh。**每个 agent 只选一条路线**，同一个 agent 两条都装，每件 skill 会出现两次；插件是只读的整包，skills.sh 安装的是可编辑的 skill 文件。

</canonical-block>

<canonical-block name="skills-sh">

律师那台 Mac 已走通的是公开仓库下的 skills.sh 安装；下面以 Codex 为例：

```bash
npx skills@latest add f4de01/loo0ng-skills -a codex
```

用 Claude Code 就把 `-a codex` 换成 `-a claude-code`；两边都用可同时指定，但已装本插件的 agent 不再用这条。安装器让你挑 skill 与安装范围。**安装源须是公开仓库**：现场私有仓库下失败三次，转 public 后装上，记录见[现场实测结论](https://github.com/f4de01/loo0ng-skills/blob/main/docs/实测/mac-20260909/结论.md)。这次成功是口述记录，没有保存本轮退出码与报错原文。

</canonical-block>

<canonical-block name="claude-plugin">

本仓尚无官方市场上架入口，自建市场是当前提供的插件安装路线，因此保留给需要插件的用户。在 Claude Code 会话里：

```
/plugin marketplace add f4de01/loo0ng-skills
/plugin install loo0ng-skills@loo0ng-marketplace
```

装上后 skill 名带 `loo0ng-skills:` 前缀，例如 `/loo0ng-skills:ask-loo0ng`。开发机已验证这条路线；上述律师 Mac 的现场记录未验证公开仓库下的插件安装，不能把 skills.sh 的成功当作插件安装的证据。

`owner/repo` 形式只取默认分支；要装某个分支，用 `https://github.com/f4de01/loo0ng-skills.git#<branch>`。安装源同样须是公开仓库，私有仓库凭本机凭据安装仅在开发机上验过。

</canonical-block>

<canonical-block name="local-junction">

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1
```

维护者的开发脚本，照上游 `link-skills.sh`，不是安装路线：把 `skills/<bucket>/<name>/` 逐条以 junction 挂到 `~/.claude/skills/` 与 `~/.agents/skills/`，顺手设 `core.hooksPath` 启用隐私钩子。开发机照上游「一个 harness 只装一条路」：Claude Code 侧装了本插件就不挂 `~/.claude/skills/`（脚本自己判断），那一侧用 `claude plugin update loo0ng-skills@loo0ng-marketplace` 更新，skill 名带 `loo0ng-skills:` 命名空间；Codex 侧要用就走上面的 skills.sh，装了它就别再挂 junction。只在改名、增删 skill 后重跑。

</canonical-block>

<canonical-block name="skills-sh-local">

```bash
command -v gh && gh auth status
gh repo clone f4de01/loo0ng-skills ~/交付包/repo
npx skills@latest add ~/交付包/repo -a codex
```

⚠️ 这台机器上有没有 `gh`、登没登录，都不知道。没有就直接降路 C。

</canonical-block>

<canonical-block name="desktop-card">

桌面卡片是另一个仓库的东西：一张常驻桌面的卡片，同时看住在办的多个案件，每案显示当前模块、进度、下一个要办的节点。它只读每个案件工作区的 `图视图.json`，一个字节都不写；装不装都不影响这里的七件 skill。

安装命令、它要的宿主、设置文件怎么写，都在它自己的 README：[loo0ng-widget](https://github.com/f4de01/loo0ng-widget)。

装过之后不用第二次配置：起手一个新案件时，`setup-case` 把这个案件的上级目录加进卡片的根目录列表（`~/.loo0ng/卡片设置.json`），卡片下一轮扫描就看得见它；已经在列表里就一个字不动，那份设置不在就整步不做。不想要这一步，起手时给 CLI 加 `--no-card`。

卡片只认当前的图格式。更早的版本起手、至今没被引擎重写过的工作区，它会列在「读不出」里：那种图没有升级路径，从预设图重新起手即可。

</canonical-block>

## 全仓检索对照

以下保留全仓检索命中的历史记录、开发参考及命令名称原行，供验收逐字对照，不作为当前安装建议。原文件保留原样；当前安装消费方只抄上面的 canonical-block。`docs/交付/记录表.md` 的 I1 摘录 `skills-sh` 命令，清单与记录表的 U9 等处只是指称安装器。后续新增安装指引从上面的块取文案。

### `.agents/release.md`

```text
4. `plugin.json` 的 version 变了，装了插件的机器才会收到更新；skills.sh 路线要律师自己 `npx skills update`。
- 插件路线：`claude plugin marketplace add` 与 `codex plugin marketplace add … --ref` 对私有仓库都吃本机凭据，缓存是整仓库拷贝。**这条只在开发机上成立**，别当分发口径，见下面「安装源必须是公开仓库」。
- 本机验证插件路线不必推分支：`claude plugin marketplace add <本仓库绝对路径>` 再 `claude plugin install loo0ng-skills@loo0ng-marketplace`，`claude -p "/loo0ng-skills:<name>"` 可触发；验完 `claude plugin uninstall` 与 `claude plugin marketplace remove loo0ng-marketplace`（#24）。
- skills.sh：`npx skills@latest add owner/repo` 只取默认分支，分支名含 `/` 时解析失败。
```

### `.agents/writing-docs.md`

```text
**说明随包自足（ADR-0025）**：skill 根目录的全部 `*.md` 与 `scripts/` 的说明（含注释、文档字符串、回显）不出现 ADR 号、issue 号、发布版本号，也不指向本 skill 目录之外的仓库文件（`CONTEXT.md`、`AGENTS.md`、`docs/`、`tests/`）。`npx skills add` 与 `claude plugin install` 装过去的只有 `skills/<bucket>/<name>/` 这一个目录，别的都读不到。历史对比句（「以前 X 现在 Y」）与出处标注一并不写；会改变模型判断的内容留下来，改写成判据本身（写「不许 X」，不写「因为当年 Y 所以不许 X」）。`check-skill.sh` 逐件扫根目录 Markdown 与 `scripts/` 文件，白名单放行清单坐标（`p2#1`）、指向本目录兄弟文件的链接、钉住的后端版本号（`python-docx==1.2.0`、`python 3.9.6`）。运行所需的图格式版本、包内路径与工作区文件名仍保留；`assets/` 中的官方模板与指南是原始数据，不按说明清洗。
```

### `CHANGELOG.md`

```text
  `/plugin install loo0ng-skills@loo0ng-marketplace` 之后装到的是齐活的七件，彼此调得通；装了插件的机器 `claude plugin update` 一次就收到整套。用 `npx skills@latest add f4de01/loo0ng-skills -a codex -a claude-code` 的照旧，一条命令装到两个 harness。
  **插件路线重新装得到东西**：`/plugin install loo0ng-skills@loo0ng-marketplace` 之后七件齐活、彼此调得通，不再是一个空包。装了插件的机器 `claude plugin update` 一次就收到整套。用 `npx skills@latest add f4de01/loo0ng-skills -a codex -a claude-code` 的照旧，一条命令装到两个 harness。
- [#4](https://github.com/f4de01/loo0ng-skills/pull/4) [`84b41dc`](https://github.com/f4de01/loo0ng-skills/commit/84b41dc9817cf9b4f7df2255dc735f9490bec7cc) Thanks [@f4de01](https://github.com/f4de01)! - **Breaking:** 七件 skill 全部搬进 `skills/in-progress/` 逐件重做（ADR-0022）。改造期间 Claude Code 插件清单为空，`claude plugin update` 之后装到的是空包；要继续用请留在 0.4.0，或走 skills.sh 单件装：`npx skills@latest add f4de01/loo0ng-skills --skill=<name>`。skill 名与打法没有变，已起手的案件工作区不受影响。ADR-0001 至 0021 同时降为参考，与 skill 正文冲突时以正文为准。
  - **不再发 Codex 原生插件**：`.codex-plugin/` 删除。Codex 用户改用 `npx skills@latest add f4de01/loo0ng-skills`；skill 在 Codex 里显示为裸名。
- 02346dc: 领域目录搬出 skill 包（#90，ADR-0019）：`~/.loo0ng/领域/<领域名>/` 是**活图**，包内 `skills/loo0ng-domain/assets/<领域名>/` 降为**出厂种子**。挡的是这条路线唯一的不可逆事故：领域图原先随包分发，律师再跑一次 `npx skills add` 升级就被整个覆盖，累计半年的图一次抹掉。`loo0ng-domain` 的雏形 CLI 多一条 `home --name <领域名>`：活图不在就从种子整份拷一份（破产那份 22 件约 540 KB，实测 0.2 秒，起手上感觉不到），已经在就一个字不动、只回显路径，回显第一行是 `活图：<绝对路径>`；活图与种子都没有的新领域它拒，那个领域从空图起手。拷贝先落临时名再改名，拷到一半断了不会留下半份被下一次当成活图。默认位置在用户主目录而不是案件根旁边：领域目录是跨案件的，不该跟着某个案件目录搬家；环境变量 `LOO0NG_HOME` 换「家」那一层，脚本层单测与 eval 跑器用它，律师那台机上不设。
```

### `docs/adr/0022-0001至0021降为参考-七件搬进in-progress逐件重做-正文为准-毕业时再登记.md`

```text
- **七件 skill 全部搬进 `skills/in-progress/`，按上游对这个桶的定义处理。** 不进 `.claude-plugin/plugin.json`、不进根 `README.md`、没有 `docs/<bucket>/<name>.md` 页；桶 `README.md` 逐件列出。`plugin.json` 的 `skills` 数组在改造期间为空：Claude Code 插件路线装到的是空包，`claude plugin update` 不会把半成品推到任何人的机器上；要试用走 skills.sh 单件装（`npx skills@latest add f4de01/loo0ng-skills --skill=<name>`），律师那台 mac 走的本来就是这条路。桶 README 原先那句「草稿放分支不放目录」对这一轮不适用：这一轮改的是全部七件、跨多次发布，分支装不下。
```

### `docs/adr/0025-skill正文随包自足-与ADR与issue与仓库文件剥离.md`

```text
这些指针在开发机上读得通，在律师机上读不通：`npx skills add` 与 `claude plugin install` 装过去的只有 `skills/<bucket>/<name>/` 这一个目录，`docs/adr/`、`CONTEXT.md`、`AGENTS.md`、`tests/` 一个都不在。
```

### `docs/research/mac-实测-20260907.md`

```text
1. **第 1 级安装误判成功。** `npx skills add` 退出码 1、报 `Authentication failed for https://github.com/...`，脚本却写出 `==> 第 1 级成功，路线：1-skills.sh 网络装`。原因是 `装上了()` 只看 `~/.agents/skills/loo0ng-doit` 存不存在，而**上一轮拷进去的还在**（律师删了桌面上的包，没删 `~/.agents/skills`）。
```

### `docs/research/skill-platforms-claude-code-与-codex.md`

```text
- marketplace：仓库根 `.claude-plugin/marketplace.json`，必填 `name`、`owner`、`plugins[]`；source 支持相对路径、GitHub、git URL、git-subdir、npm、zip、command。本地目录 marketplace：`claude plugin marketplace add ./my-marketplace --scope project`。
- 默认 marketplace 在 `.agents/plugins/marketplace.json`；CLI `codex plugin add|list|remove`、`codex plugin marketplace add|list|upgrade|remove`；TUI `/plugins`。
- `openai/skills` 仓库 README 自述已弃用，改用 `openai/plugins`；安装用内置 `$skill-installer`（无 `npx skills add`）。
```

### `docs/交付/现场清单.md`

```text
| U9 | `npx skills add`（路 A / 路 B）拷不拷 `domain/assets/` 下那 21 件 docx | 从没测过；缺了段 3 就只剩空图一条路 | 1.4 第四查那三条的输出 |
原先还有一处 U1（`npx skills add` 这一次成不成），2026-09-09 那趟答掉了：私有仓库装不上，仓库转成 public 之后装成了（`docs/实测/mac-20260909/结论.md`）。编号不回收，U2 至 U8 原号不动，U9 是这一版新加的。
```

### `docs/交付/记录表.md`

```text
| I1 | 路 A `npx skills@latest add f4de01/loo0ng-skills -a codex` | | | |
| U9 | `npx skills add` 拷不拷 `domain/assets/` 下那 21 件 docx | |
```

### `docs/实测/mac-20260907/probe/02-装.sh`

```text
run "npx skills add（180 秒上限，非交互）" bash -c "perl -e 'alarm 180; exec @ARGV' npx --yes skills@latest add $REPO -a codex < /dev/null 2>&1"
```

### `docs/实测/mac-20260907/出/结论模板.md`

```text
| 4 | 第 1 级 `npx skills add` 结果（成功 / 卡交互 / 凭据失败 / 超时） | | `04-安装.txt` |
```

### `docs/实测/mac-20260909/结论.md`

```text
| 2026-09-07 之前那一轮（日期未记） | 路 A `npx skills@latest add f4de01/lawyer-workbench-v3 -a codex` | 私有仓库 | 失败 | 原始回显：`Error in the HTTP2 framing layer` |
`docs/交付/现场清单.md` 的 U1 是「`npx skills add` 这一次成不成」，本轮答掉：**私有仓库装不上，公开之后装得上。** 清单与 `docs/交付/记录表.md` 的那一行已删，编号不回收（U2 至 U8 原号不动，免得跟旧记录表串号）。
```
