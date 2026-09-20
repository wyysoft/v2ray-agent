# Apple Intelligence and Siri routing (Clash Meta)

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
Node-only subscriptions and sing-box configurations are outside this change.
These community lists provide routing coverage, not a guarantee of complete
coverage or Apple feature availability. Device/account/service eligibility and
actual connectivity must still be checked on the device.
