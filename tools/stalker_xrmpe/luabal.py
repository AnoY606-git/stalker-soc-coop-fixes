# Rough Lua block-balance checker: strips comments/strings, counts block openers vs 'end'.
import re, sys

for path in sys.argv[1:]:
    src = open(path, encoding='cp1251').read()
    src = re.sub(r'--[^\n]*', '', src)
    src = re.sub(r'"(?:\\.|[^"\\\n])*"', '""', src)
    toks = re.findall(r'\b(function|if|for|while|do|repeat|until|end)\b', src)
    depth, opens, ends = 0, 0, 0
    pending_loop = 0
    for t in toks:
        if t in ('function', 'if'):
            opens += 1
        elif t in ('for', 'while'):
            opens += 1
            pending_loop += 1
        elif t == 'do':
            if pending_loop:
                pending_loop -= 1
            else:
                opens += 1
        elif t == 'end':
            ends += 1
    print(path.split('/')[-1].split('\\')[-1], 'openers', opens, 'ends', ends, 'OK' if opens == ends else 'MISMATCH')
