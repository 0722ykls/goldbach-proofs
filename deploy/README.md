# Deployment / 部署

Independent HTTPS service on port 8443 for www.movan.tech. The service reads the existing Let's Encrypt certificate through systemd credentials. Restart this service after its certificate renews. Install the APNIC CN IPv4 and IPv6 allocation rows in /opt/goldbach-web/china-apnic.txt and restart the service after refreshing them. The language selector uses the direct peer address. APNIC describes network allocations, so the country signal is approximate. Visitors can override it with ?lang=zh or ?lang=en.

权威工作流仅在生成 ACCEPTED 或 REJECTED 时回传。配置 GitHub Actions 仓库变量 GOLDBACH_WEBHOOK_URL 与密钥 GOLDBACH_WEBHOOK_SECRET 后，由单独的 runner 向 /api/verdict 发送 HTTPS POST。端点校验 X-Goldbach-Signature，格式为 sha256=<对原始请求体的 HMAC-SHA256>。

请求字段为 lemma_id、verdict、manifest、run_id、run_attempt。ACCEPTED 的 manifest 含 rests_on 与 defs，各为包含 module 和 sha256 的数组。REJECTED 使用 null。SQLite 按 run_id 和 run_attempt 去重。

服务端目录 /opt/goldbach-web，状态目录 /var/lib/goldbach-web。公开访问需要网关放行 TCP 8443。
