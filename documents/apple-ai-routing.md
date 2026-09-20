# Apple Intelligence and Siri routing

Both `install.sh` and `shell/install_en.sh` generate these rules for the full
`/s/clashMetaProfiles/<id>` subscription.

- **Apple Intelligence** uses MetaCubeX's apple-intelligence classical rules:
  https://github.com/MetaCubeX/meta-rules-dat/blob/meta/geo/geosite/classical/apple-intelligence.yaml
- **Siri** uses blackmatrix7's Siri rules:
  https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Clash/Siri/Siri.yaml
- Both HTTP rule providers refresh every 86400 seconds while the client is running
  and can reach the URLs. Downloads use the same gh-proxy.com prefix as existing providers.
- Both rules precede generic proxy and China direct rules. Apple Intelligence
  defaults to the existing manual-selection group; Siri defaults to the Apple
  Intelligence group. Each group also allows selecting a provider node.
- ChatGPT integration continues to use the existing OpenAI group. Select a
  suitable node in that group as well.

## Apply to an existing installation

1. Update the installer on your server from **wyysoft/v2ray-agent**, including
   the new template.
2. Run it and select account management, then view subscriptions.
3. Reuse the previous Salt to retain the subscription URL.
4. Refresh the full Clash Meta profile subscription in the client and check
   that both rule providers downloaded successfully.
5. Select the desired nodes and inspect client connection logs for rule matches.

Editing GitHub does not update an installed server or an existing client profile.
After initial deployment, upstream rule-list contents refresh automatically;
changes to groups or rule ordering require regenerating and refreshing the profile.
Node-only subscriptions do not carry routing rules.
These community lists provide routing coverage, not a guarantee of complete
coverage or Apple feature availability. Device/account/service eligibility and
actual connectivity must still be checked on the device.

## sing-box

The full `/s/sing-box/<id>` subscription now downloads this fork's
`documents/sing-box.json`. It has separate Apple Intelligence and Siri selectors,
with Siri following Apple Intelligence by default. Their route rules precede
the general Apple group and China direct rules. Their DNS matches use dns_proxy
before the China DNS rule; explicit global/direct mode still takes precedence.

Apple Intelligence uses MetaCubeX's remote source JSON:
https://github.com/MetaCubeX/meta-rules-dat/blob/sing/geo/geosite/apple-intelligence.json

Siri uses this fork's `documents/rules/siri.json`, a source-format equivalent
of blackmatrix7's Siri rule (guzzoni.apple.com), checked on 2026-09-20:
https://github.com/blackmatrix7/ios_rule_script/blob/master/rule/Clash/Siri/Siri.yaml
This file is maintained in this repository, not automatically synchronized from
blackmatrix7. Both remote sets are polled by the client every 1d; new Siri domains
must first be added to this repository's JSON file.

Regenerate subscriptions using the updated installer and previous Salt, then
refresh the full sing-box subscription. Existing configs retain their old rules
until refreshed. ChatGPT integration continues to use the OpenAI selector.

## Fork download URLs

Installer self-update, sing-box template downloads, bundled site assets, and
documented installation/helper commands now use wyysoft/v2ray-agent.
Upstream author/project references, feedback links, third-party rule sources,
and existing firewall identifiers remain unchanged.
Install the fork's script explicitly once: an already installed upstream script
still updates from upstream until replaced.

## Supplemental rules requested from the reference screenshot

These repository-maintained additions reproduce the user's requested routing:
- Exact `seed.siri.apple.com` and suffix `smoot.apple.com` (including its subdomains) use Siri.
- Exact `cp4.cloudflare.com` and `mask-api.icloud.com` use Apple Intelligence.

Clash Meta references `siri-extra.yaml` and `apple-intelligence-extra.yaml` before
general routing. Shadowrocket converts those same sources with the existing
converter; regenerate its config on the server and refresh it in the app.
sing-box includes the Siri additions in `siri.json` and loads
`apple-intelligence-extra.json` alongside the upstream Apple Intelligence set;
both DNS and route rules reference the supplemental set.

Regenerate full Clash/sing-box subscriptions with the updated installer, then
refresh clients to install the new rule-set references. Remote lists update
daily where configured. These additions are explicit user-requested routing
overrides, not a claim that every listed host serves only Apple AI.

## Apple Relay troubleshooting group

A separate **Apple Relay** selector now handles these exact hosts:
- `mask-api.icloud.com`
- `mask.icloud.com`
- `mask-h2.icloud.com`
- `mask-api.fe.apple-dns.net`
- `mask-t.apple-dns.net`
- `mask.apple-dns.net`

The three icloud.com hosts are listed as Private Relay endpoints by Apple:
https://support.apple.com/en-us/101555
The three apple-dns.net hosts are user-requested diagnostic additions from the
reference screenshot; they are not asserted to be required for Siri.

Apple Relay defaults to Apple Intelligence and also permits manual node selection
or DIRECT for comparison. This supersedes the earlier assignment of
mask-api.icloud.com to Apple Intelligence: it now belongs to Apple Relay only.
Apple Intelligence's PCC/extension hosts remain in their existing group.
Broad ls.apple.com, apps.mzstatic.com, gateway.icloud.com and keyword siri rules
are not included in this group.

Both Clash installers and sing-box have the selector and prioritized rule-set;
sing-box DNS references it as well. Shadowrocket derives the same selector/rules
from the Clash template without changing the pinned converter.

Deploy the updated installer, regenerate full subscriptions (reuse Salt), and
refresh clients. For Shadowrocket use account management option 6, then update
the remote config and verify rule-set downloads. Merely updating an old rule list
does not create the new selector or rule-set reference.

For troubleshooting, select the same intended node for Apple Intelligence, Siri,
Apple Relay and OpenAI, reproduce the failing request, then check connection
logs for host, matched rule, actual outbound and errors. Compare Apple Relay's
proxy versus DIRECT setting separately. This change supplies routing controls;
it does not establish that routing caused the Siri failure.
