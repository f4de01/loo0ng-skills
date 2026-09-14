# Skills：登记、校验与发布

`AGENTS.md` 的结构不变量每条一行；这里是长约定：怎么登记一件 skill、改完跑什么、怎么发布。仓库结构与分发照 Matt Pocock 的 skill 体系（ADR-0009），被实测推翻的四项按 #18 的决议表。

## 目录布局

```
skills/<bucket>/<name>/       # 桶照上游五个：engineering、productivity、misc、in-progress、deprecated；改造期七件都在 in-progress/（ADR-0022），毕业后主线六件回 engineering/，to-docx 回 productivity/
├── SKILL.md              # frontmatter：name、description；编排 skill 与路由另加 disable-model-invocation: true
├── agents/openai.yaml    # Codex 侧外观：interface.display_name（= name）、interface.short_description（中文进这里）；编排 skill 与路由另加 policy.allow_implicit_invocation: false
├── references/           # 正文按需指向的长材料
├── requirements.txt      # 只有 to-docx 有：填模板脚本后端的精确钉（python-docx==1.2.0，ADR-0018）。随包到律师机，agent 自备环境时按它装；仓库根上放到不了那里
├── scripts/              # 标准库零依赖的 CLI；只有 to-docx 的转换器例外（python-docx，ADR-0006），它的门禁本体也零依赖、PyMuPDF 只是可选的渲染加信（ADR-0017）。互不 import；跨 skill 一律以子进程互调、默认按兄弟目录找：要写图的（domain 的雏形、setup-case 的起手与既有成品登记）调 graph 的引擎，起手取活图路径（setup-case 的 init --domain-name）调 domain 的 sketch.py home（#97）
└── assets/               # 只有 domain 有：assets/<领域>/ 下领域图、模板/ 官方模板原件、指引手册/ 指引手册原文（ADR-0004）。这份是出厂种子，随包升级被换掉；律师那台机上的活图在 ~/.loo0ng/领域/<领域>/，由 sketch.py home 首次起手时拷出（ADR-0019）
```

**2026-09-14 起七件全部住 `in-progress/`，逐件改造后再毕业回 `engineering/` 或 `productivity/`（ADR-0022）；本段其余写的是毕业后的归属。** 分桶照上游（ADR-0009 的 2026-09-13 附注）：`skills/` 下五个桶，每桶一份 `README.md` 逐件列出、名字链接到 `./<name>/SKILL.md`；promoted 桶（`engineering/`、`productivity/`）里的每件进 `.claude-plugin/plugin.json` 与根 `README.md`（名字链接到 `SKILL.md`），并有一页 `docs/<bucket>/<name>.md`（固定段：What it does、When to reach for it、Common questions、It's working if、Where it fits，页内链接一律绝对）；`misc/`、`in-progress/`、`deprecated/` 里的不进这三处。上游 `engineering/` 装的是主线（daily code work），`productivity/` 装的是离了主线也能单独用的工具；对应到这里，办案主线六件（`ask-loo0ng`、`setup-case`、`doit`、`graph`、`domain`、`filing`，都只在有 `图.json` 的工作区里工作）在 `engineering/`，`to-docx`（清单与门禁都可对任意 DOCX 跑、施加差量默认写临时位置）在 `productivity/`；另外三桶目前只有 README。草稿放分支不放目录，要公开试用的才进 `in-progress/`（这一轮改的是全部七件、跨多次发布，分支装不下，所以七件都在那里）。分发清单只有一份：`.claude-plugin/plugin.json` 的 `skills` 数组逐件列路径（Claude Code 插件）；`.claude-plugin/marketplace.json` 让仓库自成单插件市场。不发 Codex 原生插件，Codex 及其他 harness 经 skills.sh 装编辑副本（ADR-0021，与上游 ADR-0002 同一个理由：Codex 清单只收单一路径，分桶后会把 `in-progress/` 一并装出去）。

## 命名与编码

