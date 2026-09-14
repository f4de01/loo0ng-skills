## What it does

`loo0ng-graph` 持有 `图.json` 的唯一写入口：一个零依赖的 CLI。你一句话改图的构成（加节点、改标题、调顺序、跨模块移动、改空白模板、增删改模块、节点或模块不适用）由模型调它落盘并回显；编排 skill 追加生成与确认条目也调它；每次写图后它重算 `图视图.md` 与 `图视图.json`。

条目只追加，节点永不删，不适用是终态。改构成没有确认点：你说了就落，回显照读给你。

## When to reach for it

你一句话说到加节点、改标题、挪顺序、某节点或整个模块不适用，模型自行调用它；也可以直接打 `/loo0ng-graph`。

| 你说 | 它跑 |
| --- | --- |
| 在某模块下加一个节点 | `add-node` |
| 把某节点标题改成…… | `rename-node` |
| 某节点挪到某节点前面 / 挪到某模块下 | `move-node` |
| 某节点用某模板 / 不用模板 | `set-template` |
| 加一个模块 / 模块改名 / 删空模块 | `add-module` / `rename-module` / `delete-module` |
| 某节点不适用 / 整个模块不适用 | `not-applicable` |

出一版与确认是 [loo0ng-doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-doit.md) 的事，它再来调本 skill 落条目。从指南批量长出模块与节点走雏形，是 [loo0ng-domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-domain.md)。

## Prerequisites

会话当前目录是案件工作区（有 `图.json`）；领域目录的路径从工作区 `AGENTS.md` 里读。脚本跑得动 python 3.9。

## 活图与出厂种子

领域图用同一引擎，加 `--kind domain`。同一个领域有两份：律师本机 `~/.loo0ng/领域/<领域名>/` 那份**活图**是唯一写得动的一份；skill 包内 `assets/<领域名>/` 那份**出厂种子**谁都写不动，开发会话也不行，引擎无条件拒、没有放行口。种子随包分发，写进去的东西下一次升级就被整个换掉；它改由入库更新。读种子照旧：`validate`、`views`、拿它当领域图来源起手都不受影响。

## Common questions

**我想删掉一个节点。**
节点永不删，答复是记不适用，误加的也一样。不适用是终态，已确认的节点不能不适用，要改就重出一版。

**引擎说「不合校验」。**
`图.json` 被手改过或损坏了。从上一次能用的状态重来；模型自己修改 JSON 是这条规矩的反面，律师手改 `图.json` 也不受支持。

**写领域图被拒，说这是「包内出厂种子」。**
这个工作区的领域目录还指着 skill 包内的种子（0.1.0 起手、没手改过那一行的工作区就是这个形状）。把工作区 `AGENTS.md` 里「领域目录」那一行换成活图路径，之后每个节点照常写得进。

**在 mac 上一次都写不成图。**
律师那台 mac 的系统 python 是 3.9.6，引擎曾用了 3.10 才有的 `Path.write_text(newline=)`。已修，仓库里有一条测试守着随包脚本的 3.9 底线。

## It's working if

- 你一句话之后 `图视图.md` 立刻变，回显是 CLI 的原话。
- 引擎拒写时文件一字不动，原因在 stderr，模型把它照实转告而不是绕过去。
- 图里找不到「删除」这回事，只有不适用。
- 案件图里给节点写时限会被拒：时限只住领域图。

## Where it fits

`loo0ng-graph` 是参考层，所有写图都经它：[loo0ng-doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-doit.md) 的生成与确认条目、[loo0ng-setup-case](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-setup-case.md) 的起手图、[loo0ng-domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/loo0ng-domain.md) 的雏形写入，都是它的子进程。它不出 HTML、不做可视化。整套 skill 的路由是 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/productivity/ask-loo0ng.md)。
