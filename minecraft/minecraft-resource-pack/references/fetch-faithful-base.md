# Fetching the official Faithful 32x base pack from Modrinth

The auto-upscaled pack is loaded **above** a hand-painted base. The official Faithful 32x is the standard base for 1.21.x. Download it programmatically from the Modrinth API rather than asking the user to fetch it manually.

## Project slugs (don't confuse them)

- `faithful-32x` — current official Faithful 32x (the one you usually want).
- `classic-faithful-32x` — older Jappa-era variant, lower download count.

## Modrinth API recipe

```bash
# List versions for a game version + loader
curl -s "https://api.modrinth.com/v2/project/faithful-32x/version?game_versions=%5B%221.21.1%22%5D&loaders=%5B%22minecraft%22%5D" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); [print(v['version_number'],'|',v['game_versions'],'|',v['files'][0]['url']) for v in d]"

# Download the newest (versions[0] is most recent)
URL=$(curl -s "https://api.modrinth.com/v2/project/faithful-32x/version?game_versions=%5B%221.21.1%22%5D&loaders=%5B%22minecraft%22%5D" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['files'][0]['url'])")
curl -sL -o "Faithful-32x-1.21.1.zip" "$URL"
```

Search endpoint for reference:
`https://api.modrinth.com/v2/search?query=faithful%2032x&facets=[["project_type:resourcepack"]]`

## Quirks

- The official Faithful pack's `pack.mcmeta` has a **malformed** `supported_formats` block (`min_inclusive: 34, max_inclusive: 33`). Minecraft accepts it anyway — do NOT "fix" it; ship as downloaded.
- Expected size for 1.21.1: ~11 MB, ~4,200 entries, `pack_format: 34`.

## Distributing the final bundle

The deliverable is two zips (base Faithful + generated mod pack) side by side in a release folder, load order documented in a README. Ruben pulls these via `git clone` from git.oathless.dev — create the repo with the `forgejo-repo-create.md` reference (see `go-vue-fullstack` skill). The generated mod-pack zip is often 100+ MB; git works but note LFS or Caddy hosting as the better long-term option for frequent rebuilds.