- `name` 只用小写字母、数字、连字符，基名裸着写、不带 `loo0ng-` 前缀（ADR-0009 的 2026-09-13 附注「去前缀」）；路由照上游 `ask-matt` 形叫 `ask-loo0ng`。ASCII 的理由：skills.sh 分发链把非 ASCII 名装成 `unnamed-skill`，Codex `$` 提及只认 ASCII；两平台本身不拦（#18 项 1）。目录名与 `name` 一致。
- `agents/openai.yaml` 手写，照上游（ADR-0021）：`interface.display_name` 等于 `name`（Codex 的 `$` 补全列表显示的是它，律师按 `name` 那个名字找，中文显示名反而找不到，#29），`interface.short_description` 写中文短描述。frontmatter 只用上游那四个键（`name`、`description`、`disable-model-invocation`、`argument-hint`），不再有 `metadata` 块。
- `SKILL.md`、`agents/openai.yaml` 与所有 PowerShell 以外的文本文件不带 BOM：带 BOM 的 `SKILL.md` 会让 Codex 静默跳过整个根目录（#20）。PowerShell 5.1 脚本必须带 UTF-8 BOM，否则中文注释按 ANSI 读会撕坏语法（#18）。
- 随包分发的脚本（`skills/*/*/scripts/*.py`）与种子回放（`evals/种子/*/回放.py`）跑得动 python 3.9：律师那台 mac 的 `/usr/bin/python3` 是 3.9.6，图引擎一处 3.10 的 `Path.write_text(newline=)` 就让每一次写图全炸（#61）。`tests/python-floor/` 机械守着这条：按 3.9 的 feature_version 解析，外加认得出形状的 3.10 API。`scripts/` 与 `tests/` 下的开发侧脚本不受这条约束（ADR-0015：它们只在开发机上跑）。
- 全仓禁破折号（U+2014）。连接号 U+2013 用于数字区间，不在此列。
- frontmatter 的 `description` 加双引号：不加引号时 ` #` 起 YAML 注释，两平台都把其后的字截掉（#24 空壳验证时发现）。

## description 两套

- User-invoked（编排 skill 与路由）：一句人话，功能加后面跟什么，去掉触发词。
- Model-invoked（参考 skill）：四要素齐全（功能、触发、负向、邻居互指），第三人称、中文、触发词放最前、不超过 1,024 字。
- 跨 skill 只用「调用 skill "xxx"」一种句式，散文里可用中文叫法（如「图引擎」，只是行文，不是元数据）；改名于是成为纯机械替换。
- 路由 `ask-loo0ng` 的正文是这条的例外：它写的入口名是**律师要打的那一串**（`/名 …` / `$名 …`，ADR-0005），只能裸着写；它谈别的 skill 的行为时仍用「调用 skill "xxx"」句式指出处。裸名仍是同一个字符串，改名照样是机械替换。

## 双旗

| 类型 | `SKILL.md` frontmatter | `agents/openai.yaml` |
| --- | --- | --- |
| 编排 skill、路由 | `disable-model-invocation: true` | `policy.allow_implicit_invocation: false` |
| 参考 skill | 不写 | 不写 `policy` |

两平台各读各的旗，互不认对方的（#18 项 3）：两处都手写，`bash scripts/check-skill.sh .` 守两端一致：`disable-model-invocation: true` 与 `policy.allow_implicit_invocation: false` 要么都有要么都没有。

## 登记步骤（新增、改名、删除都走一遍）

1. `skills/<bucket>/<name>/` 落目录（主线进 `engineering/`，离了案子也能用的进 `productivity/`），按上面的布局与命名、编码规则；所在桶的 `README.md` 加（或改、删）一行，名字链接到 `./<name>/SKILL.md`。
2. 双旗按类型写齐：`SKILL.md` 里写旗，手写 `agents/openai.yaml`（`display_name` 等于 `name`）。
3. `.claude-plugin/plugin.json` 的 `skills` 数组加（或改、删）`./skills/<bucket>/<name>`。
4. `README.md` 的 User-invoked 或 Model-invoked 组加（或改、删）一行，名字链接到 `./skills/<bucket>/<name>/SKILL.md`；再建（或改名、删）`docs/<bucket>/<name>.md`。
5. 动到任一入口（`setup-case`、`doit`、`ask-loo0ng`）时，改 `ask-loo0ng` 自持的入口表（ADR-0005）。
6. 重跑 relink：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/link-skills.ps1`（只对靠 junction 的那一侧有意义；Claude Code 侧装了插件时脚本自动跳过那个目录，Codex 侧走 skills.sh 时不跑）。改内容不用重跑，只有改名、增删要。Claude Code 侧要看到改动得 `claude plugin update loo0ng-skills@loo0ng-marketplace`，它只取 GitHub 默认分支；要测未合并的分支，先按下面「分发事实」把市场换成本仓库绝对路径。
7. `npm run changeset` 写一条 changeset。
8. 跑下面的校验与测试。

## 三条校验命令

`claude plugin validate .` 有 `marketplace.json` 时只验它、不验 `plugin.json`；`plugin.json` 在 `--strict` 下因根 `CLAUDE.md` 的 warning 必败（Matt 自己的插件同样），所以拆三条（#18 项 2）：

```bash
claude plugin validate . --strict                    # marketplace.json，严格
claude plugin validate skills --strict               # 全部 skill 的 frontmatter，严格
claude plugin validate .claude-plugin/plugin.json    # plugin.json，非严格
```

## 其他检查

```bash
# 破折号：期望无输出
git ls-files -z | xargs -0 grep -l -I -P '\x{2014}'

