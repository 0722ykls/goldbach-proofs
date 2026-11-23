# 强哥德巴赫研究路线 / Binary Goldbach roadmap

2026-11-23 · [English](#english) · [已上线的引理 / Live tasks](gaps.json)

令 $R_2(n)$ 为满足 $p\le n$、$p$ 与 $n-p$ 均为素数的自然数 $p$ 的个数。顺序计数，例如 $R_2(10)=3$，对应 $3+7,5+5,7+3$。项目的目标是对**每个** $n\ge4$ 的偶数证明 $R_2(n)>0$。令 $E(X)$ 计数 $[4,X]$ 中 $R_2(n)=0$ 的偶数。证明 $E(X)=0$ 对所有自然数 $X$ 成立，也是同一目标。[仓库中的最终命题](strong-goldbach.lean)

## 为什么调整路线

11 月 20 日，Levent Alpöge 公布了与 Claude 合作的 Lean 形式化，其中既有 ζ 函数的黎曼猜想（RH），也有所有正整数模数、所有狄利克雷特征的 L 函数版本（Dirichlet GRH）。截至 11 月 23 日，MIT 的 Andrew Sutherland 和滑铁卢的 Michael Rubinstein 都报告了独立的内核复核。后一类零点与**同余类中的素数计数**有关，在圆法中可用来估计靠近小分母有理数的主弧贡献。给定偶数 $n$ 时，还得证明素数与其反射集合 $n-\mathbb P$ 相交；两个集合各自的计数没有给出这个交集的逐点下界。[作者公告](https://alpo.ge/remark.pdf) · [MIT 核验记录和五条命题](https://math.mit.edu/~drew/grh/) · [滑铁卢核验](https://mrubinst.github.io/grh-lean-verification/) · [二元圆法与主弧公式](https://arxiv.org/abs/2607.27282)

## 任务顺序与验收

下面是研究排期。领取入口只发布经过独立语义复核的冻结命题。学术来源、草案和本项目已获 Lean 判定的命题分别追踪。[已发布命题](gaps.json) · [本项目核验记录](https://www.movan.tech/goldbach/#records)

| 优先级与负责人 | 工作与依赖 | 验收条件 |
|---|---|---|
| P0 · 定义组 | 统一表示谓词、有限计数 $R_2$ 和 $E$。先证明对任意自然数 $n$，$0<R_2(n)$ 当且仅当存在素数 $p,q$ 使 $p+q=n$。 | 固定到受信定义和标准的 `Nat.Prime`。逐项核对量词、自然数减法边界、$2+2$ 与对角线 $5+5$，经 Lean 判定。后续两组共用这一定义。 |
| P0 · 证书组 | 与定义组并行设计分块见证。每个偶数给一个素数 $p$，检查 $p\le n$ 及 $p,n-p$ 的素性。证明证书可靠性与相邻偶数区间拼接。 | 首个目标是闭区间 $[4,1000]$ 的全部 499 个偶数。只公布从 4 起连续通过内核核验的最大终点。用漏掉一个偶数和填入合数的证书检查拒绝路径。 |
| P1 · 解析组 | 复现 Chirre–Hagen 的短区间定理。先冻结第 5 节的归约：区间内若无两奇素数之和，就得到塞尔伯格积分的下界；与解析上界结合得到矛盾。再分别处理该上界所需的 ζ 零点估计与显式常数。 | 先交大参数结果，保留普通 RH 前提。论文从 $x\ge1.1\times10^{18}$ 起使用解析论证，较小范围引用既有计算。要把结论扩展到每个实数 $x\ge2$，需独立核验有限覆盖或给出替代论证。最终目标是在 $(x,x+123(\log x)^2]$ 内找到一个两奇素数之和。[论文第 5 节](https://arxiv.org/html/2512.23534v1#S5) |
| P1 · 依赖审计组 | 与解析组并行。固定上游档案哈希、Lean 4.33.1 / Mathlib 版本和实际所需的定理。对照项目锁定的 Lean 4.36.0，先比对 RH 以及全模数狄利克雷零点命题。 | 记录类型、版本、允许公理与独立复核日志。评估本项目能否重放所需依赖。接入前保留具名定理前提；大型上游证明无需随每份 PR 重新编译。[档案哈希、声明和实测资源](https://math.mit.edu/~drew/grh/) |
| P2 · 解析组 | 在 P0 定义上研究例外集。按 Pintz–Althöfer 预印本逐条审查其狄利克雷零点假设、指数和估计、隐常数依赖及适用范围。 | 中间目标是对每个 $\varepsilon>0$，在论文假设下得到 $E(X)\ll_\varepsilon X^{1/2+\varepsilon}$。该指数来自论文公式取 $\theta=1/2$。即使只有稀疏的无限多个例外，这类界也可能成立。[预印本及其假设](https://arxiv.org/abs/2610.15559v1) |
| 开放难题 · 二元圆法组 | 为每个充分大的偶数给出统一的正下界。固定圆法的和、权重、弧与归一化，以狄利克雷 GRH 下的等差数列估计处理主弧，单列次弧的逐点误差。采用 von Mangoldt 权重时还要扣除至少一个加数为真素数幂的贡献。 | 给出有效阈值 $N_0$，对每个偶数 $n\ge N_0$ 证明主项严格大于主弧误差、次弧误差和素数幂修正上界之和。再用经核验的证书覆盖 $4\le n<N_0$。目前缺少该逐点估计，也没有可供拼接的 $N_0$。[等差数列估计](https://arxiv.org/abs/2003.01925) · [二元圆法](https://arxiv.org/abs/2607.27282) |

**首轮交接。** 定义组先交“计数为正当且仅当存在素数对”的冻结草案。证书组同时交“两个相邻区间均已覆盖，则并集已覆盖”的草案，例如用半开区间 $[a,b)$ 与 $[b,c)$ 避免边界歧义。解析组先交短区间定理的假设和依赖清单，审计组独立核对“每个区间存在某个偶数”的量词。下一轮优先处理阻碍这三件交付的引理。

**例外集组可以先做的一条引理。** 取有限偶数集 $I$，令 $F$ 为其中无表示的数。若对每个 $n\in F$ 都能证明实误差满足 $|e(n)|\ge B>0$，则 $|F|B^2\le\sum_{n\in I}|e(n)|^2$。这把解析组的均方误差预算换成例外个数上界。只有整段误差预算严格小于 $B^2$ 时，这个判据才清空该段全部例外。

**有限组怎样支持短区间任务。** 对一个有限终点 $X\ge2$，以 2 为起点 $g_0$，选取一串递增的两奇素数之和 $g_1,\ldots,g_k$，直到 $g_k>X$。若每步满足 $g_{i+1}-g_i\le123(\log g_i)^2$，任取 $2\le x\le X$，取唯一满足 $g_i\le x<g_{i+1}$ 的下标。由对数的单调性，下一个见证就落在所需半开区间。这个方案可先在 $X=1000$ 试验并测量证书大小，再判断放大是否可行。它只证明短区间里有表示，完整的逐偶数证书另行统计。

可直接交给 Lean 参与者的样例是 $2,32,1002$。两个见证为 $32=3+29$ 与 $1002=5+997$。利用 $\log 2\ge2/3$ 和 $\log 32=5\log 2$，两步只须验证 $30\le123(2/3)^2$、$970\le123(10/3)^2$。其中 $\log 2\ge2/3$ 可由 $1/t$ 在 $[1,2]$ 上的中点切线积分得到。这是待形式化的样例。

**如何衡量进展。** 分别报告有限连续覆盖的终点、已在本项目重放的解析引理及尚存假设、能逐点控制的误差和适用范围。既有计算已经验算到 $4\times10^{18}$，这里的小区间用于建立可重放证书。陈氏定理的第二项允许是两个素数的乘积，三素数定理允许三个加数；只在其证明提供当前任务所需引理时安排复用。[既有计算](https://sweet.ua.pt/tos/bib/4.12.html) · [显式陈氏定理](https://arxiv.org/abs/2207.09452) · [Helfgott 三素数定理](https://arxiv.org/abs/1501.05438)

## English

Count ordered prime pairs by $R_2(n)=\#\{p\le n:p\text{ and }n-p\text{ are prime}\}$. The goal is $R_2(n)>0$ at **each** even $n\ge4$. Equivalently, the number $E(X)$ of failures up to $X$ must be zero for every $X$. The November 20 Alpöge–Claude release includes RH for ζ and GRH for Dirichlet L-functions for all moduli and characters. Independent kernel checks are public. Distribution in residue classes can help on the major arcs. An estimate for the overlap of the primes with their reflection about $n/2$ is still needed at each individual $n$. [Release](https://alpo.ge/remark.pdf) · [MIT checks](https://math.mit.edu/~drew/grh/) · [Waterloo checks](https://mrubinst.github.io/grh-lean-verification/)

| Assignment | Deliverable |
|---|---|
| P0 · Definitions | Freeze the equivalence of $R_2(n)>0$ with a pair of Mathlib primes summing to $n$. Audit natural subtraction, ordering, $2+2$ and the diagonal $5+5$. Use this definition in both branches. |
| P0 · Certificates | Prove witness-checker soundness and adjacent interval composition. Certify all 499 even inputs in $[4,1000]$ and test a missing witness and a composite summand. Publish the contiguous kernel-checked endpoint. Existing numerical verification reaches $4\times10^{18}$. [Earlier computation](https://sweet.ua.pt/tos/bib/4.12.html) |
| P1 · First analytic reproduction | Formalize the section 5 implication from the absence of a sum of two odd primes to a lower bound on a Selberg integral. Compare with its upper bound under RH to find a sum in $(x,x+123(\log x)^2]$. Prove the large-$x$ branch first. The paper starts it at $1.1\times10^{18}$ and uses published computation below that point. Independent finite coverage or a different argument is needed for the project to cover all real $x\ge2$. [Section 5](https://arxiv.org/html/2512.23534v1#S5) |
| P1 · Independent dependency audit | In parallel, pin the upstream archive and the five theorem types, identify the subset needed, compare Lean/Mathlib 4.33.1 with our pinned toolchain, and record axiom and replay evidence. Keep explicit hypotheses until the project can verify the imported proof. [Archive and resource measurements](https://math.mit.edu/~drew/grh/) |
| P2 · Exceptional sets | Audit the conditional argument of Pintz–Althöfer. At $\theta=1/2$ their formula gives the target $E(X)\ll_\varepsilon X^{1/2+\varepsilon}$ for each $\varepsilon>0$. Track the hypotheses and implicit constants. This bound allows infinitely many sparse exceptions. [Preprint](https://arxiv.org/abs/2610.15559v1) |
| Open · Pointwise binary estimate | For a specified weight and arc decomposition, bound the main term below and both arc errors above at each even $n\ge N_0$. Subtract proper prime powers if using von Mangoldt weights. Obtain an effective $N_0$ and certify the entire range below it. The pointwise saving and cutoff are open deliverables. [Progressions under GRH](https://arxiv.org/abs/2003.01925) · [Binary circle method](https://arxiv.org/abs/2607.27282) |

First handoff: the counting equivalence, the half-open interval composition lemma, and an independently read short-interval statement with its analytic dependencies. Only reviewed and frozen statements appear on the live desk. Track bounded coverage, reproduced analytic inputs and the uniform pointwise error separately.

An early exceptional-set lemma needs only finite sums. If each exception in $F\subseteq I$ incurs $|e(n)|\ge B>0$, then $|F|B^2\le\sum_{n\in I}|e(n)|^2$. A total strictly below $B^2$ rules out every exception in that block.

For finite short-interval coverage, use a sentinel $g_0=2$ and an increasing sequence of certified sums of two odd primes ending at $g_k>X$. If each gap is at most $123(\log g_i)^2$, every real $x\in[2,X]$ has the required next witness by monotonicity. Benchmark this sparse certificate at $X=1000$ before extrapolating. Record it separately from the certificate for all even integers.

The proposed pilot uses just $32=3+29$ and $1002=5+997$. The gap checks reduce to $30\le123(2/3)^2$ and $970\le123(10/3)^2$ using $\log 2\ge2/3$. Integrating the midpoint tangent to $1/t$ on $[1,2]$ gives the log bound. The pilot awaits Lean verification.

## 验证预算 / Verification budget

沿用 2,000 分钟的测算口径。若只计检查，按每次 75、250、848 秒分别可做 1,600、480、141 次。假设有 3 个实际并行槽位、300 份任务同时到达且每份耗时相同，相应清空时间为 2 小时 5 分、6 小时 56 分 40 秒、23 小时 33 分 20 秒。实际还须计入 runner 等待、环境安装、缓存和构建时间。For certificate shards, measure the complete workflow before increasing the target range.
