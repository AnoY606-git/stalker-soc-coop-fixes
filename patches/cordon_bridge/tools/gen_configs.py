"""Generates the config files of the cordon_bridge patch from the Shadow of COOP 8.0 sources.

  python gen_configs.py <Shadow of COOP 8.0\\source\\gamedata.db0\\configs> <patch gamedata\\configs>

Writes (byte-safe, same line endings as the source):
  scripts\\coop_l01_escape\\esc_smart_terrain_7_walker_army.ltx      five army soldiers (SoC posts 1, 3, 4, 5, 6), hit / kill by a player -> order given
  scripts\\coop_l01_escape\\esc_smart_terrain_7_walker_kuznetsov.ltx  Kuznetsov (SoC post 2) gets the same hit / kill rule
  scripts\\coop_l01_escape\\smart\\esc_smart_terrain_7.ltx             one more job (army_5); max_population stays at the mod's value
  misc\\squad_descr_coop_l01_escape.ltx                               squad 4 has two soldiers (post 5 and post 6)

Where the keys go (xr_logic.configure_schemes): the generic schemes on_hit / on_death are read from the JOB section [logic@...] only, never from the
active [walker@...] section. combat_ignore_cond / meet / on_info stay in the [walker@...] sections (they are re-read on every section switch).
"""
import os
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
NL = b"\r\n"

FLAG = "ESC_THE_ORDER_TO_ATTACK_THE_PLAYERS_INFO"
DEAD = ["ESC_SMART_TERRAIN_7_MILITARY_1_SQUAD_DEAD", "ESC_SMART_TERRAIN_7_MILITARY_2_SQUAD_DEAD",
        "ESC_SMART_TERRAIN_7_MILITARY_3_SQUAD_DEAD", "ESC_SMART_TERRAIN_7_MILITARY_4_SQUAD_DEAD",
        "ESC_SMART_TERRAIN_7_MILITARY_KUZNETSOV_SQUAD_DEAD", "ESC_SMART_TERRAIN_7_MILITARY_SHTIRTS_SQUAD_DEAD"]
HIT = "hit@esc_bridge_soldier"
DEATH = "death@esc_bridge_soldier"
SAVE = "=scenario_autosave(st_5_bottles_of_vodka_for_kuznetsov_fail)"
# the first hit / kill by ANY player gives the order once (story flag: shared, saved with the game); one autosave, like the restrictor makes.
# hit_by_actor / killed_by_actor are the xrMPE conditions: true for every player actor, false for mutants and NPCs (SoC hit@soldier / death@soldier).
HITRULE = "{=hit_by_actor -%s} %%+%s %s%%" % (FLAG, FLAG, SAVE)
DEATHRULE = "{=killed_by_actor -%s} %%+%s %s%%" % (FLAG, FLAG, SAVE)


def kv(k, v):
    return ("%-52s= %s" % (k, v)).encode("latin1")


def army(n):
    s = "esc_smart_terrain_7_walker_army_%d" % n
    L = []
    a = L.append
    a(("[logic@%s]" % s).encode())
    a(kv("suitable", "{=check_npc_name(sim_default_military_0)} true"))
    a(kv("active", "walker@" + s))
    a(kv("prior", "300"))
    a(kv("on_hit", HIT))
    a(kv("on_death", DEATH))
    a(b"")
    a(("[walker@%s]" % s).encode())
    common = [("path_walk", "walker_%d_walk" % n), ("path_look", "walker_%d_look" % n), ("def_state_moving", "walk"),
              ("def_state_standing", "guard"), ("invulnerable", "false"), ("gather_items_enabled", "false"),
              ("help_wounded_enabled", "false"), ("corpse_detection_enabled", "false")]
    for k, v in common:
        a(kv(k, v))
    a(kv("combat_ignore_cond", "true"))
    a(kv("combat_ignore_keep_when_attacked", "true"))
    a(kv("meet", "no_meet"))
    a(kv("on_info", "{+%s} walker@%s_attack_players" % (FLAG, s)))
    for i, d in enumerate(DEAD, 1):
        a(kv("on_info%d" % i, "{+%s} walker@%s_attack_players" % (d, s)))
    a(b"")
    a(("[walker@%s_attack_players]" % s).encode())
    for k, v in common:
        a(kv(k, v))
    a(kv("combat_ignore_cond", "false"))
    a(kv("combat_ignore_keep_when_attacked", "false"))
    a(kv("meet", "no_meet"))
    a(b"")
    a(b";================================================")
    a(b"")
    return NL.join(L) + NL


def rules():
    return NL.join([
        b"[" + HIT.encode() + b"]",
        kv("on_info", HITRULE),
        b"",
        b"[" + DEATH.encode() + b"]",
        kv("on_info", DEATHRULE),
        b"",
    ]) + NL


def army_file():
    out = b""
    for n in range(1, 6):
        out += army(n)
    return out + rules()


def put(rel, data):
    p = os.path.join(dst, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(data)
    print("wrote", rel, len(data))


put(r"scripts\coop_l01_escape\esc_smart_terrain_7_walker_army.ltx", army_file())

# --- Kuznetsov: same rules, in his [logic@...] section (right after the "prior" line)
k = open(os.path.join(src, r"scripts\coop_l01_escape\esc_smart_terrain_7_walker_kuznetsov.ltx"), "rb").read()
assert b"on_hit" not in k and b"on_death" not in k, "source already has hit rules"
m = re.search(rb"(\[logic@esc_smart_terrain_7_walker_kuznetsov\][^\[]*?prior[^\r\n]*)(\r?\n)", k)
assert m, "kuznetsov logic section not found"
k = k[:m.end(1)] + NL + kv("on_hit", HIT) + NL + kv("on_death", DEATH) + k[m.end(1):]
k = k.rstrip(b"\r\n") + NL + NL + rules()
put(r"scripts\coop_l01_escape\esc_smart_terrain_7_walker_kuznetsov.ltx", k)

# --- smart terrain: the job of soldier 5. max_population is NOT touched: it counts simulation squads that may move in (the bridge squads
# have a target_smart and are not counted), a bigger value would let roaming squads in.
s = open(os.path.join(src, r"scripts\coop_l01_escape\smart\esc_smart_terrain_7.ltx"), "rb").read()
m = re.search(rb"esc_smart_terrain_7_walker_army_4[^\r\n]*", s)
assert m, "army_4 job line not found"
s = s[:m.end()] + NL + m.group(0).replace(b"army_4", b"army_5") + s[m.end():]
put(r"scripts\coop_l01_escape\smart\esc_smart_terrain_7.ltx", s)

# --- squad description: the 4th bridge squad gets a second soldier (soldier 5). No new squad, so simulation.ltx (shipped by
# sarcophagus_count), story_flags_table and the DEAD flags stay untouched.
sd = open(os.path.join(src, r"misc\squad_descr_coop_l01_escape.ltx"), "rb").read()
key = b"[esc_smart_terrain_7_military_4_squad]"
i = sd.index(key)
j = sd.index(b"npc = sim_default_military_0", i)
assert j - i < 80, "unexpected squad 4 block"
sd = sd[:j] + b"npc = sim_default_military_0, sim_default_military_0" + sd[j + len(b"npc = sim_default_military_0"):]
put(r"misc\squad_descr_coop_l01_escape.ltx", sd)