# BOM：PowerShell 以外的文本文件不得带 BOM，期望无输出
git ls-files -z | grep -z -v '\.ps1$' | xargs -0 grep -l -I $'^\xEF\xBB\xBF'

# BOM：每个 .ps1 首三字节须为 ef bb bf
for f in scripts/*.ps1; do printf '%s ' "$f"; head -c 3 "$f" | od -An -tx1; done

# 版本一致：.claude-plugin/plugin.json 跟上 package.json（package-lock 不同步，照上游）
npm run check-plugin-version

# 结构与接线（照上游约定的四个检查，提交前必跑；Windows 上用 Git Bash 跑）
bash scripts/check-skill.sh .              # 每件 skill：name、description 引号、openai.yaml、双旗一致
bash scripts/check-wiring.sh .             # promoted 四处都在、非 promoted 四处都不在、plugin.json 路径真实
bash scripts/check-stale.sh . <旧名>       # 改名或删除之后：旧名字一处不留
bash scripts/check-release.sh .            # 发版前：changesets 配置、同步脚本、workflow、版本一致
```

## 测试命令

脚本层单测在 `tests/<名>/`，标准库 unittest，全部本地跑（ADR-0015）：

```bash
for d in tests/*/; do python -m unittest discover -s "$d" -p 'test_*.py' || exit 1; done
```

`tests/to-docx/` 分两条跑道（ADR-0017 改了 ADR-0015 的口径）：**推算层那条不起 Word，在任何机器上必须全绿、不许 skip**（`test_layout_estimate.py` 全篇，加 `test_gate.py` 与 `test_templates.py` 的无渲染跑道，合起来十几秒）；**渲染层那条要 Word COM**（`NormalAndFaultPairsRendered`、`TemplatesRegressionRendered`），每件门禁起一次 Word 约 7 秒、合起来约六分钟，缺渲染通道时整类 skip 并打印一行说明，不静默。只在开发侧跑，不进 Codex 的 30 秒 shell。别在门禁测试跑的同时另起 Word 出件，两件门禁同时跑会互相关掉对方的实例。

**3.9 那条跑道**：随包脚本的底线是 python 3.9（律师那台 mac 的 `/usr/bin/python3` 是 3.9.6），`tests/python-floor/` 只按形状扫，真跑要自己起一次。装一份钉住的后端再跑全套：

```bash
uv pip install --python <3.9 解释器> --target <临时目录> -r skills/in-progress/to-docx/requirements.txt
PYTHONPATH=<临时目录> <3.9 解释器> -m unittest discover -s tests/to-docx -p 'test_*.py'
```

2026-09-14 在 cpython 3.9.25 上跑过一遍：97 件全绿，14 件 skip（那台临时环境里没装 PyMuPDF，渲染层整类 skip，与主力环境一致）。

skill 层 eval：一个跑器两个后端，用例与种子在 `evals/`（ADR-0015，#25）：

```bash
python scripts/skill-eval.py --harness claude                 # Claude Code 侧，走 claude -p
python scripts/skill-eval.py --harness codex                  # Codex 侧，走 codex exec
python scripts/skill-eval.py --harness claude --case 冒烟     # 只跑一个用例；--case 可重复
python scripts/skill-eval.py --harness codex --runs 3         # 怀疑抖动时多跑几次
python scripts/skill-eval.py --harness claude --evals evals/自检   # 跑器自检用例（故意失败），不进门槛
python scripts/skill-eval.py --harness claude --case 回流 --model opus --effort high   # 换模型跑
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
├── 种子/<场景>/         # 收件箱/ 等直接拷进工作区的东西 + 回放.py + 状态.md；除「空目录」外每个回放都以真的起手 CLI 开头（#31；「逐节点回流」「活图多一件」「回流」先跑 `sketch.py home` 取活图路径，前两个再拿它 `init`，「回流」的案件那一层仍按包内出厂种子起手、活图只作回流的目标）
├── 共用/                # 跨用例、跨种子共用的几个模块，不是用例也不是种子（跑器按目录里有没有 用例.json 认用例，扫不到这里）：
│                        #   回放助手.py 七个路由种子共用的起手与写图动作（用活图() 把领域目录从包内种子换成一份活图，ADR-0019）；基线.py 三份图文件的 sha256（路由只读的判据）；
│                        #   路由断言.py ask-matt 五条验收项加「只指向表里的三个入口」，八个路由用例各 import 一遍；
│                        #   活图断言.py 活图在哪、回流前的逐文件 sha256，四个逐节点回流用例与用例「回流」各 import 一遍，种子「回流」的回放也读它（ADR-0019、ADR-0020）
└── 领域/<领域名>/领域图.json   # 脚本层用的合成小领域「菜园」（ADR-0015，#26），tests/graph 与 tests/domain 全用它跑；领域/说明.md 一段说明
```

ADR-0015「目录名保持 ASCII」只指 `tests/`、`evals/` 两个顶层；其下按仓库习惯用中文（ADR 自己的例子 `evals/种子/<场景>/` 即如此），`--case 冒烟` 直接传中文名。

`用例.json` 的键（多一个未知键即报错）：

| 键 | 含义 |
| --- | --- |
| `种子` | `evals/种子/` 下的场景名，本票允许为空 |
| `skill` | 编排 skill 名，可空。Claude Code 侧拼成 `/loo0ng-skills:<skill> <提示词>`（开发机 Claude Code 侧装的是插件，照上游一个 harness 只装一条路；`--claude-plugin ""` 退回 junction 路线的裸名 `/<skill>`）；Codex 侧用替身提示词「读 `~/.agents/skills/<skill>/SKILL.md` 并照做：<提示词>」，测的是正文不是触发，触发另由人工实测与完成定义那一次覆盖。带 skill 的用例必须有 `说明` |
| `回复正则` | 对最后一条回复做 `re.search`，可空；报红时断言名是「回复正则」 |
| `回合上限` | Claude Code 侧交给 `--max-turns`；Codex 侧数 JSONL 流里工具类 item（命令、改文件、MCP、搜索），超了杀进程树。默认 30 |
| `超时秒` | 单次调用的墙钟上限，超了杀进程树。默认 300 |
| `允许工具` | Claude Code 侧 `--allowedTools` 的列表（如 `["Bash(python *)"]`）；权限模式固定 acceptEdits。Codex 侧靠沙箱，不需要 |
| `Codex沙箱` | Codex 侧 `codex exec -s` 的值：`workspace-write`（默认）或 `danger-full-access`。**本套用例全在默认值上**（#78 实测全绿）：沙箱里起不来 Word COM（0x80070520 登录会话不存在）、`python` 也敲不动（那两个目录就在 PATH 上，只是沙箱账户读不到），但两样都不阻断：门禁本体零第三方依赖（ADR-0017），转换器的环境由 agent 自备、经 uv 走得通（ADR-0018）。`danger-full-access` 是跑器的能力，不是任何用例的前提 |
| `说明` | 一句话，含用例的局限；带 skill 时必填，写明替身提示词的局限 |

每次运行：在 `%TEMP%` 下建临时工作区 → 回放种子 → 调 harness（cwd 即工作区）→ 回复正则 → 逐条断言 → 删工作区（超时、超回合、断言抛错都删）。断言报红时给出函数名与 assert 的消息。

每次运行另在 `%TEMP%` 下建一个**活图家**，经环境变量 `LOO0NG_HOME` 交给 harness（ADR-0019）：领域目录的活图本来住 `~/.loo0ng/领域/`，eval 既不该往律师的主目录里拷东西，也不该吃上一次跑剩下的活图（ADR-0015 只生不存）。跑完连它一起删，`--keep` 时连它一起留并打印路径。两侧都吃这个变量（#90 实测 Codex 的 `workspace-write` 沙箱写得动 `%TEMP%` 下的它）。`--materialize` 生出来的工作区不设它，回放自己兜底：多数种子的领域目录本来就钉在包内的出厂种子上（`evals/共用/回放助手.py` 的默认值），那个工作区的指针块指的就是种子；调过 `用活图()` 的那几个（「逐节点回流」「活图多一件」「回流」）把活图落进工作区里的 `.活图家/`。**但兜底只管回放自己那几条命令，管不到 harness 里的模型**：模型自己跑 `sketch.py home` 时环境里没有这个变量，解析到的就是真的 `~/.loo0ng/`，一次关票触发就能写进开发者自己那份活图（#105 在 Codex 侧实测到；用例「回流」的提示词不再给路径之后，这条路才走得到）。所以 `--materialize` 回显里带上这次要设的 `LOO0NG_HOME`，关票触发之前把它设进环境；eval 那条路由跑器统一设，碰不到真的主目录。

种子接口（实现随起手票）：`evals/种子/<场景>/` 里除 `回放.py` 与 `状态.md` 之外的条目原样拷进工作区，再在工作区里跑 `python 回放.py <工作区>`；起手（`setup-case`）、引擎 CLI、归档脚本都写在回放里，跑器不另定回放格式。

Windows 上工作区用 `os.mkdir` 而不用 `tempfile.mkdtemp`：后者建的目录只有 SYSTEM、Administrators、OWNER RIGHTS 三条 ACE，Codex 沙箱账户写进去的文件本用户读不了也删不了。

合入门槛 = 脚本层全绿 + 两侧 eval 全绿 + 三条校验；关票门槛 = Codex 与 Claude Code 各真实触发一次（ADR-0015）。**改造期按件收（ADR-0022）**：`in-progress/` 里的件提交前只跑 `check-skill.sh`、`check-wiring.sh` 与 `claude plugin validate`；一件毕业时它的单测与 eval 随脚本与正文重定，留下的才重新成为它的门槛。

全绿只有一件例外：Codex 侧的 `出雏形` 列为已知抖动，单件红放行（律师 2026-09-08 裁定，#68；见 ADR-0015 的同日附注）。只对这一件、只在 Codex 侧、且只在其余各件全绿时成立；别的用例红仍是阻塞，PR 里要点名这件红并写明与本票无关。

### 关票触发怎么做

触发在**从种子生出的临时工作区**里做，跑完即弃（ADR-0015 与 ADR-0009 的 2026-09-07 附注，#66）。

案件根下还留着几个目录名带「合成」字样的常驻工作区（#32 起攒下来的，现在三个：两个整份起手、一个空图起手），它们是**手工探索的现成起点**：想在一个办到一半的案子上试打一句、看看回显长什么样，不必等回放。**它们不承担任何门槛**：关票不在它们上面做，合入也不看它们，因此也不必为它们定「什么时候重建」的规矩，脏了就脏了。理由是改图不可逆（节点永不删、不适用是终态，ADR-0003），在常驻目录上触发留下的痕走支持的路子撤不掉，撤只有标不适用（残渣更多）或手改 `图.json`（不受支持）两条。路径不写进仓库与 issue（硬边界 1）。

```bash
# 1. 生一个工作区：打印路径就停，不跑 harness、不删
#    活图在工作区里的种子（「逐节点回流」「活图多一件」「回流」）还会多回显一行 LOO0NG_HOME=<…>
python scripts/skill-eval.py --materialize 在办中

