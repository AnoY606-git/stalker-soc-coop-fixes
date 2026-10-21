
-- TEST ONLY (never shipped): drives the menu through its pages and asks the harness for an engine screenshot of each.
local socfx_test_Update = main_menu.Update
local function socfx_snap(tag)
	local ok, err = pcall(function()
		local f = io.open(getFS():update_path("$logs$", "qa_cmd.txt"), "a")
		f:write("console screenshot jpg\n")
		f:close()
	end)
	printf_msg("socfx TEST snap %s %s", tag, ok and "ok" or tostring(err))
end
local function socfx_hover(self, row)
	local x, y = socfx_mm_selector.test_point(row)
	socfx_mm_selector.on_mouse(self, x, y, 6)
end
local function socfx_page(self, name)
	self.shniaga:SetPage(CUIMMShniaga.epi_main, "ui_mm_main.xml", name)
	self.shniaga:ShowPage(CUIMMShniaga.epi_main)
	printf_msg("socfx TEST page %s", name)
end
local socfx_steps = {
	{ 3, function(self) socfx_hover(self, 3) end },
	{ 6, function(self) socfx_snap("coop_row3") end },
	{ 7, function(self) socfx_hover(self, 6) end },
	{ 10, function(self) socfx_snap("coop_row6") end },
	{ 11, function(self) socfx_page(self, "menu_main"); socfx_hover(self, 1) end },
	{ 14, function(self) socfx_snap("main_row1") end },
	{ 15, function(self) socfx_page(self, "menu_main_logout"); socfx_hover(self, 4) end },
	{ 18, function(self) socfx_snap("logout_row4") end },
	{ 19, function(self) socfx_page(self, "menu_main_mm"); socfx_hover(self, 0) end },
	{ 22, function(self) socfx_snap("mm_row0") end },
	{ 23, function(self) socfx_page(self, "menu_network_game"); socfx_hover(self, 2) end },
	{ 26, function(self) socfx_snap("netgame_row2") end },
	{ 27, function(self) socfx_page(self, "menu_main_coop_mm"); socfx_hover(self, 0) end },
}
function main_menu:Update()
	socfx_test_Update(self)
	self.socfx_t = (self.socfx_t or 0) + (device().f_time_delta or 0)
	self.socfx_step = self.socfx_step or 1
	local s = socfx_steps[self.socfx_step]
	if s and self.socfx_t >= s[1] then
		self.socfx_step = self.socfx_step + 1
		local ok, err = pcall(s[2], self)
		if not ok then printf_msg("socfx TEST step failed %s", tostring(err)) end
	end
end
