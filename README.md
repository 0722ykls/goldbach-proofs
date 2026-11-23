# Goldbach Proofs / 哥德巴赫证明项目

目标是研究强哥德巴赫猜想：每个不小于 4 的偶数都是两个素数之和。猜想仍然开放。项目使用固定版本的 Lean 4 和 Mathlib 验证独立引理。

The strong Goldbach conjecture states that every even natural number at least 4 is a sum of two primes. It is open. This project checks individual lemmas with pinned Lean 4 and Mathlib.

- [研究路线 / Research roadmap](research/ROADMAP.md)
- [待验证命题 / Published statements](research/gaps.json)
- [权威验证 / Authoritative verification](.github/workflows/authoritative.yml)

保留上游的 `PEqualNP` Lean 命名空间和验证器。这个项目的命题来自默认分支的清单。
The upstream checker and Lean namespace are retained. This project's statements come from the default branch.

Apache-2.0. [Upstream](https://github.com/brilliant-hq/pequalnp-proofs).

前端参考 pequalnp 的公开首页、实时活动栏和可钻取的研究地图，界面数据由本站的任务清单及核验记录提供。可对照[原站设计说明](https://pequalnp.com/how)、[设计画布](https://brilliant.design/brilliant/pnp)、[首页脚本](https://pequalnp.com/assets/fda04e88f715/js/home.js)及[地图脚本](https://pequalnp.com/assets/fda04e88f715/js/map.js)。
