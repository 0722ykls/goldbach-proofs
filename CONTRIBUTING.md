# 参与数学猜想协作平台 / Contribute to the Open Conjecture Platform

在[猜想目录](https://www.goldbach.tech/problems/?lang=zh)选题后，请复制对应分站的提示词。下方默认命令适用于哥德巴赫主站，其他分站请使用各自指南里的问题参数。

## 数学研究管理员 / Research maintainers

希望主持一道猜想的研究方向，可以发起路线 PR，写明想负责的猜想、依据文献、下一条可独立验证的引理及其依赖。主项目使用 `research/gaps.json`，其他研究台使用 `research/problems.json`。请邀请另一位审查者核对命题的量词、假设和结论，由仓库维护者合并。证明贡献者继续通过各自研究台领取任务。

To propose a research direction, open a roadmap PR identifying the conjecture, sources, next lemma and its dependencies. Ask a second reviewer to compare the formal and informal statements before a maintainer merges the change.

## 用自己的 Agent 参与 / Bring your own agent

复制站点上的参与提示词给编程助手，由助手领取一条引理并按完整流程提交。也可以自己执行同一份指南。 [中文参与指南](https://www.movan.tech/goldbach/join-zh.txt) · [研究台](https://www.movan.tech/goldbach/)

Give the participation prompt to a coding agent to claim a lemma and follow the full submission flow. The same instructions work for manual contributions. [English joining guide](https://www.movan.tech/goldbach/join.txt) · [Research desk](https://www.movan.tech/goldbach/?lang=en)

1. 在专用 checkout 运行 `python tools/goldbach.py claim`，使用分配的单个 Lean 文件、定理名和冻结命题。
2. 向默认分支创建只新增这一文件的 PR。
3. 用领取任务时的同一 GitHub 账号运行 `python tools/goldbach.py submit PR_NUMBER`。工具登记确切的提交，并由 PR 作者发布 `/goldbach-check GAP_ID`，触发权威验证。
4. 合并前对照运行报告中的 head、命题哈希和结果。

1. Run `python tools/goldbach.py claim` in a dedicated checkout and use the assigned Lean file, theorem name, and frozen statement.
2. Open a PR against the default branch that adds exactly that file.
3. From the same GitHub account, run `python tools/goldbach.py submit PR_NUMBER`. The helper registers the exact head and posts `/goldbach-check GAP_ID` as the PR author to request authoritative verification.
4. Verify the recorded head, statement hash, and result before merging.

命题进入清单前，由另一位审查者逐项比对中英文表述、Lean 类型、量词范围以及依赖。提交者以已登记的命题为准。 [命题清单](research/gaps.json)

A second reviewer checks the English and Chinese statements against the Lean type, quantifier bounds, and dependencies before publication. Use the registered statements when submitting proofs. [Statement registry](research/gaps.json)
