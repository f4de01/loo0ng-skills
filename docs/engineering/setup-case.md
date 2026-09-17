## What it does

`setup-case` 把当前目录长成一个案件工作区，一案一次。它只问你一件事：**空图，还是用哪一份预设图起**（随包出厂的与你自己存下的分两组列给你）。你选了之后一条命令落下全部东西：

```
<案件工作区>/
├── 图.json  图视图.md  图视图.json  AGENTS.md  CLAUDE.md
├── 待归档/                   ← 你原本堆在这个目录里的东西都在这里
├── 材料/
├── 参考/模板/  参考/指南/
└── 文书/                     ← <模块>/<节点>/ 出件时才建
```

选了预设图，它的模块、节点、空白模板文件名与时限句一次拷进案件图，`模板/` 整份拷进 `参考/模板/`。之后这张图**自足**：接下来该办什么只从它自己算，不再回头看预设图。

工作区根的 `AGENTS.md` 只记四项：预设图的名与归属、图与视图的文件名、入口名、「本工作区对 skill 仓库只读」。**一条路径都不记**：记下来，skill 包一升级那条路径就死了。

## When to reach for it

在一个新案子的目录里打 `/setup-case`，一次。**目录里已经堆着文件不妨**：它们一律当作待归档，由起手挪进 `待归档/`，该归到哪是下一步的事。

已经有 `图.json` 的目录它会拒绝：那个目录已经是案件工作区，要改图的构成在对话里说一句（走 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)），要另起一案换一个目录。

## 一问二选，定的是这张图的起点

起手前不必先整理材料，也不必先报一个领域名。**一问二选**只让你决定这张案件图从哪里长出来：

| 你选 | 起手后手里有什么 |
| --- | --- |
| 空图 | 案件工作区与一张空图，节点之后按本案需要添加；`参考/模板/` 先空着 |
| 一份预设图 | 已排好的模块、节点、时限句与配套空白模板，可以接着办节点 |

出厂与个人预设图分两组列，只有一份也不替你选；同名时按归属分清。你已经说了「用破产那份」，就不再重复问。拷入之后，案件图按本案自己的条目往下走，后来加节点、调顺序都改本案这张图。

空目录就能起手。脚本只用 Python 标准库，支持 Python 3.9；填模板所需的环境在出件时自备，不必在起手前配好。

## 起手清单，把搬文件与登记成品放在一起拍板

一个目录里可能同时有事实材料、空白模板和已经写好的文书。**起手清单**把它们的去向放在同一处，让你一次看完、一次决定：

| 清单里的内容 | 你要决定什么 |
| --- | --- |
| 归档去向 | 文件归材料、参考/模板还是参考/指南，旁边附一句理由 |
| 既有成品 | 已写好的文书是否登记到建议的节点，登记后是已生成未确认 |
| 同名冲突与拿不准的文件 | 逐件决定去向；没有定下来的继续留在待归档 |

这时目录和图已经建好，原有文件已挪进 `待归档/`；从待归档搬到清单建议的位置、登记既有成品，要等你那一句话。「都按建议来」可以整张通过，「第 3 条不要」也可以只改一条。没有文件要归，就没有这张清单，也不多问一次。

## Common questions

**目录里已经有材料或写好的文书，还能起手吗？**
能。已有文件与子目录先挪进 `待归档/`，点开头的项目（如 `.git`）不动。起手清单把归档去向、建议登记的既有成品、冲突放在一起，等你一句话才归档、登记；既有成品只登记为已生成，不自动确认。没有文件要归就没有这次拍板。出处：[CHANGELOG 0.6.0，起手重做](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**以前的领域名、三选一和自动提节点去哪了？**
现在只选空图或一份预设图，不再问领域名。空图不拷模板；选预设图就整份拷入图与配套模板。起手不再因为指南非空而自动提节点，需要时说「从这份指南里提节点」，由 `domain` 先给雏形，拍板后再写图。出处：[CHANGELOG 0.6.0，起手与 domain 重做](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

**旧的 `loo0ng-setup-case` 找不到了，插件还装过空包？**
0.4.0 去掉了六件 skill 的 `loo0ng-` 前缀，没有旧名别名，路由仍叫 `ask-loo0ng`。0.5.0 七件进 `in-progress/` 重做时插件清单曾清空，0.6.0 已恢复七件。旧名安装按 [README 安装说明](https://github.com/f4de01/loo0ng-skills/blob/main/README.md)重装；旧工作区指针块中的入口名也要改成新名，改名本身不改变图与文书。出处：[CHANGELOG 0.4.0](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#040)、[0.5.0](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#050)、[CHANGELOG 0.6.0，七件回归分发](https://github.com/f4de01/loo0ng-skills/blob/main/CHANGELOG.md#060)。

## It's working if

- 目录形状、`图.json` 与两份视图一次落齐，你原本堆在目录里的东西都在 `待归档/`。
- 收尾第一段是固定五行：目录与图、起手图、待归档、归档、既有成品，件数逐个写实。
- `AGENTS.md` 里只有名与归属，翻遍找不到一条路径。
- 没有任何节点被自动确认。

## Where it fits

起手是主线第 1 步，跑完就交给 [doit](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/doit.md) 办第一个节点。它自己不出件、不确认：清待归档调 [filing](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/filing.md)，预设图的列表与路径调 [domain](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/domain.md)，写图经 [graph](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/graph.md)。不知道下一步做什么就打 [ask-loo0ng](https://github.com/f4de01/loo0ng-skills/blob/main/docs/engineering/ask-loo0ng.md)。
