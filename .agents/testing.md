# 校验、测试与验收

改文件后选校验命令、改脚本或种子后跑回归、改 skill 后跑 eval 与关票触发时读本篇。命令在仓库根目录执行；发布流程见 [release.md](./release.md)。

## 三条校验命令

`claude plugin validate .` 有 `marketplace.json` 时只验它、不验 `plugin.json`；`plugin.json` 在 `--strict` 下因根 `CLAUDE.md` 的 warning 必败（Matt 自己的插件同样），所以拆三条（#18 项 2）：

```bash
claude plugin validate . --strict                    # marketplace.json，严格
claude plugin validate skills --strict               # 全部 skill 的 frontmatter，严格
claude plugin validate .claude-plugin/plugin.json    # plugin.json，非严格
```

## 其他检查

```bash
# 全仓文本规矩三条（破折号 U+2014、非 .ps1 不带 BOM、.ps1 必须带 BOM），改任何文本文件都跑
bash scripts/check-text.sh .

# 版本一致：.claude-plugin/plugin.json 跟上 package.json（package-lock 不同步，照上游）
npm run check-plugin-version

# 结构与接线（照上游约定的四个检查，提交前必跑；Windows 上用 Git Bash 跑）
bash scripts/check-skill.sh .              # 每件 skill：name、description 引号、openai.yaml、双旗一致、正文随包自足
bash scripts/check-wiring.sh .             # promoted 四处都在、非 promoted 四处都不在、plugin.json 路径真实
bash scripts/check-stale.sh . <旧名>       # 改名或删除之后：旧名字一处不留
bash scripts/check-release.sh .            # 发版前：changesets 配置、同步脚本、workflow、版本一致
```

`check-text.sh` 三条的名单都是「已跟踪 + 未被忽略的未跟踪」（`git ls-files -z` 接上 `git ls-files -z --others --exclude-standard`），二进制由 `grep -I` 自己跳过；`privacy-check.py --all` 的名单同理。名单曾经只有已跟踪那一半，于是新文件在 `git add` 之前对它是隐形的，一个带破折号的 ADR 正文提交前三次校验全绿、提交之后才报错（#93）。现在仓库工作树里一个临时草稿也会被检查，这是对的：它本来就在工作树里，提交上去就晚了，真不想被扫的东西该进 `.gitignore`。

这三条原先只以命令的形态写在这里，没有任何脚本查它们，全靠人记得跑，于是破折号一路漂到 14 个文件 68 处才被发现；收进脚本并进 `AGENTS.md` 不变量 6 之后，每个开发会话都会跑到它。**正则里真要认破折号时写成 `\u2014` 转义**（Python `re` 认得），别在源码里放字面字符。

## 测试命令

脚本层单测在 `tests/<名>/`，标准库 unittest，全部本地跑（ADR-0015）：

```bash
for d in tests/*/; do python -m unittest discover -s "$d" -p 'test_*.py' || exit 1; done
```

`tests/共用/` 不是测试目录，是几个测试目录 import 的夹具（`sys.path.insert(0, str(REPO / "tests" / "共用"))`）：`工作区.py` 用引擎在临时目录里造一个案件工作区，`临时仓库.py` 造一个只有一次提交的临时 git 仓库（`check-text`、`privacy-check` 这两个扫全仓的脚本共用它）。

`tests/evals/test_seeds.py` 是种子那一份：16 个种子各回放一遍，对着各自的 `状态.md` 断工作区状态（目录形状、图与两份视图、条目、高亮清没清、归档索引、家里那份个人预设图），并守两条接口：每个种子都有 `回放.py` 与 `状态.md`、每个用例指的种子都存在。种子一改它立刻红，所以改种子与改它是同一次提交的事。约半分钟（每个种子都真跑一遍起手 CLI）。

