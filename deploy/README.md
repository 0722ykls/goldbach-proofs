# Deployment / 部署

The public site is https://www.movan.tech/goldbach/. Nginx strips the /goldbach/ prefix and forwards to the HTTPS service on 127.0.0.1:8443. The upstream service reads its certificate through systemd credentials. Restart the service after its certificate renews. Install the APNIC CN IPv4 and IPv6 allocation rows in /opt/goldbach-web/china-apnic.txt and restart the service after refreshing them. Nginx sets the visitor address used for language selection. Visitors can override it with ?lang=zh or ?lang=en.

权威工作流仅在生成 ACCEPTED 或 REJECTED 时回传。配置 GitHub Actions 仓库变量 GOLDBACH_WEBHOOK_URL 与密钥 GOLDBACH_WEBHOOK_SECRET 后，由单独的 runner 向 https://www.movan.tech/goldbach/api/verdict 发送 HTTPS POST。端点校验 X-Goldbach-Signature，格式为 sha256=<对原始请求体的 HMAC-SHA256>。

请求字段为 lemma_id、verdict、manifest、run_id、run_attempt。ACCEPTED 的 manifest 含 rests_on 与 defs，各为包含 module 和 sha256 的数组。REJECTED 使用 null。SQLite 按 run_id 和 run_attempt 去重。

服务端目录 /opt/goldbach-web，状态目录 /var/lib/goldbach-web。公网入口使用 nginx 的 HTTPS 443 端口。

发布站点时，将 deploy/ 下的 server.py、desk.py、zh.html、en.html、site.css、site.js、join.txt、join-zh.txt，以及 research/gaps.json 部署到 /opt/goldbach-web，再重启 goldbach-web。GET /goldbach/api/status 从命题清单和 SQLite 返回公开引理、最近的验证结果及累计统计。

`/goldbach/join.txt` 和 `/goldbach/join-zh.txt` 对应一键参与提示词。任务台在 `/goldbach/api/desk/` 接受领取、续约、归还和登记提交。租约通过 Authorization 请求头传递。
PR 作者在登记提交后使用 `/goldbach-check <gap>` 触发权威验证。GitHub Actions 使用仓库变量 `GOLDBACH_DESK_URL` 指向任务台根 URL，并用 `GOLDBACH_WEBHOOK_SECRET` 签署授权请求。
授权绑定 PR、提交 SHA、作者和固定命题哈希。结果写入同一 SQLite 数据库，并更新参与动态和贡献榜。

评论事件未直接启动核验时，desk-queue 工作流定期检查已登记提交，并用当前 PR 作者、head 与请求评论做预检，再派发同一个权威工作流。管理员可手动运行 desk-queue 补跑队列。
