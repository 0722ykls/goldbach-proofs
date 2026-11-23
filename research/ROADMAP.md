# 研究路线 / Research roadmap

| 阶段 / Stage | 交付与验收 / Deliverable and acceptance |
|---|---|
| 1. 基线 / Baseline | 用 4 和 10 的显式素数见证跑通核验。另用错误命题或带 sorry 的候选检查拒绝路径。 / Check explicit witnesses for 4 and 10, then exercise rejection with an invalid candidate. |
| 2. 有限区间 / Finite ranges | 定义表示谓词，证明可执行素数搜索与该谓词等价。按区间产生见证并验证无缺口覆盖，记录精确上界。 / Prove search soundness and completeness, then certify contiguous bounded ranges. |
| 3. 分析数论 / Analytic number theory | 分别研究素数计数、筛法和表示数下界；用 Helfgott 三素数结果与显式陈氏定理作为独立复现目标。 / Develop prime counting, sieves, and representation bounds. Use ternary Goldbach and explicit Chen as separate reproduction targets. |
| 4. 无界目标 / Unbounded target | 冻结强猜想的量词和边界。若取得严格的最终阈值，证明阈值以上覆盖，并对阈值以下提供独立证书。 / Combine a proven eventual bound with verified coverage below its threshold. |

- [Helfgott, The ternary Goldbach problem](https://arxiv.org/abs/1501.05438)
- [An explicit version of Chen's theorem](https://arxiv.org/abs/2207.09452)

按 2,000 分钟预算，仅计 75 秒检查，可完成约 1,600 次。每次按 250 秒或 848 秒估算，则分别为 480 或 141 次。300 个任务在 3 个并行槽位、每批耗时固定为 75 / 250 / 848 秒的模型下，清空队列约需 2 小时 5 分钟 / 6 小时 56 分 40 秒 / 23 小时 33 分 20 秒。实际还要加上 runner 排队、Lean 安装、Mathlib 缓存和全套构建。三个槽位是估算假设。
