#!/usr/bin/env python3
"""Verify modpack dependency closure by parsing each jar's embedded metadata.

Usage:  python3 verify-deps.py [mods_dir]

For every *.jar in mods_dir (default: ./mods), extracts declared modIds + all
`type="required"` dependency modIds from META-INF/neoforge.mods.toml (or mods.toml,
or fabric.mod.json), then cross-checks required deps against the declared set.

Prints "UNRESOLVED" entries that need manual triage. Three classes of false positive
(do NOT add a jar for these):
  1. JiJ (jar-in-jar): the dep is bundled under META-INF/jarjar/ inside the requiring
     jar (e.g. endercore in enderio, apollib in tectonic, productivelib in productivebees).
  2. Game libraries declared via MANIFEST FMLModType (e.g. mezz_config) — no mods.toml.
  3. Merged/combined fabric+neoforge jars (Distant Horizons, PlayerAnimationLibMerged):
     their fabric.mod.json lists fabric-* deps the NeoForge side ignores.

Run after assembling/adding mods; add the real missing libs, then re-run until only the
false-positive classes remain.
"""
import os, re, sys, json, zipfile

def mods_toml_deps(data):
    own, req = set(), set()
    for b in re.split(r'(?=^\[\[)', data, flags=re.M):
        b = b.strip()
        if b.startswith('[[dependencies'):
            m = re.search(r'modId\s*=\s*"([^"]+)"', b)
            t = re.search(r'type\s*=\s*"([^"]+)"', b)
            if m and t and t.group(1).lower() == 'required':
                req.add(m.group(1).lower())
        elif b.startswith('[[mods'):
            m = re.search(r'modId\s*=\s*"([^"]+)"', b)
            if m:
                own.add(m.group(1).lower())
    if not own:
        m = re.search(r'modId\s*=\s*"([^"]+)"', data)
        if m:
            own.add(m.group(1).lower())
    return own, req

def fabric_deps(data):
    own, req = set(), set()
    try:
        j = json.loads(data)
        own.add(j.get('id', '').lower())
        for k in j.get('depends', {}):
            req.add(k.lower())
    except Exception:
        pass
    return own, req

def jarjar_has(jar_path, modid):
    try:
        with zipfile.ZipFile(jar_path) as z:
            return any('jarjar' in n and modid in n.lower() for n in z.namelist())
    except Exception:
        return False

LOADER = {'minecraft', 'neoforge', 'forge', 'java', 'fabricloader', 'fabric', 'quilt_loader', 'quilt'}

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else './mods'
    if not os.path.isdir(d):
        sys.exit(f"not a directory: {d}")
    jars = sorted(f for f in os.listdir(d) if f.endswith('.jar'))
    all_own, reqs = set(), {}
    for f in jars:
        own, rq = set(), set()
        p = os.path.join(d, f)
        try:
            with zipfile.ZipFile(p) as z:
                for cand in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
                    if cand in z.namelist():
                        o, r = mods_toml_deps(z.read(cand).decode('utf-8', 'replace'))
                        own |= o; rq |= r
                if 'fabric.mod.json' in z.namelist():
                    o, r = fabric_deps(z.read('fabric.mod.json').decode('utf-8', 'replace'))
                    own |= o; rq |= r
        except Exception:
            pass
        all_own |= own
        reqs[f] = rq - LOADER

    print(f"{len(jars)} jars | {len(all_own)} unique modIds\n")
    probs = [(f, dep) for f, r in sorted(reqs.items()) for dep in r if dep and dep not in all_own]
    if not probs:
        print("All required dependencies resolved.")
        return
    print("UNRESOLVED (check JiJ / game-lib / merged-jar before adding a jar):")
    for f, dep in probs:
        p = os.path.join(d, f)
        jj = "  [JiJ bundled]" if jarjar_has(p, dep) else ""
        print(f"  {dep:30s} <- {f}{jj}")

if __name__ == '__main__':
    main()