`tests/to-docx/` 只有一条跑道（ADR-0024 之后，版式门禁整件退场）：**不起 Word，在任何机器上必须全绿、不许 skip**，合起来半分钟上下。19 件官方模板逐件回归（`test_templates.py`）守的是施加前后 `tblPr`、`tblGrid`、`trPr`、`tcPr` 逐字节相同、槽外格式不变、元数据清掉：数据泄露与渲染格式两样保证从运行时的门禁挪进了测试，每次改 `fill.py` 都要过 19 件。

**3.9 那条跑道**：随包脚本的底线是 python 3.9（律师那台 mac 的 `/usr/bin/python3` 是 3.9.6），`tests/python-floor/` 只按形状扫，真跑要自己起一次。装一份钉住的后端再跑全套：

```bash
uv pip install --python <3.9 解释器> --target <临时目录> -r skills/productivity/to-docx/requirements.txt
PYTHONPATH=<临时目录> <3.9 解释器> -m unittest discover -s tests/to-docx -p 'test_*.py'
```

2026-09-14 在 cpython 3.9.25 上跑过一遍（门禁退场之后）：全绿、零 skip。

skill 层 eval：一个跑器两个后端，用例与种子在 `evals/`（ADR-0015，#25）：

```bash
python scripts/skill-eval.py --harness claude                 # Claude Code 侧，走 claude -p
python scripts/skill-eval.py --harness codex                  # Codex 侧，走 codex exec
python scripts/skill-eval.py --harness claude --case 冒烟     # 只跑一个用例；--case 可重复
python scripts/skill-eval.py --harness codex --runs 3         # 怀疑抖动时多跑几次
python scripts/skill-eval.py --harness claude --evals evals/自检   # 跑器自检用例（故意失败），不进门槛
python scripts/skill-eval.py --harness claude --case 出一版留黄 --model opus --effort high   # 换模型跑
```

Codex 侧提示词经 stdin 送入（`PROMPT` 位置是 `-`）：PATH 上的 `codex` 是 npm 的 `.cmd` 垫片，cmd.exe 会把参数里第一个换行之后的字吞掉，多行提示词（如带一段稿子的「出一版」用例）只剩第一行（#28）。其他参数：`--max-turns N`、`--timeout 秒` 覆盖用例里的值；`--keep` 跑完不删工作区，只为排障；`--model` 与 `--effort` 透传给各自的 CLI（Claude Code 侧 `--model`/`--effort`，Codex 侧 `-m` 加一条 `-c model_reasoning_effort=...`），两个都不给时走 CLI 自己的默认（Codex 读 `~/.codex/config.toml`），这是既有跑法的兼容线；这次用的是哪个，跑器回显第一行报出来，跨跑比较才读得出结果是哪个模型跑的。退出码 0 全绿、1 有红、2 用法或用例配置错。结果只打印不进仓库。从 Claude Code 会话内跑 `--harness claude` 不用自己去环境变量：跑器已去掉 `CLAUDECODE` 两项并带上 `MSYS_NO_PATHCONV=1`。

### `evals/` 目录

```
evals/
├── 用例/<名>/           # 合入门槛跑的用例，目录名即用例名
│   ├── 提示词.md        # 律师原本会打的那一句
│   ├── 用例.json        # 见下
│   └── 断言.py          # check_ 开头的函数各是一条断言，签名 (workspace: Path, reply: str)，assert 判真伪
├── 自检/<名>/           # 只测跑器自己的用例（如 故意失败），同格式，用 --evals evals/自检 跑
├── 种子/<场景>/         # 待归档/ 等直接拷进工作区的东西 + 回放.py + 状态.md（#20 按 ADR-0023 重定）。除「空目录」（它就是起手之前的样子）外每个回放都以真的起手 CLI 开头：出厂预设图「破产」按名解析、原位读；合成小领域「菜园」是一份由回放助手用引擎现造在「家」里的**个人预设图**（4 模块 9 节点），「图引擎」「待归档」「模板」「指南」「另存」都从它起手。tests/evals/test_seeds.py 逐个回放、对着各自的 状态.md 断
└── 共用/                # 跨用例、跨种子共用的几个模块，不是用例也不是种子（跑器按目录里有没有 用例.json 认用例，扫不到这里）：
                         #   桶.py 按 skill 名解析它住哪个桶（全仓库唯一一处写桶名的地方：回放、四条用例断言、tests/ask-loo0ng 都调它）；
                         #   回放助手.py 起手、写图、归档、合成 docx、造菜园与「家」的解析，各种子共用；基线.py 三份图文件的 sha256（路由只读与「图一字不动」的判据）；
                         #   路由断言.py ask-matt 五条验收项加「只指向表里的三个入口」「只读基线」「五段按序」「第一行是待拍板行」，八个路由用例各 import 一遍
```

