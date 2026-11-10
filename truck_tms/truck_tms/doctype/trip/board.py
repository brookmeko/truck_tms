"""Board columns: the 11 detailed load stages grouped into 6 Kanban columns."""

BOARD_COLUMNS = [
	{"key": "assigned", "label": "Assigned", "stages": ["Assigned"], "color": "Gray"},
	{"key": "loading", "label": "Loading", "stages": ["Queued for Loading", "Loading", "Waiting Documents"], "color": "Blue"},
	{"key": "transit", "label": "In Transit", "stages": ["In Transit"], "color": "Cyan"},
	{"key": "customs", "label": "Border & Customs", "stages": ["Border Crossing", "At Customs"], "color": "Orange"},
	{"key": "unloading", "label": "Unloading", "stages": ["Waiting Unload Place", "Unload Queue", "Unloading"], "color": "Purple"},
	{"key": "settlement", "label": "Settlement", "stages": ["Delivered"], "color": "Green"},
]
STAGE_TO_COLUMN = {stage: col["key"] for col in BOARD_COLUMNS for stage in col["stages"]}
STAGE_TO_LABEL = {stage: col["label"] for col in BOARD_COLUMNS for stage in col["stages"]}
LABEL_TO_COLUMN = {col["label"]: col for col in BOARD_COLUMNS}
ALL_STAGES = [stage for col in BOARD_COLUMNS for stage in col["stages"]]
