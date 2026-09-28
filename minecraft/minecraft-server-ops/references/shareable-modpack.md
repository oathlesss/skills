# Building a shareable PrismLauncher modpack from the itzg server

Goal: hand friends ONE importable file that gives them the server's exact mod set so they can
join without version-mismatch errors. PrismLauncher imports both CurseForge-format `.zip`
(`manifest.json` + `modlist.html` + `overrides/`) and Modrinth `.mrpack`.

## Mental model (avoid over-building)

ATM packs are already public on CurseForge. "Our own" pack = the **pinned official version** +
the few **client-required manual mods**. Two valid deliverables:

1. **Full zip** — official pack manifest + overrides + your extra jars bundled in
   `overrides/mods/`. One file, but ~100 MB (overrides are large; kubejs alone was 103 MB here).
2. **Lazy path (usually better)** — friends install the official pack from CurseForge inside
   PrismLauncher at the SAME version, then drop your tiny extra jars in. The extra jars are
   ~360 KB and fit through Discord directly; CF's CDN serves the 400+ mods faster than anything
   you'd self-host.

## Version-pinning gotcha (critical)

The server stays on the version it was installed at; CF's "latest" moves on. Server ran **0.5.1**
while CF listed **0.6.1**. If a friend installs the wrong version they get a mod-mismatch on join.
Always read the exact version from `.curseforge-manifest.json` / `.install-curseforge.env` and
pin the friends to it.

## Full-zip build recipe

```bash
# 1. Get pack identity + download URL (query CF API through the container's mounted key).
#    modId/fileId come from data/.curseforge-manifest.json
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/mods/<modId>/files/<fileId>"'
#    -> data.downloadUrl (edge.forgecdn.net), data.fileLength (~100 MB; mods are NOT bundled)

# 2. Download + extract manifest.json + modlist.html + overrides/ (python zipfile; unzip may be absent)
python3 - <<'PY'
import zipfile
z = zipfile.ZipFile('official.zip')
for n in z.namelist():
    if n in ('manifest.json','modlist.html') or n.startswith('overrides/'):
        z.extract(n, 'build/')
PY

# 3. Bundle extra client-required jars into overrides/mods/ (no CF project/file ID lookup needed —
#    the launcher copies overrides/ over the instance AFTER downloading manifest files)
cp AppliedFlux-*.jar advancedae_addon-*.jar build/overrides/mods/

# 4. Re-zip -> CurseForge-format pack PrismLauncher can import
python3 - <<'PY'
import zipfile, os
with zipfile.ZipFile('ATM10-Aeronautics-Oathless-0.5.1.zip','w',zipfile.ZIP_DEFLATED) as z:
    for r,_,fs in os.walk('build'):
        for f in fs:
            p=os.path.join(r,f); z.write(p, os.path.relpath(p,'build'))
PY
```

The CF-format zip has `manifest.json` (minecraft + modLoaders + `files[]` of projectID/fileID),
`modlist.html` (cosmetic only), and `overrides/` (config + kubejs + defaultconfigs + …). Mods are
NOT bundled in the manifest-referenced zip — the launcher downloads them at install time, which
keeps the zip redistribution-compliant.

## Client-required vs server-side extras

Only bundle what clients NEED to join: content mods that add blocks/items (AppliedFlux,
advancedae_addon). Server-side perf/pregen mods (Chunky, C2ME, Distant Horizons server jar) don't
gate joining and shouldn't be forced on clients (DH is optional both sides).

## Distribution

The full zip (~100 MB) exceeds Discord's 25 MB attachment cap. Options: Forgejo release on
git.oathless.dev, Caddy static file on the homelab, or the user uploads to Drive/Dropbox. The
tiny extras zip ships through Discord directly — so prefer the lazy path when possible.

## docker exec CF API quoting pitfall

The working form is SINGLE-quoted `sh -c '...'`:
```bash
docker exec minecraft-atm10aero sh -c 'curl -s -H "x-api-key: $(cat /run/secrets/cf_api_key)" "https://api.curseforge.com/v1/..."'
```
Do NOT nest it inside a host `for` loop with double-quoted `sh -c "..."` and `\$(cat …)` — the
`\$` escape gets eaten and the inner `$(cat …)` runs on the HOST (empty value), so curl returns
non-JSON and `json.load` throws. If you must loop, run the loop INSIDE the container's `sh -c`,
or issue one `docker exec` per call.
