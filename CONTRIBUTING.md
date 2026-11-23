# 提交证明 / Submit a proof

从 [命题清单](research/gaps.json) 选择一项，在清单指定路径新增唯一一个 Lean 文件。定理名称和类型使用 `module` 和 `statement` 字段。提交只含该文件的 PR。维护者在默认分支运行 authoritative，输入 PR 编号和引理 ID。合并前对照运行报告中的提交、命题哈希和结果。

Pick a row in the [statement registry](research/gaps.json). Add exactly one Lean file at its listed path and use the listed module as the theorem name. A maintainer dispatches authoritative on main with the PR number and lemma ID. Verify the recorded commit and statement hash before merging.

命题进入清单前，由另一位审查者逐项比对中英文表述、Lean 类型、量词范围以及依赖。提交者不能自行更改已登记的命题。
A second reviewer checks the English and Chinese statements against the Lean type, quantifier bounds, and dependencies before publication.