# 2. Claude Code 侧（开发会话里就能跑，打的是真名，算真实触发；插件路线带 loo0ng-skills: 命名空间）
cd <上一步打印的路径>
export LOO0NG_HOME=<上一步回显的那个>   # 回显了就必须设：不设的话模型自己跑 home 会写真的 ~/.loo0ng
MSYS_NO_PATHCONV=1 CLAUDECODE= CLAUDE_CODE_ENTRYPOINT= \
  claude -p "/loo0ng-skills:<skill 名> <律师那句话>" --output-format json \
  --permission-mode acceptEdits --no-session-persistence --allowedTools Bash

# 3. Codex 侧：只能人工，在客户端里 cd 到同一个路径再打 $<skill 名>；
#    回显了 LOO0NG_HOME 就先在那个终端里设好，客户端继承的是它自己的环境

# 4. 用完删掉那个目录
```

种子挑与要验的路径最接近的那个：`在办中` 是办到一半（12 模块 72 节点、一份已确认一份待确认），`空目录` 用来验起手，`图引擎` 是合成小领域「菜园」，`逐节点回流` 是「菜园」上一个待确认节点加一份活图（它的回放在 `LOO0NG_HOME` 没设时把活图落进工作区里的 `.活图家/`，所以 `--materialize` 出来的那个也碰不到真的 `~/.loo0ng/`）。

**第 2 步那行与跑器给 Claude Code 侧拼的命令是同一条**（`build_command`），差别不在命令而在别处：打的是你自己想打的那句话（不是用例里的提示词）、看的是回复本身（不跑断言）、判的是人。所以 Claude Code 侧这一次相对合入门槛那次 eval 的增量本来就小，两道门在这一侧几乎重合；增量大的是 Codex 侧，那边 eval 用的是替身提示词、根本没测触发（ADR-0015）。这条局限照实记着，别把它当成两次独立的证据。

**Codex 侧那一次只能人工**：`$名` 在 AFK 下不解析（`codex debug prompt-input '$名 …'` 可复核：那一串原样留在用户消息里，`SKILL.md` 正文一句都不进 prompt），显式触发的 skill 因此在 `codex exec` 下触不到。律师在客户端里打的是带前缀的 `$loo0ng-skills:<名>`，靠补全 tab 选中（#44）。

关票评论按 ADR-0009 只记日期、平台、打的名、结果类别，并写明材料是合成的。验到的与验不到的要分清：验到的是**这条安装路线下**按名字触发、流程走通（Claude Code 侧是插件路线的 `/loo0ng-skills:<名>`，Codex 侧是客户端里带前缀的 `$loo0ng-skills:<名>`）；验不到的是真实案件材料下的判断，也验不到插件路线的 `/loo0ng-skills:<名>`（那条另由「两平台注册、补全与拉取实测」与 #44 覆盖）。工作区路径不写进 issue（硬边界 1）。

## 发布

改名、改功能都是一次发布，只在开发者维护时做（ADR-0009）。发布链照上游（ADR-0021）：

1. 每次会让律师感知的修改，写一张 changeset（`npm run changeset`，或手写 `.changeset/<slug>.md`：frontmatter 是 `"loo0ng-skills": patch|minor`，正文是给律师看的一段话，会原样进 `CHANGELOG.md`）。改文档、脚本、测试不写。
2. 推到 `main`。`.github/workflows/release.yml` 里的 changesets/action 发现有待消费的 changeset，跑 `npm run version`（`changeset version` 结算版本与 `CHANGELOG.md`，再 `node scripts/sync-plugin-version.mjs` 把版本抄进 `.claude-plugin/plugin.json`），开一个 "chore: version skills" 的 PR；后续再进 changeset 它自动更新。
3. 读那个 PR 的 diff（就是 CHANGELOG 的预览），顺了就合并。合并后 action 再跑一次，这次没有 changeset 了，执行 `npx changeset tag` 打出 `v<version>`。
4. `plugin.json` 的 version 变了，装了插件的机器才会收到更新；skills.sh 路线要律师自己 `npx skills update`。

级别照上游用法：patch 是修 bug、措辞、单件行为微调；minor 是新增或毕业 skill、改名（正文以 **Breaking:** 开头，说明无别名需重装）；major 上游没用过。

本地也能跑同一条链（`npm run version` → 提交 → `npx changeset tag`），但 CI 是常态。仓库设置里 Actions 的 "Allow GitHub Actions to create and approve pull requests" 必须勾上，否则开不了 PR。

上 CI 的只有发布这一条路：ADR-0015 的 2026-09-12 附注把「全部本地不做 CI」的射程划回测试与门禁那一层，脚本层单测、两侧 eval、版式门禁仍然全部本地跑。离线兜底包不再随 Release 附带（ADR-0021）；要给断网的律师机装，直接拷 `skills/in-progress/` 下的七个目录。

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
2. **登记不变量跨仓库**：`AGENTS.md` 结构不变量 1 的几处登记（`skills/<bucket>/<name>/`、桶 README、`.claude-plugin/plugin.json`、根 `README.md`、docs 页）会落在两个仓库里，上面的校验命令不再是在一个工作副本上跑得完的。
3. **入口显示名可能从裸名变成带前缀**：Codex 显示裸名还是 `loo0ng-skills:<名>`，取决于装到 `~/.agents/skills/` 的那个目录上面找不找得到一份 Codex 插件清单（本仓库已不带，ADR-0021）（`docs/交付/现场清单.md` 1.5 的实测）。律师那台机器走的是路 A，直接拷目录，现在看见的是**裸名**；拆出分发仓库之后若改走那个仓库的插件市场装，同一件 skill 就显示成 `loo0ng-skills:<名>`，`ask-loo0ng` 的入口表、打法段与教律师打的那一串跟着都要改。
