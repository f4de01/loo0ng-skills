## What it does

`domain` 是一个领域的三样内容的家：领域图、官方模板原件、指引手册原文。三样都是原件或图，没有摘要层。它另持有把指南变成图里模块与节点的唯一机制，雏形：模型整读指南写成雏形文件，CLI 按标题判重、回显清单，你一句话拍板后才经图引擎写入。

未拍板不写图。它不含任何领域语义：判重、写入、读 docx 都不认「破产」两个字，换一个领域只换目录。

## When to reach for it

你一句话说「按这份指南出雏形」「从指南里提节点」「指南里还有哪些没建」「官方模板原件在哪」「领域图在哪」，模型自行调用它。起手末尾归档后 `指南/` 非空，[setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md) 调它出起手清单里的雏形；你确认一个领域图里没有的节点之后，[doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 按它的口径问一次归属。

改图的其他构成与追加条目归 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)；把指南搬进 `指南/` 是归档，归 [filing](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/filing.md)。

## Prerequisites

活图住 `~/.loo0ng/领域/<领域名>/`，第一次起手这个领域时从 skill 包内的出厂种子整份拷出。模板与手册是 docx，harness 读不了，用它的 `docx-text` 打成纯文本整读。

## 活图与出厂种子

| 哪一份 | 在哪 | 谁写 |
| --- | --- | --- |
| 活图 | `~/.loo0ng/领域/<领域名>/` | 唯一写得动的一份：律师办案时逐节点长，开发者对手册跑雏形、批量回流也写它 |
| 出厂种子 | skill 包内 `assets/<领域名>/` | 谁都不许在会话里写，引擎无条件拒；升级时整个被换掉；改由入库更新 |

内置的领域是「破产」：19 件官方模板、2 份指引手册、由手册长出的 12 个模块 72 个节点。

雏形四步：整读来源，写雏形文件到临时目录（不落进工作区），`check` 判重回显（同名不再提、相似不同名列为待定），你一句话之后 `apply`。有一条待定没定，`apply` 整个拒、一字不写。

## Common questions

**升级 skill 包会不会抹掉我累计半年的领域图？**
不会。这正是活图搬出包外的理由：包内那份降为出厂种子，升级只换种子，活图一个字不动。仓库里有一条测试模拟一次升级，断言活图逐字不变。

**我想做一个全新领域，从哪起？**
开发侧走律师那条路：`home --empty` 在活图位置起一份空领域图，办一遍案子、逐节点回流进自己的活图，攒够了 `intake` 入库成为出厂种子。律师侧不必管这些：起手时给一个此前没有的领域名，就是新领域从空图起手。

**`check` 之后为什么还要我说一句？**
清单之外不加判断，也不先写再问。未拍板不写图，与逐节点回流同一条规矩。

**`intake` 会把整个领域目录搬进仓库吗？**
只拿 `领域图.json`。官方模板原件与指引手册原文走普通的 git 添加。拷之前先校验，再把这次比种子多了什么、改了什么分栏回显，那是第二双眼之前的第一道人眼过滤。

**`loo0ng-domain` 去哪了？**
改名为 `domain`（2026-09-13，ADR-0009 附注）：六件都去掉了 `loo0ng-` 前缀，只有路由还叫 `ask-loo0ng`。没有别名，装了旧名的机器按 README 重装。

## It's working if

- 第一次在某领域上起手后，`~/.loo0ng/领域/<领域名>/` 出现三样：`领域图.json`、`模板/`、`指引手册/`。
- 重装 skill 包之后活图逐字不变。
- 雏形清单回显在你说话之前，图一个字不变；相似不同名的列在「待定」而不是被自动合并。
- 案件图上时限句只回显不写。

## Where it fits

`domain` 是参考层，领域内容的家与雏形机制的主人。它的写入全经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md) 的引擎；起手时把官方模板拷进工作区是 [setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/setup-case.md) 做，出件读它是 [to-docx](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/to-docx.md) 做。整套 skill 的路由是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。
