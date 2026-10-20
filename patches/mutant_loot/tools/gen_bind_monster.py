"""Builds gamedata/scripts/bind_monster.script = the add-on's file (byte for byte, CP1251 comments kept) + 4 small edits.
usage: python -I gen_bind_monster.py <add-on bind_monster.script> <out>"""
import re, sys
src = open(sys.argv[1], 'rb').read()
n = 0
def sub(pat, rep, flags=0):
    global src, n
    new, c = re.subn(pat, rep, src, count=1, flags=flags)
    assert c == 1, pat
    src = new; n += 1

# 1. clients: the full binder is server only; clients get a small binder that arms the "Search" tip on dead mutants
sub(rb"\tif OnClient\(\) then \r\n\t\treturn \r\n\tend\r\n",
    b"\tif OnClient() then \r\n\t\t-- mutant_loot: clients only arm the Search tip / use callback on dead mutants\r\n\t\tobj:bind_object(mutant_loot.client_binder(obj))\r\n\t\treturn \r\n\tend\r\n")
# 2. server binder, dead branch of update()
sub(rb"\tif not object_alive then\r\n\t\treturn\r\n\tend\r\n",
    b"\tif not object_alive then\r\n\t\tmutant_loot.tick_dead(self.object, self)\r\n\t\treturn\r\n\tend\r\n")
# 3. death: the add-on dropped the part on the ground (PartSpawnName / PartSpawnProbaility); now one SoC roll, part goes into the corpse
sub(rb"\tlocal section = self\.object:section\(\)\r\n.*?\r\n\tend\r\n\r\n(?=\t--alife\(\):create\(\"mp_wpn_binoc\")",
    b"\t-- mutant_loot: one SoC roll per corpse; the part is taken from the corpse (Search), not lying on the ground\r\n\tmutant_loot.on_death(self.object, who)\r\n\r\n", re.S)
# 4. spawn alive: an old corpse's loot flags can not belong to this object
sub(rb"(\tif alife\(\):object\(self\.object:id\(\)\) == nil then\r\n\t\treturn false\r\n\tend\r\n)(?=\r\n--\tlocal pos)",
    rb"\1\tmutant_loot.on_alive_spawn(self.object:id())\r\n")
open(sys.argv[2], 'wb').write(src)
print('edits', n)
