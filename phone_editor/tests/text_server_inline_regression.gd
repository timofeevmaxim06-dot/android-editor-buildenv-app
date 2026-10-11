extends SceneTree

func _initialize() -> void:
	var ts := TextServerManager.get_primary_interface()
	var font := ThemeDB.fallback_font
	var failures := []
	var cases := 0
	var object_cases := 0
	for prefix in ["", "\t", "    ", "\tdraw_rect(rect, ", "draw_string(font, Vector2(20, 30), \"Привет\", ", " ".repeat(40)]:
		for suffix in ["Color(1, 0, 0)", "Color(\"#123456\")", "Color(1, 0, 0), Color(0, 1, 0)", " ", ""]:
			for size in [14, 24, 48]:
				var rid := ts.create_shaped_text()
				ts.shaped_text_add_string(rid, prefix, font.get_rids(), size)
				ts.shaped_text_add_object(rid, "color", Vector2(size, size), INLINE_ALIGNMENT_CENTER, 0)
				ts.shaped_text_add_string(rid, suffix, font.get_rids(), size)
				ts.shaped_text_tab_align(rid, PackedFloat32Array([size * 2.4]))
				for width in [-400.0, -1.0, 0.0, 1.0, 2.0, 8.0, 20.0, 50.0, 100.0, 400.0]:
					for flags in [TextServer.BREAK_MANDATORY, TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND | TextServer.BREAK_ADAPTIVE, TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND | TextServer.BREAK_ADAPTIVE | TextServer.BREAK_TRIM_INDENT, TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND | TextServer.BREAK_ADAPTIVE | TextServer.BREAK_TRIM_START_EDGE_SPACES | TextServer.BREAK_TRIM_END_EDGE_SPACES | TextServer.BREAK_TRIM_INDENT]:
						var breaks := ts.shaped_text_get_line_breaks(rid, width, 0, flags)
						var advanced := ts.shaped_text_get_line_breaks_adv(rid, PackedFloat32Array([width]), 0, false, flags)
						# These APIs have different adaptive-wrap semantics in this base.
						# Each must still produce valid, forward substring ranges.
						cases += 1
						for ranges in [breaks, advanced]:
							for i in range(0, ranges.size(), 2):
								if ranges[i] < 0 or ranges[i+1] < ranges[i] or ranges[i+1] > prefix.length()+suffix.length():
									failures.append({"prefix":prefix,"suffix":suffix,"width":width,"size":size,"flags":flags,"breaks":Array(ranges)})
				# Check that the color object remains present after line slicing.
				if not suffix.is_empty():
					var slices := ts.shaped_text_get_line_breaks(rid, 100, 0, TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND | TextServer.BREAK_ADAPTIVE)
					var objects := 0
					for i in range(0, slices.size(), 2):
						if slices[i+1] < slices[i]: continue
						var slice := ts.shaped_text_substr(rid,slices[i],slices[i+1]-slices[i])
						if ts.shaped_text_get_objects(slice).has("color"): objects += 1
						ts.free_rid(slice)
					object_cases += 1
					if objects != 1: failures.append({"reason":"inline object lost or duplicated", "objects":objects,"prefix":prefix,"suffix":suffix})
				ts.free_rid(rid)
	print(JSON.stringify({"cases":cases,"object_cases":object_cases,"failures":failures}))
	quit(0 if failures.is_empty() else 1)
