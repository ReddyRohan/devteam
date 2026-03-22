# NanoClaw / Pi-hole Setup Customizations

## Raspberry Pi Details
- Hostname: `rohan-pi-hole`
- Local IP: `192.168.1.50` (reserve in router DHCP)
- Tailscale IP: `100.112.209.68`
- SSH: `ssh rohan@192.168.1.50` (key: `C:\Users\rohan\.ssh\id_ed25519`)
- OS user: `rohan`, SSH key auth (no password)

---

## `/home/rohan/nanoclaw/.env`
Full contents:
```
ANTHROPIC_API_KEY=dummy-key
ANTHROPIC_BASE_URL=http://localhost:4000
ASSISTANT_NAME=nanoclaw
TELEGRAM_BOT_TOKEN=8772822984:AAGWCjezNGfXMpv0x7qU4xyl-_dJM7JN9xc
DISCORD_BOT_TOKEN=<REDACTED_DISCORD_TOKEN>
```
- Must always be synced: `cp ~/.env ~/nanoclaw/data/env/env`

---

## `/home/rohan/nanoclaw/data/env/env`
- Mirror of `.env` above (used by Docker containers)

---

## `/opt/litellm/config.yaml`
Routes all Claude model names → Azure GPT-4.1 deployment:
```yaml
litellm_settings:
  drop_params: true

model_list:
  - model_name: claude-3-5-sonnet-20241022
    litellm_params:
      model: azure/gpt-41
      api_base: https://ai-rohanreddy6652ai346568304857.cognitiveservices.azure.com/
      api_key: <AZURE_API_KEY>
      api_version: "2025-01-01-preview"
  - model_name: claude-sonnet-4-6
    litellm_params:
      model: azure/gpt-41
      ...
  - model_name: claude-3-7-sonnet-20250219
    litellm_params:
      model: azure/gpt-41
      ...
```

---

## `/etc/systemd/system/litellm.service`
```ini
[Unit]
Description=LiteLLM Proxy
After=network.target

[Service]
ExecStart=/opt/litellm/bin/litellm --config /opt/litellm/config.yaml --port 4000 --drop_params
Restart=always
User=rohan
Environment=HOME=/home/rohan
Environment=LITELLM_DROP_PARAMS=true

[Install]
WantedBy=multi-user.target
```

---

## `/etc/systemd/system/nanoclaw.service`
```ini
[Unit]
Description=NanoClaw AI Agent
After=network.target litellm.service

[Service]
WorkingDirectory=/home/rohan/nanoclaw
ExecStart=/usr/bin/node dist/index.js
Restart=always
RestartSec=5
User=rohan
Environment=HOME=/home/rohan

[Install]
WantedBy=multi-user.target
```

---

## `/etc/unbound/unbound.conf.d/pi-hole.conf`
- Unbound listening on `127.0.0.1:5335`
- Pi-hole upstream set to `127.0.0.1#5335`

---

## `/opt/litellm/lib/python3.13/site-packages/litellm/llms/anthropic/experimental_pass_through/adapters/handler.py`
**Patched** — added `"output_config"` to `excluded_keys` set to prevent it being forwarded to Azure:
```python
# Before:
excluded_keys = {"anthropic_messages"}
# After:
excluded_keys = {"anthropic_messages", "output_config"}  # output_config is Anthropic-specific
```

---

## `/home/rohan/nanoclaw/src/channels/discord.ts`
- Copied from `.claude/skills/add-discord/add/src/channels/discord.ts`
- **Appended** at bottom: `registerChannel('discord', ...)` factory function

---

## `/home/rohan/nanoclaw/src/channels/index.ts`
- **Appended**: `import './discord.js';` to auto-register Discord channel on startup

---

## `/home/rohan/nanoclaw/src/config.ts`
- **Appended** at bottom: `DISCORD_BOT_TOKEN` export reading from `.env`

---

## NanoClaw Registered Channels (store/messages.db)
| JID | Name | Folder | Trigger | Requires Trigger |
|-----|------|--------|---------|-----------------|
| `tg:1419669711` | Rohan | `telegram_main` | `@nanoclaw` | No |
| `dc:1484646170931233021` | Discord main | `discord_main` | `@nanoclaw` | No |

---

## Azure Resources
- Subscription: `cb15c9de-a57f-4a7a-8b1c-4a070c319ad6` (Visual Studio Professional)
- Resource Group: `DefaultResourceGroup-NEU`
- Cognitive Services account: `ai-rohanreddy6652ai346568304857`
- Deployments:
  - `gpt-4o` (2024-11-20)
  - `gpt-4o-2` (2024-08-06)
  - `gpt-41` (2025-04-14) ← **active, used by LiteLLM**

---

## Pi-hole
- Web UI: `http://192.168.1.50/admin` or `http://100.112.209.68/admin`
- Listening mode: `ALL` (listens on all interfaces including Tailscale)
- Blocking: **enabled**
- Blocklists added:
  - StevenBlack: `https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts`
  - OISD Basic: `https://small.oisd.nl/`
  - Hagezi Pro: `https://raw.githubusercontent.com/hagezi/dns-blocklists/main/adblock/pro.txt`
- Total blocked domains: ~267,500

---

## Tailscale DNS
- Custom nameserver: `100.112.209.68` with **Override local DNS** enabled
- MagicDNS: **disabled**
- Phone DNS routes through Pi-hole when Tailscale is active

---

## Bots
- Telegram: `@mera_chot_bot` (token starts with `8772822984:`)
- Discord: `Chotu#8357` (bot ID: `1484643047923777758`)

---

## Services Status (all auto-start on reboot)
| Service | Command |
|---------|---------|
| Pi-hole | `sudo systemctl status pihole-FTL` |
| Unbound | `sudo systemctl status unbound` |
| Tailscale | `sudo systemctl status tailscaled` |
| LiteLLM | `sudo systemctl status litellm` |
| NanoClaw | `sudo systemctl status nanoclaw` |
