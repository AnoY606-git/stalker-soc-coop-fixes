"""Makes the logic copies of patch soc_yan_x16_quests from the mod's own files (idempotent on the mod files).

  python make_logic.py <mod gamedata.db0 folder> <patch gamedata folder>

  coop_l08_yantar\\yan_smart_terrain_1_walker_saharov.ltx
      Sakharov no longer walks off for 50 s ("configuring helmets") after the results and no longer calls give_task: in SoC he hands the
      helmet over in the dialog. The old sections stay (an old save may be in one of them), they are just not entered any more.
  coop_l08_yantar\\space_restrictors\\yan_give_dev_psi_protection_helmet_space_restrictor.ltx
      no longer creates the helmet (the server tick of coop_soc_yan.script gives one to every player); keeps the autosave
  coop_l08_yantar\\space_restrictors\\ros_start_go_to_yantar_quest_task_space_restrictor.ltx
      no give_task (the Barkeep task of patch bar_soc_quests covers it); keeps the info flag the Rostok tasks read
  coop_l08_x16\\space_restrictors\\x16_start_find_the_installation_quest_task_space_restrictor.ltx
      no give_task (the tick gives the lab tasks to every player); keeps the info flag and the autosave
"""
import os
import sys

mod, out = sys.argv[1], sys.argv[2]


def rd(rel):
    return open(os.path.join(mod, *rel.split('/')), 'rb').read().decode('utf-8')


def wr(rel, text):
    p = os.path.join(out, *rel.split('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(text.encode('utf-8'))
    print('wrote', rel, len(text))


def sub(text, old, new, count=1):
    assert text.count(old) == count, (old, text.count(old))
    return text.replace(old, new)


# Sakharov
rel = 'configs/scripts/coop_l08_yantar/yan_smart_terrain_1_walker_saharov.ltx'
t = rd(rel)
line = [l for l in t.split('\n') if l.startswith('on_info') and 'psi_protection_helmet_idle' in l and 'TALK_TO_THE_SAHAROV_MEASUREMENTS' in l]
assert len(line) == 1, line
t = t.replace(line[0] + '\n', ';(patch soc_yan_x16_quests) the walk to the room for the helmet is gone: SoC hands the helmet over in the dialog\n')
t = sub(t, ' %=give_task(yan_start_configuring_helmets_quest_task) =scenario_autosave(st_configuring_helmets)%', ' %=scenario_autosave(st_configuring_helmets)%')
wr(rel, t)

# helmet restrictor
rel = 'configs/scripts/coop_l08_yantar/space_restrictors/yan_give_dev_psi_protection_helmet_space_restrictor.ltx'
t = rd(rel)
t = sub(t, 'sr_idle@nil %=give_dev_psi_protection_helmet =scenario_autosave(st_sneak_into_the_x_16_lab)%', 'sr_idle@nil %=scenario_autosave(st_sneak_into_the_x_16_lab)%')
wr(rel, t)

# Rostok zone on Yantar
rel = 'configs/scripts/coop_l08_yantar/space_restrictors/ros_start_go_to_yantar_quest_task_space_restrictor.ltx'
t = rd(rel)
t = sub(t, ' =give_task(yan_start_go_to_yantar_quest_task)%', '%', count=2)
wr(rel, t)

# X16 entrance zone
rel = 'configs/scripts/coop_l08_x16/space_restrictors/x16_start_find_the_installation_quest_task_space_restrictor.ltx'
t = rd(rel)
t = sub(t, ' =give_task(x16_start_find_the_installation_quest_task)', '', count=2)
wr(rel, t)
