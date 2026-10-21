"""Level logic copies of patch bar_soc_quests (idempotent): the mod's file with one effect added, or an inert one.

  python apply_logic.py <mod source gamedata.db0 dir>

  coop_l06_rostok\\ros_smart_terrain_4_walker_kruglov.ltx   Kruglov speaks and starts walking when a player is within 2 m of him: that sets
      BAR_KRUGLOV_FOLLOW_ACTOR (SoC info bar_kruglov_follow_actor, which starts bar_resque_information_2). The walk itself is unchanged.
  coop_l05_bar\\space_restrictors\\bar_start_find_the_family_gun_quest_task_space_restrictor.ltx   inert: the hunter tasks are given to every player by
      coop_soc_barros.script (the restrictor gave the first one to the first player only)
"""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.dirname(here)
if len(sys.argv) < 2:
    sys.exit('usage: apply_logic.py <mod source gamedata.db0 dir>')
mod = sys.argv[1]
OLD = b'on_info 											= {=dist_to_actor_le(2)} walker@ros_smart_terrain_4_walker_kruglov_help_1_start'
NEW = OLD + b' %+BAR_KRUGLOV_FOLLOW_ACTOR%'
NL = b'\r\n'


def write(rel, fn):
    src = open(os.path.join(mod, 'configs', 'scripts', rel), 'rb').read()
    new = fn(src)
    dst = os.path.join(patch, 'gamedata', 'configs', 'scripts', rel)
    old = open(dst, 'rb').read() if os.path.exists(dst) else None
    if old != new:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(new)
        print('written', rel)
    else:
        print('unchanged', rel)


def kruglov(src):
    assert src.count(OLD) == 1, 'anchor not found'
    return src.replace(OLD, NEW)


HUNTER = NL.join([b'[logic]',
                  b'active 												= sr_idle@nil',
                  b'',
                  b'; Original logic: on the flag of the accepted hunter quest it gave bar_start_find_the_family_gun_quest_task (give_task: first player only).',
                  b'; The hunter tasks (find the rifle, return it) are given to every player by coop_soc_barros.script (patch bar_soc_quests).',
                  b'[sr_idle@nil]'])


def hunter_restrictor(src):
    assert b'give_task(bar_start_find_the_family_gun_quest_task)' in src, 'anchor not found'
    return HUNTER


write(os.path.join('coop_l06_rostok', 'ros_smart_terrain_4_walker_kruglov.ltx'), kruglov)
write(os.path.join('coop_l05_bar', 'space_restrictors', 'bar_start_find_the_family_gun_quest_task_space_restrictor.ltx'), hunter_restrictor)
