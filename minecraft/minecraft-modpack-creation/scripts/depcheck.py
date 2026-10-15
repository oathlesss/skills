#!/usr/bin/env python3
"""Dependency-closure checker for a NeoForge/Fabric mods folder.

Parses each jar's embedded metadata (neoforge.mods.toml / mods.toml / fabric.mod.json),
collects declared modIds and every `type="required"` dependency, then cross-checks that
required deps are satisfiable by the installed set.

For each unresolved dep it also checks whether the requiring jar bundles it via
Jar-in-Jar (META-INF/jarjar/), so JiJ deps are auto-confirmed rather than flagged.

Usage: python3 depcheck.py [mods_dir]     # default: ./mods
"""
import json, os, re, sys, zipfile

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

LOADER = {'minecraft', 'neoforge', 'forge', 'java', 'fabricloader', 'fabric', 'quilt_loader', 'quilt'}

def is_bundled(mods_dir, jar, dep):
    """True if `jar` bundles `dep` via META-INF/jarjar/."""
    try:
        with zipfile.ZipFile(os.path.join(mods_dir, jar)) as z:
            return any('jarjar' in n and dep in n.lower() for n in z.namelist())
    except Exception:
        return False

def main():
    d = sys.argv[1] if len(sys.argv) > 1 else 'mods'
    jars = sorted(f for f in os.listdir(d) if f.endswith('.jar'))
    all_own, reqs, empty = set(), {}, []
    for f in jars:
        own, rq = set(), set()
        try:
            with zipfile.ZipFile(os.path.join(d, f)) as z:
                for cand in ('META-INF/neoforge.mods.toml', 'META-INF/mods.toml'):
                    if cand in z.namelist():
                        o, r = mods_toml_deps(z.read(cand).decode('utf-8', 'replace'))
                        own |= o; rq |= r
                if 'fabric.mod.json' in z.namelist():
                    o, r = fabric_deps(z.read('fabric.mod.json').decode('utf-8', 'replace'))
                    own |= o; rq |= r
        except Exception as e:
            print(f'  !! parse error {f}: {e}')
        if not own:
            empty.append(f)
        all_own |= own
        reqs[f] = rq - LOADER

    print(f'{len(jars)} jars, {len(all_own)} declared modIds')
    unresolved, jij = [], []
    for f, r in sorted(reqs.items()):
        for dep in sorted(r):
            if dep and dep not in all_own:
                (jij if is_bundled(d, f, dep) else unresolved).append((f, dep))
    if jij:
        print('JiJ-bundled (auto-resolved, no action):')
        for f, dep in jij:
            print(f'  {dep:28s} <- {f}')
    if unresolved:
        print('UNRESOLVED (add the jar, or confirm GAMELIBRARY / combined-jar fabric-* false positive):')
        for f, dep in unresolved:
            print(f'  {dep:28s} <- {f}')
    if not unresolved and not jij:
        print('all required deps resolved')
    if empty:
        print(f'\nJars with no detectable modId ({len(empty)}) — usually GAMELIBRARY (MANIFEST FMLModType):')
        for f in empty:
            print(f'  {f}')

if __name__ == '__main__':
    main()
