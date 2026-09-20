# 小火箭规则配置地址与二维码

服务器更新本仓库脚本后，选择 **7.用户管理 → 6.生成小火箭规则地址与二维码**。
英文脚本提供相同入口。首次使用会按原订阅流程配置 nginx，并安装缺少的
Python 3 / qrencode 系统软件包；转换器仅使用 Python 标准库。

成功后显示：

- `.conf` 地址：`https://你的域名:订阅端口/s/clashMetaProfiles/shadowrocket.conf`
- 导入链接：`shadowrocket://config/add/` 后接上述地址。
- 终端二维码：用小火箭扫码导入配置；二维码在服务器本地生成。

也可以在小火箭的「配置 → 添加配置」中粘贴 `.conf` 地址。导入后选中使用该配置，
将全局路由设为「配置」。节点仍需通过原来的节点订阅单独导入。
规则配置不包含账号、密码或节点，不依赖订阅 Salt，因此所有用户共用相同规则地址。
配置沿用已安装订阅服务的 HTTP/HTTPS、域名/IP 和端口，复用原有 nginx 路由，
无需为已安装服务器改写 nginx 配置。

## 与 Clash Meta 的一致性

转换器读取正在运行的安装脚本中 `clashMetaConfig()` 模板，按原顺序读取已引用的
规则集，并下载同一 URL 的 Clash YAML 数据。转换为小火箭原生文本规则，保留
服务策略组、直连选择及最终兜底。包含 Apple Intelligence、Siri、OpenAI、Claude 等。
未被 Clash `rules` 引用的规则集不会擅自启用。

策略组使用小火箭已导入的节点；自动选择组通过节点名称匹配全部本地节点。
它不会同步 Clash 客户端当前的节点选择，也不搬运 Clash 的 DNS/TUN 设置。
本地直连和漏网之鱼等组仍保留模板的首选顺序，请按需要选择策略。

兼容差异：

- `MATCH` 转为 `FINAL`；IPv6 CIDR 转为小火箭的 `IP-CIDR`。
- Clash 的 `+.example.com` 转为包含根域名的 `DOMAIN-SUFFIX`。
- IP 规则的 `no-resolve` 保留；域名规则无需这个参数。
- iOS 不能等价执行桌面 `PROCESS-NAME` / `PROCESS-PATH`，配置中注明并省略它们。
- 不支持的新规则类型会使生成失败，不静默丢弃；原有 `.conf` 保持不变。
- 客户端自身的匹配实现与 GeoIP 数据库可能不同，不承诺所有流量行为完全相同。

## 更新

这是**生成时的完整规则快照**。每次运行菜单都会重新下载规则，并原子替换同一个
`.conf` 文件；任何规则下载或解析失败都会保留上一版。下载使用超时和有限并发，
GitHub 代理地址失败时尝试同一资源的原始地址。

刷新步骤：服务器再次运行此功能 → 小火箭更新该远程配置。
仅在小火箭中点更新不会触发服务器重新转换规则。本功能不安装后台定时任务；
Clash Meta 和 sing-box 原有的远程规则更新机制不受影响。

配置格式与导入 URI 参考：
https://github.com/LOWERTOP/Shadowrocket/blob/main/README.md
https://github.com/LOWERTOP/Shadowrocket/blob/main/lazy_group.conf

开发验证：`python3 -m unittest discover -s tests -p 'test_shadowrocket_rules.py'`。
仍需在真实小火箭客户端确认导入和实际流量命中。