用例与种子的对应（27 个用例，含不依赖任何 skill 的 `冒烟`；16 个种子）：起手类两个（`起手`、`起手一问二选`）在「空目录」上；归档两个（`归档一件`、`归档清单拍板`）在「待归档」上；`改标题`、`换节点被拒` 在「图引擎」上，`出雏形` 在「指南」上，`模板槽清单` 在「模板」上，`另存预设图` 在「另存」上；办节点那一路 `出一版留黄`、`记一句`、`拍板`、`模块不适用` 与路由的 `问了图里没有的事` 在「在办中」上，`兜底登记` 在「兜底」上，`拒改收尾` 在「拒改」上（ADR-0024 之后「不通过收尾」的替身：模板里的槽所在 run 带域代码，施加必拒），`律师填后重出` 与 `模型误去黄` 在「填过黄」上，`跨对话确认`、`两份同时待确认`、`路由第一行` 在「两份待确认」上，其余路由用例各自一个同名种子。

ADR-0015「目录名保持 ASCII」只指 `tests/`、`evals/` 两个顶层；其下按仓库习惯用中文（ADR 自己的例子 `evals/种子/<场景>/` 即如此），`--case 冒烟` 直接传中文名。

`用例.json` 的键（多一个未知键即报错）：

| 键 | 含义 |
| --- | --- |
| `种子` | `evals/种子/` 下的场景名，本票允许为空 |
| `skill` | 编排 skill 名，可空。Claude Code 侧拼成 `/loo0ng-skills:<skill> <提示词>`（照上游一个 harness 只装一条路：跑器看 `~/.claude/plugins/installed_plugins.json` 里有没有装本插件，装了带命名空间，没装（开发机挂 junction 跑待验分支时就是这样）就是裸名 `/<skill>`；`--claude-plugin` 显式给了以它为准）；Codex 侧用替身提示词「读 `~/.agents/skills/<skill>/SKILL.md` 并照做：<提示词>」，测的是正文不是触发，触发另由人工实测与完成定义那一次覆盖。带 skill 的用例必须有 `说明` |
| `回复正则` | 对最后一条回复做 `re.search`，可空；报红时断言名是「回复正则」 |
| `回合上限` | Claude Code 侧交给 `--max-turns`；Codex 侧数 JSONL 流里工具类 item（命令、改文件、MCP、搜索），超了杀进程树。默认 30 |
| `超时秒` | 单次调用的墙钟上限，超了杀进程树。默认 300 |
| `允许工具` | Claude Code 侧 `--allowedTools` 的列表（如 `["Bash(python *)"]`）；权限模式固定 acceptEdits。Codex 侧靠沙箱，不需要 |
| `Codex沙箱` | Codex 侧 `codex exec -s` 的值：`workspace-write`（默认）或 `danger-full-access`。**本套用例全在默认值上**（#78 实测全绿）：沙箱里 `python` 敲不动（那两个目录就在 PATH 上，只是沙箱账户读不到），但不阻断：填模板脚本的环境由 agent 自备、经 uv 走得通（ADR-0018）。`danger-full-access` 是跑器的能力，不是任何用例的前提 |
| `说明` | 一句话，含用例的局限；带 skill 时必填，写明替身提示词的局限 |

每次运行：在 `%TEMP%` 下建临时工作区 → 回放种子 → 调 harness（cwd 即工作区）→ 回复正则 → 逐条断言 → 删工作区（超时、超回合、断言抛错都删）。断言报红时给出函数名与 assert 的消息。

