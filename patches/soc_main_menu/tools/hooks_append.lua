

-- ---- SoC main menu selector (socfx_mm_selector.script) ----------------------------------------------------------------------
-- Wraps the functions above: the selector statics are created with the menu, follow the mouse (CUIScriptWnd:OnMouse) and are
-- animated every frame. Nothing else in this file is changed.
local socfx_base_InitControls = main_menu.InitControls
function main_menu:InitControls()
	-- UE4 styles: the picture statics are made first so that they are drawn below the buttons
	local xml0 = CScriptXmlInit()
	xml0:ParseFile("ui_mm_main.xml")
	socfx_mm_selector.pre(self, xml0)
	socfx_base_InitControls(self)
	if self.gs_profile and not level.present() then
		self.socfx_page = "menu_main_logout"
	end
	local xml = CScriptXmlInit()
	xml:ParseFile("ui_mm_main.xml")
	socfx_mm_selector.init(self, xml)
end

local socfx_base_Update = main_menu.Update
function main_menu:Update()
	socfx_base_Update(self)
	socfx_mm_selector.update(self)
end

function main_menu:OnMouse(x, y, mouse_action)
	socfx_mm_selector.on_mouse(self, x, y, mouse_action)
	return CUIScriptWnd.OnMouse(self, x, y, mouse_action)
end

local socfx_base_logout = main_menu.OnButton_logout_clicked
function main_menu:OnButton_logout_clicked()
	socfx_base_logout(self)
	self.socfx_page = "menu_main"
end
