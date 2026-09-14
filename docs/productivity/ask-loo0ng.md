## What it does

`ask-loo0ng` 是一张只读的地图。你说一句话，它读案件图与领域图，告诉你这个案件走到哪一步、当前节点、上一完成、下一任务、往下几步各自的拍板点，最后把下一句该打的整串写出来，然后停。

它不触发任何 skill、不写图、不替你按下去。用不用它，案件都走得一样：它的回答不成为图里的状态，每次回答都是完整的，不接上一次。

## When to reach for it

你打 `/ask-loo0ng`（Codex 里 `$ask-loo0ng`）加一句话触发它，怎么问都行；模型不会自己调它。随时可问，也可以一直不问。

| 你想 | 用什么 |
| --- | --- |
| 知道我在哪、接下来做什么、下一句打什么 | `ask-loo0ng` |
| 真的去办某个节点 | [loo0ng-doit](https://github.com/f4de01/lawyer-workbench-v3/blob/main/docs/productivity/loo0ng-doit.md) |
| 改图的构成 | 一句话说给模型，它调用 [loo0ng-graph](https://github.com/f4de01/lawyer-workbench-v3/blob/main/docs/productivity/loo0ng-graph.md) |

## Prerequisites

会话当前目录是案件工作区（有 `图.json`）。没有它就说没有；还没起手先打 [loo0ng-setup-case](https://github.com/f4de01/lawyer-workbench-v3/blob/main/docs/productivity/loo0ng-setup-case.md)。

## 五问有序决策树

下一任务由五问按顺序定，第一个 yes 胜出，回复里标出命中哪一问：

1. 案件图里有已生成、等你确认的文书吗？有，先确认它们。
2. 案件图里有未生成的节点吗？有，出图里顺序最早的那个。
3. 最近动过的那个模块，领域图里还有案件图没有的节点吗？有，顺着这一块做完。
4. 领域图里还有案件图没有的节点吗？有，回头补空。
5. 都没有，无事可做。

时限不进这棵树。带时限的节点，领域图上那句话原样附在「往下的路」里，判断留给你，顺序不因它改变。

回复固定五段、段序不变：你在哪、三问、往下的路、相近入口分界线、下一句该打什么。

## Common questions

**Codex 里打 `$ask-loo0ng` 找不到。**
取决于装法。插件路线装上的 skill 带前缀，打的是 `$loo0ng-skills:ask-loo0ng`，补全按子串匹配，打 `ask` 再按 tab 选中就行；用 skills.sh 装的或直接拷进 `~/.agents/skills/` 的显示裸名。列表二十几项，只打一个 `$` 反而不好找。

**它说「对不上」是什么意思？**
你说的那件事在案件图与领域图里都找不到。它不猜、不造入口、不新建节点，只给出 `loo0ng-doit 出一版 <你说的标题>` 这一串，那个入口会按你说的标题把节点建进图再出件。

**它读材料吗？**
不读。它只读两张图，不读材料、不读律师陈述、不读文书正文，所以算不出本案真正的截止日，任何「临近」的判断它都不做。

## It's working if

- 回复恰好五个二级标题，名字一字不差，末段之后再无正文。
- 「下一句该打什么」那一串可以原样粘贴进新对话。
- 跑完之后 `图.json` 与两份视图一个字节都没变。
- 带时限的节点在「往下的路」里附了「时限：…」一行，原句照抄。
- 凡对某个入口行为的断言，末尾都有「以它们各自的 `SKILL.md` 为准」那一行。

## Where it fits

`ask-loo0ng` 是整套 skill 的**路由**，一个随时可用的只读入口，永远不是流程里的一步。它把你送到 [loo0ng-setup-case](https://github.com/f4de01/lawyer-workbench-v3/blob/main/docs/productivity/loo0ng-setup-case.md)（起手）或 [loo0ng-doit](https://github.com/f4de01/lawyer-workbench-v3/blob/main/docs/productivity/loo0ng-doit.md)（办节点）这两个入口，自己不动任何东西。图的字段与状态的权威是 [loo0ng-graph](https://github.com/f4de01/lawyer-workbench-v3/blob/main/docs/productivity/loo0ng-graph.md)。
