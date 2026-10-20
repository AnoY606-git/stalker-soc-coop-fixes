# Finds Lua string literals with a single backslash before a letter that is not a Lua escape (e.g. "misc\coop.ltx",
# which Lua reads as "miscoop.ltx"). Paths in Lua strings need "\\".
import os, re, sys
root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'patches')
valid = set('abfnrtv\\"\'\n0123456789')
strlit = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'(?:[^\'\\\n]|\\.)*\'')
n = 0
for dp, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith(('.script', '.dscript', '.lua')):
            continue
        p = os.path.join(dp, f)
        for i, line in enumerate(open(p, encoding='cp1251', errors='replace'), 1):
            code = line.split('--', 1)[0] if '--' in line and '"' not in line.split('--', 1)[0][-1:] else line
            for m in strlit.finditer(code):
                s = m.group(0)[1:-1]
                for j, ch in enumerate(s):
                    if ch == '\\':
                        # skip escaped backslash pairs
                        k = j
                        while k > 0 and s[k - 1] == '\\':
                            k -= 1
                        if (j - k) % 2 == 1:
                            continue
                        nxt = s[j + 1] if j + 1 < len(s) else ''
                        if nxt and nxt not in valid:
                            print('%s:%d: %s' % (os.path.relpath(p, root), i, line.strip()[:140]))
                            n += 1
                            break
print(n, 'suspicious literals')
