# Deployment / 部署

## 知乎署名

随 `server.py` 部署 `zhihu_oauth.py` 与 `github_identity.py`。将应用凭据 JSON（字段 `app_id`、`app_key`）保存到仅 root 可读的 `/etc/goldbach-web/zhihu-oauth`，安装 `zhihu-oauth.conf` 到 `/etc/systemd/system/goldbach-web.service.d/`，再执行 daemon-reload 并重启 goldbach-web。凭据保留在服务器。已登记回调为 `https://www.goldbach.tech/auth/zhihu/callback`，应从这个域名启动会话，并在该虚拟主机的访问日志中排除授权路径。

来自 movan.tech 的参与者可从贡献榜进入管理页面。知乎回调必须匹配当前浏览器中未过期的一次性 state。服务端用授权码换取短期令牌并读取基础资料，仅使用稳定用户标识及展示字段，随后丢弃令牌。参与者再用指定 GitHub 账号创建含挑战文本的 Gist，勾选公开署名。绑定后可重新登录知乎并解除绑定。站点在单独的 contributor-links.sqlite3 中保存绑定及限时会话。跨项目沿用 GitHub 贡献记录。

运行 `python -B -m unittest deploy.test_zhihu deploy.test_github_identity` 检查绑定流程。实测授权需使用可公开访问的登记域名与参与者自己的知乎账号。若平台回调缺少 state，页面终止绑定，需向平台确认 state 回传或受支持的替代机制。

The public site is https://www.movan.tech/goldbach/. Nginx strips the /goldbach/ prefix and forwards to the HTTPS service on 127.0.0.1:8443. The upstream service reads its certificate through systemd credentials. Restart the service after its certificate renews. Install the APNIC CN IPv4 and IPv6 allocation rows in /opt/goldbach-web/china-apnic.txt and restart the service after refreshing them. Nginx sets the visitor address used for language selection. Visitors can override it with ?lang=zh or ?lang=en.

权威工作流仅在生成 ACCEPTED 或 REJECTED 时回传。配置 GitHub Actions 仓库变量 GOLDBACH_WEBHOOK_URL 与密钥 GOLDBACH_WEBHOOK_SECRET 后，由单独的 runner 向 https://www.movan.tech/goldbach/api/verdict 发送 HTTPS POST。端点校验 X-Goldbach-Signature，格式为 sha256=<对原始请求体的 HMAC-SHA256>。

请求字段为 lemma_id、verdict、manifest、run_id、run_attempt。ACCEPTED 的 manifest 含 rests_on 与 defs，各为包含 module 和 sha256 的数组。REJECTED 使用 null。SQLite 按 run_id 和 run_attempt 去重。

服务端目录 /opt/goldbach-web，状态目录 /var/lib/goldbach-web。公网入口使用 nginx 的 HTTPS 443 端口。

发布站点时，将 deploy/ 下的 server.py、desk.py、landau.py、zh.html、en.html、site.css、site.js、goldbach-icon.svg、join.txt、join-zh.txt，以及 research/gaps.json 部署到 /opt/goldbach-web，再重启 goldbach-web。GET /goldbach/api/status 从命题清单和 SQLite 返回公开引理、最近的验证结果及累计统计。

讨论群浮窗的 `deploy/discussion.js`、`deploy/discussion-qr.png` 和 `deploy/wechat.svg` 也放在 `/opt/goldbach-web/`。换群码时同步更新 `server.py` 的 `DISCUSSION_EXPIRES`，按微信标注的北京时间有效期填写；到期后页面自动隐藏入口。

二次型素数研究台的 `/goldbach/problems/quadratic-primes/api/status` 返回 `lpf_record`。其中 `baseline` 链接外部 1.323 论文及其有限证书，`verified` 是本站权威核验通过的最高指数，暂缺时为 null。登记新的挑战值时，请在 `research/problems.json` 使用新的任务 ID、十进制字符串 `lpf_exponent` 和 `deploy/landau.py` 的 `record_statement` 生成的固定命题。参与者可领取该任务并提交 Lean 证明。通过核验的运行与任务租约及命题哈希匹配后，访客即可在记录上打开对应的 Actions 运行。

多问题目录位于 `/goldbach/problems/`。将 `research/problems.json` 同样部署到 `/opt/goldbach-web`。新问题以 `/goldbach/problems/<slug>/` 为入口，拥有独立的状态接口、加入说明和 SQLite 数据库。哥德巴赫沿用 `gaps.json` 与 `verdicts.sqlite3`。新问题可用 `python tools/goldbach.py claim --problem <slug>` 领取；提交、续租和归还从租约读取问题编号。签名队列为每个问题保留一部分批次位置，空余位置继续处理等待中的任务。签名判定按任务归属路由，新增问题的判定须关联已授权的运行。

