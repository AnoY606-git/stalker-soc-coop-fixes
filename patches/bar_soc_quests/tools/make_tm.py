"""Task files of the Bar and Rostok (patch bar_soc_quests), made from the mod's own files (idempotent).

  python make_tm.py <mod source gamedata.db0 dir>

Writes (same encoding as the mod's file, UTF-8, CRLF) patches\\bar_soc_quests\\gamedata\\configs\\misc\\tm_coop_l05_bar.ltx and tm_coop_l06_rostok.ltx: the mod's file with these sections
replaced or added. Nothing else of the mod's files is touched.
"""
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
patch = os.path.dirname(here)
if len(sys.argv) < 2:
    sys.exit('usage: make_tm.py <mod source gamedata.db0 dir>')
mod = sys.argv[1]

SAHAROV_TALK = 'YAN_SMART_TERRAIN_1_ECOLOG_SAHAROV_TALK_TO_THE_SAHAROV_X16_STOP_DIALOG_INFO'
KRUGLOV_TALK_YAN = 'YAN_SMART_TERRAIN_1_ECOLOG_KRUGLOV_X16_PREPARATION_STOP_DIALOG_INFO'


class Tm:
    def __init__(self, path):
        raw = open(path, 'rb').read()
        try:
            self.enc = 'utf-8'
            self.t = raw.decode('utf-8').replace('\r\n', '\n')
        except UnicodeDecodeError:
            self.enc = 'cp1251'
            self.t = raw.decode('cp1251').replace('\r\n', '\n')

    @staticmethod
    def make(name, comment, lines):
        body = ''.join('%-40s= %s\n' % (k, v) for k, v in lines)
        return '%s[%s]\n%s' % (''.join('; %s\n' % c for c in comment), name, body)

    def put(self, name, comment, lines, after=None):
        """replace (header, the comment lines right above it, key lines) or append / insert behind section `after`"""
        body = self.make(name, comment, lines).rstrip('\n').split('\n')
        L = self.t.split('\n')
        h = next((i for i, x in enumerate(L) if x.strip() == '[' + name + ']'), None)

        def section_end(h):
            end = h + 1
            while end < len(L) and not L[end].startswith('[') and not (L[end].startswith(';') and end + 1 < len(L) and L[end + 1].startswith('[')):
                end += 1
            while end - 1 > h and (L[end - 1].strip() == '' or L[end - 1].startswith(';')):
                end -= 1
            return end

        if h is None:
            if after is not None:
                ah = next(i for i, x in enumerate(L) if x.strip() == '[' + after + ']')
                end = section_end(ah)
                L[end:end] = [''] + body
            else:
                while L and L[-1].strip() == '':
                    L.pop()
                L += [''] + body + ['']
        else:
            start = h
            while start > 0 and L[start - 1].startswith(';') and not L[start - 1].startswith(';--'):   # keep the ;---- header banners
                start -= 1
            end = section_end(h)
            L[start:end] = body
        self.t = '\n'.join(L)

    def save(self, path):
        data = self.t.replace('\n', '\r\n').encode(self.enc)
        old = open(path, 'rb').read() if os.path.exists(path) else None
        if old != data:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'wb').write(data)
            print('written', os.path.relpath(path, os.path.dirname(os.path.dirname(patch))))
        else:
            print('unchanged', os.path.basename(path))


# ---------------------------------------------------------------------------------------------------
# Bar
# ---------------------------------------------------------------------------------------------------
bar = Tm(os.path.join(mod, 'configs', 'misc', 'tm_coop_l05_bar.ltx'))
bar.put('bar_start_go_to_yantar_quest_task', [
    'SoC bar_x16_documents (patch bar_soc_quests): ONE task for the whole X16 documents job, given to every player by coop_soc_barros.script when the Barkeep',
    'job is accepted (flag BAR_X16_DOCUMENTS_START). Its text and its marker follow the objectives: "Talk to the scientists" (x16_yantar, level changers on the',
    'way, then the scientists), "Find the X16 documents" (look_for_x16_lab, after the first talk with Sakharov), "Bring the documents to the Barkeep"',
    '(bring_x16_documents, once the party holds them). Done when the Barkeep has them. The Rostok copy of this task (ros_start_go_to_yantar) is hidden.'], [
    ('icon', 'ui_inGame2_bar_start_go_to_yantar_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_bar_start_go_to_yantar_quest_task_name'),
    ('descr', '{+YAN_X16_DOCUMENTS_GAIN} coop_soc_x16_bring_descr, {+%s} coop_soc_x16_look_descr, st_bar_start_go_to_yantar_quest_task_descr' % SAHAROV_TALK),
    ('target', '{+YAN_X16_DOCUMENTS_GAIN} bar_smart_terrain_1_stalker_barmen, {+%s} yan_smart_terrain_1_ecolog_saharov, '
               '{+ROS_START_GO_TO_YANTAR_QUEST_TASK_INFO} yan_smart_terrain_1_ecolog_saharov, {+BAR_START_GO_TO_YANTAR_QUEST_TASK_INFO} ros_yan_level_changer, '
               'bar_ros_level_changer' % SAHAROV_TALK),
    ('condlist_0', '{+BAR_X16_DOCUMENTS_DONE} complete')])
bar.put('bar_start_go_to_military_quest_task', [
    'SoC bar_radar_deactivate (patch bar_soc_quests): given to every player when the Barkeep job "Turn off the Brain Scorcher" is accepted (flag',
    'BAR_DEACTIVATE_RADAR_START). ONE task up to the Radar level: the marker is the Bar exit to Military, once the party is there the Military exit to the',
    'Radar (it is the step the level maker had on the Military level, now hidden). Done on the Radar level, where rad_start_go_to_radar takes over.'], [
    ('icon', 'ui_inGame2_bar_start_go_to_military_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_bar_start_go_to_military_quest_task_name'), ('descr', 'st_bar_start_go_to_military_quest_task_descr'),
    ('target', '{+BAR_START_GO_TO_MILITARY_QUEST_TASK_INFO} mil_rad_level_changer, bar_mil_level_changer'),
    ('condlist_0', '{+MIL_START_GO_TO_RADAR_QUEST_TASK_INFO} complete')])