每次运行另在 `%TEMP%` 下建一个**家**，经环境变量 `LOO0NG_HOME` 交给 harness（ADR-0023：个人预设图住 `<家>/预设图/<名>/`，由 `domain` 的 `preset.py` 解析，默认 `~/.loo0ng`）：eval 既不该往律师的主目录里写东西（另存会写进去），也不该吃上一次跑剩下的预设图（ADR-0015 只生不存）。跑完连它一起删，`--keep` 时连它一起留并打印路径。两侧都吃这个变量（#90 实测 Codex 的 `workspace-write` 沙箱写得动 `%TEMP%` 下的它）。`--materialize` 生出来的工作区不设它，回放自己兜底：`evals/共用/回放助手.py` 没看到这个变量就把家落进工作区里的 `.预设图家/`（点开头，起手不挪它），所以「空目录」「图引擎」那几个在家里造菜园的种子 `--materialize` 出来也碰不到真的 `~/.loo0ng/`。**但兜底只管回放自己那几条命令，管不到 harness 里的模型**：模型调 `preset.py` 时环境里没有这个变量，解析到的就是真的 `~/.loo0ng/`，起手找不到那份个人预设图、另存写进开发者自己的家（#105 在 Codex 侧实测过同款事故）。所以 `--materialize` 回显里带上这次要设的 `LOO0NG_HOME`，关票触发之前把它设进环境；eval 那条路由跑器统一设，碰不到真的主目录。

种子接口：`evals/种子/<场景>/` 里除 `回放.py` 与 `状态.md` 之外的条目原样拷进工作区，再在工作区里跑 `python 回放.py <工作区>`；起手（`setup-case`）、引擎 CLI、归档脚本都写在回放里，跑器不另定回放格式。起手会把工作区根上原有的条目挪进 `待归档/`，所以种子里要落在别处的文件先放 `待归档/` 下、由回放经归档 CLI 搬（「指南」「在办中」即如此），只有「空目录」把文件放根上（它测的正是起手把根上的东西挪进待归档）。

Windows 上工作区用 `os.mkdir` 而不用 `tempfile.mkdtemp`：后者建的目录只有 SYSTEM、Administrators、OWNER RIGHTS 三条 ACE，Codex 沙箱账户写进去的文件本用户读不了也删不了。

合入门槛 = 脚本层全绿 + 两侧 eval 全绿 + 三条校验；关票门槛 = Codex 与 Claude Code 各真实触发一次（ADR-0015）。`in-progress/` 里要公开试用的件提交前只跑 `check-skill.sh`、`check-wiring.sh` 与 `claude plugin validate`；它毕业时单测与 eval 随脚本与正文重定，留下的才重新成为它的门槛。

**没有按名字放行的用例**，门槛就是两侧全绿。红了就查那一件，不查名单：先在改后的正文上复跑几次（`--runs 3`）拿到红的比例，再把那一件正文换回 main 的版本跑同样次数。两边比例相同、失败模式相同，就是常规抖动，与本票无关，PR 里点名这件红并附两组数字；比例变了就是本票的正文改出来的，改正文，不改门槛。

### 关票触发怎么做

触发在**从种子生出的临时工作区**里做，跑完即弃（ADR-0015 与 ADR-0009 的 2026-09-07 附注，#66）。

案件根下还留着几个目录名带「合成」字样的常驻工作区（#32 起攒下来的，现在三个：两个整份起手、一个空图起手），它们是**手工探索的现成起点**：想在一个办到一半的案子上试打一句、看看回显长什么样，不必等回放。**它们不承担任何门槛**：关票不在它们上面做，合入也不看它们，因此也不必为它们定「什么时候重建」的规矩，脏了就脏了。理由是改图不可逆（节点永不删、不适用是终态，ADR-0003），在常驻目录上触发留下的痕走支持的路子撤不掉，撤只有标不适用（残渣更多）或手改 `图.json`（不受支持）两条。路径不写进仓库与 issue（硬边界 1）。

