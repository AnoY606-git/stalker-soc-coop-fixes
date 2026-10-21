# Offline logic check of scripts/soc_talk_ui.script and scripts/pda.dscript with a mocked engine (needs the lupa module).
# Usage: python mock_test.py       (prints OK or the failing assertion)
import os, sys
from lupa import LuaRuntime

here = os.path.dirname(os.path.abspath(__file__))
sdir = os.path.join(here, '..', 'gamedata', 'scripts')

lua = LuaRuntime(unpack_returned_tuples=True)
mock = r'''
log = {}
unpack = unpack or table.unpack
function printf_msg(fmt, ...) table.insert(log, string.format(fmt, ...)) end
function super() end
function class(name)
  return function(base)
    local c = {}
    c.__index = c
    setmetatable(c, { __index = base, __call = function(cls, ...)
      local o = setmetatable({}, cls)
      if cls.__init then cls.__init(o, ...) end
      return o
    end })
    _G[name] = c
  end
end
CUIScriptWnd = { Show = function(self, b) self.shown = b end }
statics = {}
function mkstatic(n)
  local s = { name = n, text = nil, shown = true, tex = nil }
  function s:SetText(t) self.text = t end
  function s:Show(b) self.shown = b end
  function s:InitTexture(t) self.tex = t end
  function s:SetStretchTexture(b) self.stretch = b end
  statics[n] = s
  return s
end
CScriptXmlInit = function()
  local x = {}
  function x:ParseFile(f) xml_file = f end
  function x:InitWindow(n, i, w) win_node = n end
  function x:InitStatic(n, w) return mkstatic(n) end
  return x
end
-- the engine returns the id itself for an unknown string: ui_soc_talk_loner stays untranslated here to test the fallback to "stalker"
game = { translate_string = function(id) if string.sub(id, 1, 12) == "ui_soc_talk_" then return id end return "T(" .. id .. ")" end }
game_object = { friend = 0, neutral = 1, enemy = 2 }
function system_ini()
  return { r_string = function(self, sec, line)
    assert(sec == "game_relations" and line == "rating")
    return "novice, 300, experienced, 600, veteran, 900, master"
  end }
end
render = { added = 0, removed = 0, wnd = nil }
function get_hud()
  return {
    AddDialogToRender = function(self, w) render.added = render.added + 1; render.wnd = w end,
    RemoveDialogToRender = function(self, w) render.removed = render.removed + 1 end,
  }
end
function mkobj(o)
  o.id = function(self) return o._id end
  o.position = function(self) return { distance_to = function(_, p) return 1 end } end
  o.character_name = function(self) return o._name end
  o.character_icon = function(self) return o._icon end
  o.character_rank = function(self) return o._rank end
  o.character_community = function(self) return o._comm end
  o.is_talking = function(self) return o._talking end
  return o
end
actor = mkobj({ _id = 0, _name = "Marked", _icon = "ui_actor_p", _rank = 120, _comm = "actor", _partner = 77 })
function actor:get_talk_partner_id() return self._partner end
npc = mkobj({ _id = 77, _name = "Trader", _icon = "ui_npc_u_trader", _rank = 650, _comm = "trader", _talking = true })
function npc:relation(a) return game_object.neutral end
level = { object_by_id = function(id) if id == 77 then return npc end end }
db = { storage = { [77] = { object = npc } }, actor = actor }
function getLocalActor() return actor end
-- pda.script stand-in the dscript is appended to
pda_calls = {}
function dialog_wnd_showed() table.insert(pda_calls, "showed") end
function dialog_wnd_closed() table.insert(pda_calls, "closed") end
'''
lua.execute(mock)
lua.execute(open(os.path.join(sdir, 'soc_talk_ui.script'), encoding='ascii').read().replace('\r\n', '\n') + '\nsoc_talk_ui = { on_show = on_show, on_hide = on_hide, is_shown = is_shown }\n')
lua.execute(open(os.path.join(sdir, 'pda.dscript'), encoding='ascii').read().replace('\r\n', '\n'))
g = lua.globals()

lua.execute('dialog_wnd_showed()')
st = g.statics
assert g.xml_file == 'soc_talk_info.xml' and g.win_node == 'info'
t = lambda n: st[n].text
assert t('l_name') == 'Marked' and t('r_name') == 'Trader', (t('l_name'), t('r_name'))
assert t('title_npc') == 'Trader' and t('title_actor') == 'Marked'
assert st['l_icon'].tex == 'ui_actor_p' and st['r_icon'].tex == 'ui_npc_u_trader'
assert t('l_rank_v') == 'T(novice)' and t('r_rank_v') == 'T(veteran)', (t('l_rank_v'), t('r_rank_v'))
assert t('l_comm_v') == 'T(stalker)', t('l_comm_v')          # fallback because ui_soc_talk_loner is untranslated here
assert t('r_comm_v') == 'T(trader)'
assert t('r_rel_v') == 'T(neutral)'
assert st['l_rel_c'].shown is False and st['l_rel_v'].shown is False   # player has no relation row
assert g.render.added == 1 and g.pda_calls[1] == 'showed'
assert lua.eval('soc_talk_ui.is_shown()') is True
lua.execute('dialog_wnd_showed()')                                      # second show must not add twice
assert g.render.added == 1
lua.execute('dialog_wnd_closed()')
assert g.render.removed == 1 and g.pda_calls[3] == 'closed'
assert lua.eval('soc_talk_ui.is_shown()') is False
lua.execute('dialog_wnd_showed()')                                      # reopen reuses the window
assert g.render.added == 2
# partner id unknown: fallback scan via is_talking
lua.execute('actor._partner = 65535; dialog_wnd_closed(); dialog_wnd_showed()')
assert st['r_name'].text == 'Trader'
# nobody to talk to: partner panel hidden, no error
lua.execute('actor._partner = 65535; npc._talking = false; dialog_wnd_closed(); dialog_wnd_showed()')
assert st['r_panel'].shown is False and st['r_name'].shown is False
# max rank
lua.execute('npc._talking = true; npc._rank = 5000; actor._partner = 77; dialog_wnd_closed(); dialog_wnd_showed()')
assert st['r_rank_v'].text == 'T(master)'
# errors are swallowed
lua.execute('get_hud = function() error("boom") end; dialog_wnd_closed(); dialog_wnd_showed()')
assert lua.eval('(function() for _, v in ipairs(log) do if string.find(v, "failed", 1, true) then return true end end return false end)()')
print('OK')