bar.put('bar_start_find_the_family_gun_quest_task', [
    'SoC bar_hunter_rifle objective "Find the family rifle" (patch bar_soc_quests): done when a player holds the rifle (flag BAR_HUNTER_RIFLE_FOUND),',
    'the next objective is bar_soc_hunter_return_task'], [
    ('icon', 'ui_inGame2_bar_start_find_the_family_gun_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_bar_start_find_the_family_gun_quest_task_name'), ('descr', 'st_bar_start_find_the_family_gun_quest_task_descr'),
    ('target', 'nil'), ('condlist_0', '{+BAR_HUNTER_RIFLE_FOUND} complete')])
bar.put('bar_soc_hunter_return_task', [
    'SoC bar_hunter_rifle objective "Return the rifle to the hunter at the Bar" (patch bar_soc_quests): done when the hunter has the rifle (his dialog sets the flag)'], [
    ('icon', 'ui_inGame2_bar_start_find_the_family_gun_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_bar_start_find_the_family_gun_quest_task_name'), ('descr', 'coop_soc_hunter_return_descr'),
    ('target', 'bar_smart_terrain_1_stalker_bad_hunter'),
    ('condlist_0', '{+BAR_SMART_TERRAIN_1_STALKER_BAD_HUNTER_FIND_THE_FAMILY_GUN_IDLE_STOP_DIALOG_INFO} complete')],
    after='bar_start_find_the_family_gun_quest_task')
bar.save(os.path.join(patch, 'gamedata', 'configs', 'misc', 'tm_coop_l05_bar.ltx'))

# ---------------------------------------------------------------------------------------------------
# Rostok (Wild Territory)
# ---------------------------------------------------------------------------------------------------
ros = Tm(os.path.join(mod, 'configs', 'misc', 'tm_coop_l06_rostok.ltx'))
ros.put('ros_start_help_kruglov_quest_task', [
    'SoC bar_resque_information objective "Get through to Kruglov" (patch bar_soc_quests): done when the Mercs are dead, or when a player reached Kruglov',
    '(he speaks and starts walking, flag BAR_KRUGLOV_FOLLOW_ACTOR). The next steps are given by coop_soc_barros.script to every player.'], [
    ('icon', 'ui_inGame2_ros_start_help_kruglov_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_ros_start_help_kruglov_quest_task_name'), ('descr', 'st_ros_start_help_kruglov_quest_task_descr'),
    ('target', 'ros_smart_terrain_4_ecolog_kruglov'),
    ('condlist_0', '{+ROS_SMART_TERRAIN_3_KILLER_1_SQUAD_DEAD} complete'), ('condlist_1', '{+BAR_KRUGLOV_FOLLOW_ACTOR} complete')])
ros.put('ros_soc_kruglov_talk_task', [
    'SoC bar_resque_information objective "Talk to professor Kruglov" (patch bar_soc_quests): the Mercs are dead, now reach Kruglov; he speaks when a player',
    'is close (his walker logic sets BAR_KRUGLOV_FOLLOW_ACTOR, SoC bar_kruglov_follow_actor, which starts the escort)'], [
    ('icon', 'ui_inGame2_ros_start_help_kruglov_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_ros_start_help_kruglov_quest_task_name'), ('descr', 'coop_soc_kruglov_talk_descr'),
    ('target', 'ros_smart_terrain_4_ecolog_kruglov'), ('condlist_0', '{+BAR_KRUGLOV_FOLLOW_ACTOR} complete')],
    after='ros_start_help_kruglov_quest_task')
ros.put('ros_start_escort_kruglov_to_yantar_quest_task', [
    'SoC bar_resque_information_2 objective "Lead Kruglov to the exit to Yantar" (patch bar_soc_quests): given to every player when Kruglov follows (flag',
    'BAR_KRUGLOV_FOLLOW_ACTOR), done when he is on Yantar'], [
    ('icon', 'ui_inGame2_ros_start_escort_kruglov_to_yantar_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_ros_start_escort_kruglov_to_yantar_quest_task_name'), ('descr', 'st_ros_start_escort_kruglov_to_yantar_quest_task_descr'),
    ('target', 'ros_smart_terrain_4_ecolog_kruglov'), ('condlist_0', '{+YAN_SMART_TERRAIN_1_WALKER_KRUGLOV_GO_TO_SAXAROV_INFO} complete')])
ros.put('ros_soc_kruglov_bring_task', [
    'SoC bar_resque_information_2 objective "Talk to Kruglov" (patch bar_soc_quests): Kruglov is on Yantar, talk to him (his first Yantar talk completes it)'], [
    ('icon', 'ui_inGame2_ros_start_escort_kruglov_to_yantar_quest_task'), ('prior', '200'), ('storyline', 'true'),
    ('title', 'st_ros_start_escort_kruglov_to_yantar_quest_task_name'), ('descr', 'coop_soc_kruglov_bring_descr'),
    ('target', 'yan_smart_terrain_1_ecolog_kruglov'), ('condlist_0', '{+%s} complete' % KRUGLOV_TALK_YAN)],
    after='ros_start_escort_kruglov_to_yantar_quest_task')
ros.save(os.path.join(patch, 'gamedata', 'configs', 'misc', 'tm_coop_l06_rostok.ltx'))
