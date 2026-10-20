# Fast offline config checks (seconds, no game): merged mod configs + a patch stage.
# Usage: python tools/lint_configs.py <mod gamedata.db0 folder> <stage gamedata folder> [--base DIR]
# --base DIR = output of tools/extract_base_configs.py (the stock xrMPE/CoP configs, lowest layer; without it many names look missing).
# Checks:
#  1. weapons with scope/silencer/grenade_launcher status 2 (attachable) whose *_name is missing or names no section
#     (the engine then reads section '' and aborts: "Can't open section ''")
#  2. sections inheriting from a parent that does not exist
#  3. upgrade lists naming missing upgrade sections
import os, re, sys

pos = [a for a in sys.argv[1:] if not a.startswith('--')]
mod, stage = pos[0], pos[1]
base = sys.argv[sys.argv.index('--base') + 1] if '--base' in sys.argv else None
if base is not None:
    pos.remove(base)
    mod, stage = pos[0], pos[1]

def files():
    out = {}
    for layer in ([os.path.join(base, 'configs')] if base else []) + [os.path.join(mod, 'configs'), os.path.join(stage, 'configs')]:
        root = layer
        for dp, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith('.ltx'):
                    p = os.path.join(dp, f)
                    out[os.path.relpath(p, root).lower()] = p   # stage overrides mod
    return out

sections, parents, where = {}, {}, {}
head = re.compile(r'^\s*\[([^\]]+)\]\s*(?::\s*([^;]*))?')
for rel, p in files().items():
    cur = None
    for raw in open(p, 'rb').read().decode('cp1251', 'replace').splitlines():
        line = raw.split(';', 1)[0].strip()
        if not line or line.startswith('#'):
            continue
        m = head.match(line)
        if m:
            cur = m.group(1).strip().lower()
            sections[cur] = {}
            parents[cur] = [x.strip().lower() for x in (m.group(2) or '').split(',') if x.strip()]
            where[cur] = rel
            continue
        if cur is not None:
            k, _, v = line.partition('=')
            sections[cur][k.strip().lower()] = v.strip()

def get(sec, key, seen=None):
    seen = seen or set()
    if sec in seen or sec not in sections:
        return None
    seen.add(sec)
    if key in sections[sec]:
        return sections[sec][key]
    for par in reversed(parents.get(sec, [])):
        v = get(par, key, seen)
        if v is not None:
            return v
    return None

problems = 0
for sec, par in parents.items():
    for p in par:
        if p not in sections:
            print('MISSING PARENT  [%s]:%s  (%s)' % (sec, p, where[sec])); problems += 1
for sec in sections:
    cls = (get(sec, 'class') or '').lower()
    if not cls.startswith('wp_') and get(sec, 'scope_status') is None:
        continue
    for st, nm in (('scope_status', 'scope_name'), ('silencer_status', 'silencer_name'), ('grenade_launcher_status', 'grenade_launcher_name')):
        s = get(sec, st)
        if s is not None and s.split(',')[0].strip() in ('1', '2'):
            n = get(sec, nm)
            n = (n or '').split(',')[0].strip().lower()
            if nm == 'scope_name' and not n and (get(sec, 'scopes_sect') or '').strip():
                continue   # CoP 1.6 style: scopes come from the scopes_sect list
            if not n or n not in sections:
                print('ADDON NAME      [%s] %s=%s but %s=%r  (%s)' % (sec, st, s, nm, n, where[sec])); problems += 1
    ups = get(sec, 'upgrades')
    if ups:
        for u in [x.strip().lower() for x in ups.split(',') if x.strip()]:
            if u not in sections:
                print('MISSING UPGRADE [%s] upgrades -> %s  (%s)' % (sec, u, where[sec])); problems += 1
for sec in sections:
    ss = (get(sec, 'scopes_sect') or '').strip()
    if ss and get(sec, 'ammo_class') is not None:
        for n in [x.strip().lower() for x in ss.split(',') if x.strip()]:
            if n not in sections:
                print('SCOPES_SECT     [%s] lists missing section %s  (%s)' % (sec, n, where[sec])); problems += 1
print(problems, 'problems,', len(sections), 'sections checked')