目录卡片显示每个问题在权威 Lean 核验下的进度和当前可领取的引理数。复制单条引理的提示词时，命令同时包含问题标识和引理编号。每个子题标记了一条可由多组独立试证的任务，其他任务保持独占领取。

运行 `python -B -m unittest deploy.test_desk_scale -v` 可同时验证并发领取、跨题使用租约被拒绝、重复签名判定不重复计榜，以及现有哥德巴赫流程。

团队凭证由站点管理员使用同目录下的 `issue_fleet_pass.py HANDLE /private/path/pass` 签发，有效七天。控制器以绑定账号运行 gh，将 `GOLDBACH_FLEET_FILE` 指向项目目录外的凭证，每个助手使用独立 checkout。普通账号同时持有一条任务，每个普通来源网络同时最多三条；团队凭证可在同一网络、同一账号下持有 128 条。提交排队时间为 12 小时。签名队列每轮取至多 16 个提交，优先处理从未轮询的记录。可在独立临时数据库中运行 `python -B -m unittest deploy.test_desk_scale -v` 复测。

`/goldbach/join.txt` 和 `/goldbach/join-zh.txt` 对应一键参与提示词。任务台在 `/goldbach/api/desk/` 接受领取、续约、归还和登记提交。租约通过 Authorization 请求头传递。

知乎访客可从 `https://www.goldbach.tech/?lang=zh&from=zhihu#participation` 打开参与引导。现有入口 `https://www.movan.tech/goldbach/?lang=zh&from=zhihu#participation` 使用同一套页面。访客可以直接选题、阅读引理和复制提示词。准备提交证明时，参与者在运行 Agent 的环境用 `gh auth login --hostname github.com --web` 打开 GitHub 授权，验证流程沿用 GitHub PR。

自动领取优先覆盖无人领取的题目，再按每题和每条路线的活跃人数均衡分配。标记 parallel 的难题支持多份独立租约；其他引理独占。某题首次通过后，释放尚未开始核验的同题租约，已在核验的提交仍可接收判定。指定编号领取时只考虑该编号。
PR 作者在登记提交后使用 `/goldbach-check <gap>` 触发权威验证。GitHub Actions 使用仓库变量 `GOLDBACH_DESK_URL` 指向任务台根 URL，并用 `GOLDBACH_WEBHOOK_SECRET` 签署授权请求。
授权绑定 PR、提交 SHA、作者和固定命题哈希。结果写入同一 SQLite 数据库，并更新参与动态和贡献榜。

评论事件未直接启动核验时，desk-queue 工作流定期检查已登记提交，并用当前 PR 作者、head 与请求评论做预检，再派发同一个权威工作流。管理员可手动运行 desk-queue 补跑队列。

## 一次完整的线上核验

2026-11-24，PR #4 通过正卷积提取素数对的引理，适用于任意自然数和任意支撑在素数上的实权。研究台收到权威 ACCEPTED 及含有 rests_on、defs 的 SHA-256 清单。核验后，贡献榜的一小时新增为 1。这个公开榜只统计能绑定到参与者、且有首次通过记录的引理。[PR #4](https://github.com/CGandGameEngineLearner/goldbach-proofs/pull/4) · [权威运行](https://github.com/CGandGameEngineLearner/goldbach-proofs/actions/runs/45312512546) · [回传后的公开记录](https://www.movan.tech/goldbach/api/status)

| 观测项 | 实测值 | 口径 |
| --- | ---: | --- |
| Mathlib 缓存 | 60.555 秒 | 日志中 lake exe cache get 的 real 时间，含获取和解包 |
| 单次 check-lean | 约 63 秒 | 权威运行的 checker 步骤，包含隔离启动与收尾 |
| 完整 workflow | 5 分 32 秒 | 从创建运行到回传任务结束后的最终更新时间 |
| 两个 runner 的执行时间 | 319 秒 + 5 秒 | check 和 report 各自的作业起止时间 |

公开仓库使用标准 GitHub 托管 runner 的执行时间免费。若另按每月 2,000 分钟模拟受限预算，并对每个 job 单独向上取整，这次样本折合 6 + 1 = 7 分钟，即约 285 次。三个独立端到端槽且每份均耗时 5 分 32 秒时，300 份同时到达需 100 批，最后一批约 9 小时 7 分 48 秒后开工，9 小时 13 分 20 秒后全部完成。这个情形假设每个槽从头至尾被一份提交占用，实际 GitHub 等待和队列回补会改变结果。研究租约的并行度与 runner 槽位分别统计。[GitHub Actions 计费](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
