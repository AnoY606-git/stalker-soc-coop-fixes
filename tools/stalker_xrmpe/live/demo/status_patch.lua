-- demo for live.reload: re-defines one function of the loaded script "coop_scenes" without restarting the game
function status()
	return "PATCHED by live.reload: coop_scenes.status() now answers from the reloaded file"
end
