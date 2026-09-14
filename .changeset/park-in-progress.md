---
"loo0ng-skills": minor
---

**Breaking:** 七件 skill 全部搬进 `skills/in-progress/` 逐件重做（ADR-0022）。改造期间 Claude Code 插件清单为空，`claude plugin update` 之后装到的是空包；要继续用请留在 0.4.0，或走 skills.sh 单件装：`npx skills@latest add f4de01/loo0ng-skills --skill=<name>`。skill 名与打法没有变，已起手的案件工作区不受影响。ADR-0001 至 0021 同时降为参考，与 skill 正文冲突时以正文为准。