```bash
# 1. 生一个工作区：打印路径就停，不跑 harness、不删
#    在家里造了个人预设图的种子（「空目录」「图引擎」「待归档」「模板」「指南」「另存」）还会多回显一行 LOO0NG_HOME=<…>
python scripts/skill-eval.py --materialize 在办中

# 2. Claude Code 侧（开发会话里就能跑，打的是真名，算真实触发；插件路线带 loo0ng-skills: 命名空间）
cd <上一步打印的路径>
export LOO0NG_HOME=<上一步回显的那个>   # 回显了就必须设：不设的话模型调 preset.py 会读写真的 ~/.loo0ng
MSYS_NO_PATHCONV=1 CLAUDECODE= CLAUDE_CODE_ENTRYPOINT= \
  claude -p "/loo0ng-skills:<skill 名> <律师那句话>" --output-format json \
  --permission-mode acceptEdits --no-session-persistence --allowedTools Bash

# 3. Codex 侧两条路都算按名字触发，挑一条：
#    a. 客户端：cd 到同一个路径再打 $<skill 名>（`/` 与 `$` 两种写法都调得到，靠补全 tab 选中）。
#       回显了 LOO0NG_HOME 就先在那个终端里设好，客户端继承的是它自己的环境
#    b. 无人值守：printf '%s' '$<skill 名> <律师那句话>' | codex exec -s workspace-write -
#       目录不是 git 仓库时它不肯起，要么先 git init，要么加 --skip-git-repo-check

# 4. 用完删掉那个目录
```

种子挑与要验的路径最接近的那个：`在办中` 是办到一半（出厂预设图「破产」12 模块 72 节点、一份已确认一份待确认、律师说过的四行），`空目录` 用来验起手，`图引擎` 是合成小领域「菜园」（个人预设图），`填过黄` 是律师在 Word 里填过黄之后的重出，`拒改` 是施加必拒的那一档。

**第 2 步那行与跑器给 Claude Code 侧拼的命令是同一条**（`build_command`），差别不在命令而在别处：打的是你自己想打的那句话（不是用例里的提示词）、看的是回复本身（不跑断言）、判的是人。所以 Claude Code 侧这一次相对合入门槛那次 eval 的增量本来就小，两道门在这一侧几乎重合；增量大的是 Codex 侧，那边 eval 用的是替身提示词、根本没测触发（ADR-0015）。这条局限照实记着，别把它当成两次独立的证据。

**Codex 侧 `$名` 是解析的**：2026-09-16 在 codex-cli 0.154 上实测，`codex exec` 的提示词里写 `$doit`，`SKILL.md` 全文进上下文（让它抄第一行标题，抄出来的就是 `# 办节点`）；`doit` 带 `disable-model-invocation: true`、被滤出了隐式 skill 清单，那段正文只可能来自 `$名` 展开。所以关票触发在这一侧也能无人值守跑，不是非人工不可。本文件原先记的「AFK 下不解析」对 0.154 不成立，连它给的复核办法一并作废：`codex debug prompt-input` 只渲染提示词、自己不做展开，`$doit`、`$graph`、`$implement` 在它下面一律原样留在用户消息里，拿它推断不出 `exec` 行不行。客户端里 `/` 与 `$` 两种写法都调得到，靠补全 tab 选中（#44）；显示带不带 `loo0ng-skills:` 前缀看装的是哪条路线，拷贝进 `~/.agents/skills/` 的是裸名。

关票评论按 ADR-0009 只记日期、平台、打的名、结果类别，并写明材料是合成的。验到的与验不到的要分清：验到的是**这条安装路线下**按名字触发、流程走通（Claude Code 侧是插件路线的 `/loo0ng-skills:<名>`，Codex 侧是 `$<名>`，客户端与 `codex exec` 都算）；验不到的是真实案件材料下的判断，也验不到插件路线的 `/loo0ng-skills:<名>`（那条另由「两平台注册、补全与拉取实测」与 #44 覆盖）。工作区路径不写进 issue（硬边界 1）。
