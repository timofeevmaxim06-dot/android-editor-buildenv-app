extends SceneTree
func _initialize() -> void:
	var ts := TextServerManager.get_primary_interface()
	var font := ThemeDB.fallback_font
	var paragraph := TextParagraph.new()
	paragraph.add_string("\tdraw_rect(rect, ", font, 24)
	paragraph.add_object("color", Vector2(24, 24), INLINE_ALIGNMENT_CENTER, 0)
	paragraph.add_string("Color(\"#123456\")", font, 24)
	paragraph.tab_align(PackedFloat32Array([57.6]))
	paragraph.set_break_flags(TextServer.BREAK_MANDATORY | TextServer.BREAK_WORD_BOUND | TextServer.BREAK_ADAPTIVE)
	paragraph.set_width(20)
	var rid := paragraph.get_rid()
	print("GLYPHS ",JSON.stringify(ts.shaped_text_sort_logical(rid)))
	print("BREAKS ",ts.shaped_text_get_line_breaks(rid,20,0,paragraph.get_break_flags()))
	print("LINE_COUNT ",paragraph.get_line_count())
	print("LINE_COUNT_AGAIN ",paragraph.get_line_count())
	quit()
