---
name: smite2-rallyhere-api
description: Work with SMITE 2 player/match/item data via the RallyHere API (NOT the old Hi-Rez SMITE 1 API). Covers the Hi-Rez/Titan Forge/RallyHere org chart, the official SDK + endpoints + data model, how third-party trackers obtained access, partnership contact channels, and the smite2-tracker project's live-bridge/mock architecture.
triggers:
  - Working on SMITE 2 stats, data, or tracker tooling
  - Requesting or configuring RallyHere / Hi-Rez API access
  - Extending or deploying the smite2-tracker project
  - Drafting a SMITE 2 partnership or Creator Program application
---

# SMITE 2 Data via RallyHere

## The one gotcha that matters
SMITE 2 does **NOT** use the classic Hi-Rez SMITE 1 API (`getmatchhistory`, `getitems`,
`getgods`, `getmatchdetails` with `devId`/`authKey` + MD5 signature). That API is SMITE 1 /
Paladins / Realm Royale only. SMITE 2 data lives in **RallyHere**, Hi-Rez's
backend-as-a-service platform.

## Org chart (who owns what)
- **Hi-Rez Studios** — publisher, owns the SMITE 2 IP and data.
- **Titan Forge Games** — Hi-Rez subsidiary that develops SMITE 2 (the IP gatekeeper).
- **RallyHere** — a division of Hi-Rez Ventures; provides the backend and issues API credentials.

Third-party trackers (tracker.gg, smitesource.com, smitetracker.com) are **partnered** with
Hi-Rez + Titan Forge + RallyHere — that's how they get data. There is no self-serve public
fan API.

## Official SDK & endpoints
SDK: `hirezstudios/s2rh_pythonsdk` (Python). Auth is OAuth2 client-credentials, then:
- `POST /users/v2/oauth/token` — `grant_type=client_credentials` → access token
- `GET /users/v1/platform-user?platform=&platform_user_id=` — resolve player → `player_uuid`
- `GET /match/v1/player/{uuid}/match?page_size=&cursor=` — match history (paginated)
- `GET /match/v1/player/{uuid}/stats` — aggregate stats
- `GET /match/v1/match?instance_id=` — match detail
- Files API (combat/chat logs, match summaries) also exists in the SDK.

## Data model (SDK's transformed output)
The SDK transforms native RallyHere records into a SMITE 2-friendly shape:
- `god_name` — parsed from `custom_data.CharacterChoice` (`"Gods.Anubis"` → `Anubis`)
- `basic_stats` — `Kills/Deaths/Assists/TowerKills/…/TotalDamage/TotalGoldEarned/PlayerLevel`,
  stored as **strings** in `custom_data` (SDK does `int(x) if x.isdigit()`)
- `assigned_role` / `played_role`, `items` (a **stringified JSON** blob the SDK `json.loads()`-es),
  `map`/`mode`/`winning_team` from `match.custom_data` (`CurrentMap`/`CurrentMode`/`LobbyType`/`WinningTeam`)
- `damage_breakdown` — built from `custom_data` keys prefixed `Gods.`/`Items.`/`NPC.`

⚠️ When mocking RallyHere data, keep numbers-as-strings and stringified `Items` faithful —
that's how the real API returns, and showing it in a PoC signals you understand the contract
(reviewers may flag it as a "bug" otherwise).

## Getting access (for a stats site)
No public fan API. Path for a third-party site = a partnership with Hi-Rez/Titan Forge +
technical credentials from RallyHere (the tracker.gg model — cite this in applications).
Contact channels:
- RallyHere: `contact@rallyhere.gg`, portal `developer.rallyhere.gg`, docs `docs.rallyhere.gg`
- Hi-Rez: press `hirezstudios.com/press`, support `support.hirezstudios.com`, partner/affiliate `affiliate.hirezstudios.com`
- SMITE 2 Creator Program (streamer entry point): `smite2.com/creator-kit/`
- Titan Forge has no public direct email — route via Hi-Rez.

## Project: smite2-tracker
`/home/ruben/smite2-tracker` — Go backend + Vue 3 + Tailwind (Rose Pine), single Docker
container, private repo `git.oathless.dev/oathless/smite2-tracker`.
- **Live bridge:** `internal/rallyhere/client.go` is env-gated (`RH_BASE_URL`/`RH_CLIENT_ID`/
  `RH_CLIENT_SECRET`). Set → live mode (`/api/meta` reports `mode`); unset → bundled mock data
  mirroring the SDK shape.
- `README.md` has the architecture + endpoint table; `APPLICATION.md` has partnership email drafts.
- Full live transform (raw RallyHere → app model) is the remaining step once credentials land.
