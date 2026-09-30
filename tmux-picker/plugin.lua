local function workspace_command()
	local command = os.getenv("TMUX_WORKSPACE_COMMAND")
	if command and command ~= "" then
		return command
	end

	local plugin_dir = os.getenv("TMUX_WORKSPACE_PLUGIN_DIR")
	if plugin_dir and plugin_dir ~= "" then
		return plugin_dir .. "/bin/tmux-workspace"
	end

	local source = debug.getinfo(1, "S").source:gsub("^@", "")
	local repository = source:match("^(.*)/tmux%-picker/plugin%.lua$")
	return repository and (repository .. "/bin/tmux-workspace") or nil
end

return {
	api_version = 1,
	id = "tmux-workspace",
	setup = function(ctx)
		ctx.register_view({
			id = "tmux-workspace.new",
			order = 20,
			label = "new workspace",
			key = "ctrl-n",
			chord = "C-n",
			prompt = "new workspace > ",
			color = ctx.config.colors.teal,
			list = function() end,
			query = function(name)
				name = ctx.util.trim(name)
				if name == "" then
					return
				end

				local command = workspace_command()
				if not command then
					ctx.notify("tmux-workspace executable not found")
					return
				end

				local invocation = "PATH="
					.. ctx.util.shell_quote(ctx.config.path_prefix)
					.. " "
					.. ctx.util.shell_quote(command)
					.. " "
					.. ctx.util.shell_quote(name)
				local ok, reason, code = os.execute(invocation)
				if ok ~= true and ok ~= 0 then
					ctx.notify("tmux-workspace failed (" .. tostring(code or reason or ok) .. ")")
				end
			end,
		})
	end,
}
