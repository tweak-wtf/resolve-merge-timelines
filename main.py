import sys

clipcolor_names = [
    "Orange",
    "Apricot",
    "Yellow",
    "Lime",
    "Olive",
    "Green",
    "Teal",
    "Navy",
    "Blue",
    "Purple",
    "Violet",
    "Pink",
    "Tan",
    "Beige",
    "Brown",
    "Chocolate",
]
merge_names = ["Reel Name", "Source File"]


class Timeline:
    def __init__(self, resolve_obj) -> None:
        self.__resolve_obj = resolve_obj

    @property
    def cut_in(self):
        return self.__resolve_obj.GetLeftOffset()

    @property
    def cut_out(self):
        return self.__resolve_obj.GetDuration() - self.cut_in


class RPManager:
    def __init__(self) -> None:
        self.__manager = bmd.scriptapp("Resolve").GetProjectManager()
        self.__current_project = self.manager.GetCurrentProject()
        self.__mediapool = self.current_project.GetMediaPool()
        self.__timelines: list
        print(self.manager)

    @property
    def manager(self):
        return self.__manager

    @property
    def all_timelines(self):
        result = [Timeline(i) for i in self.manager.GetAllTimelines()]
        return self.__manager

    @property
    def fps_map(self):
        return {
            "16": 16.0,
            "18": 18.0,
            "23": 23.976,
            "24": 24.0,
            "24.0": 24.0,
            "25": 25.0,
            "29": 29.97,
            "30": 30.0,
            "30.0": 30.0,
            "47": 47.952,
            "48": 48.0,
            "50": 50.0,
            "59": 59.94,
            "60": 60.0,
            "72": 72.0,
            "95": 95.904,
            "96": 96.0,
            "100": 100.0,
            "119": 119.88,
            "120": 120.0,
        }

    @property
    def current_project(self):
        return self.__current_project

    @property
    def current_project_name(self):
        return self.__current_project.GetName()

    @property
    def timelines(self):
        return self.__timelines

    @timelines.setter
    def timelines(self):
        return self.__timelines

    @property
    def mediapool(self):
        return self.__mediapool


class Merger:
    def __init__(self, fu) -> None:
        self.fu = fu
        self.__mode: str
        self.__gapsize: int
        self.__timeline_in: str
        self.__timeline_out: str
        self.__color_to_skip: str
        self.__timeline_filter: str

    @property
    def timeline_in(self):
        return self.__timeline_in

    @timeline_in.setter
    def timeline_in(self, var):
        self.__timeline_in = var

    @property
    def timeline_out(self):
        return self.__timeline_out

    @timeline_out.setter
    def timeline_out(self, var):
        self.__timeline_out = var

    @property
    def timeline_filter(self):
        return self.__timeline_filter

    @timeline_filter.setter
    def timeline_filter(self, var):
        self.__timeline_filter = var

    @property
    def mode(self):
        return self.__mode

    @mode.setter
    def mode(self, var):
        self.__mode = var

    @property
    def gapsize(self):
        return self.__gapsize

    @gapsize.setter
    def gapsize(self, var):
        self.__gapsize = var

    @property
    def color_to_skip(self):
        return self.__color_to_skip

    @color_to_skip.setter
    def color_to_skip(self, var):
        self.__color_to_skip = var

    def merge(self):
        rpmanager = RPManager()
        # query all timelines that match the given filters
        all_timelines = rpmanager.get_all_timelines(filter=True)

        # build dict with source mediapool item: clip item
        # ! make sure clip_map has no duplicate keys
        clip_map = {}
        for tl in all_timelines:
            for tl_clip in tl.GetClips():
                src_clip = tl_clip.GetSource()  # maybe .GetMediaPoolItem()
                if not clip_map.get(src_clip):
                    clip_map.update({src_clip: [tl_clip]})
                else:
                    clip_map[src_clip].append(tl_clip)

        # ? do i need to sort the tl_clips by cut in

        # apply algo... get lower cut in and highest cut out
        #               keep gap_size in mind
        result = {}  # src_clip: (cut_in, cut_out)
        for src_clip, tl_clips in clip_map.items():
            result[src_clip] = None
            _in, _out, curr_gap = sys.maxsize, 0, None
            for c in tl_clips:
                if c.cut_in < _in:
                    _in = c.cut_in
                else:
                    curr_gap = c.cut_in - _out
                    if curr_gap > self.gapsize:
                        pass  # ! split clip, effectively getting a new one
                if c.cut_out > _out:
                    _out = c.cut_out
            result[src_clip] = (_in, _out)

        # create new timeline
        # append all clips in their best length to timeline
        try:
            print(self.mode)
        except Exception as err:
            print(err)


class UI:
    def __init__(self, fu) -> None:
        self.fu = fu
        self.merger = Merger(fu)
        self.ui_manager = self.fu.UIManager
        self.ui_dispatcher = bmd.UIDispatcher(self.ui_manager)

        # self.load_config()
        self.create_ui()
        self.init_ui_defaults()
        self.init_ui_callbacks()

    def create_ui(self):
        self.selection_group = self.ui_manager.HGroup(
            {"Spacing": 5, "Weight": 0},
            [
                self.ui_manager.VGroup(
                    {"Spacing": 5, "Weight": 1},
                    [
                        self.ui_manager.Label(
                            {
                                "StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"
                            }
                        ),
                        self.ui_manager.HGroup(
                            {"Spacing": 5, "Weight": 0},
                            [
                                self.ui_manager.Label(
                                    {
                                        "Text": "Timeline Filter:",
                                        "Alignment": {"AlignLeft": True},
                                        "Weight": 0.1,
                                    }
                                ),
                                self.ui_manager.LineEdit(
                                    {
                                        "ID": "include_only",
                                        "Text": "",
                                        "Weight": 0.5,
                                    }
                                ),
                            ],
                        ),
                        self.ui_manager.HGroup(
                            {"Spacing": 5, "Weight": 0},
                            [
                                self.ui_manager.Label(
                                    {
                                        "Text": "Pick Master Timeline:",
                                        "Alignment": {"AlignLeft": True},
                                        "Weight": 0.1,
                                    }
                                ),
                                self.ui_manager.ComboBox(
                                    {
                                        "ID": "timelines",
                                        "Alignment": {"AlignLeft": True},
                                        "Weight": 0.5,
                                    }
                                ),
                            ],
                        ),
                        self.ui_manager.HGroup(
                            {"Spacing": 5, "Weight": 0},
                            [
                                self.ui_manager.Label(
                                    {
                                        "Text": "Merged Timeline Name:",
                                        "Alignment": {"AlignLeft": True},
                                        "Weight": 0.1,
                                    }
                                ),
                                self.ui_manager.LineEdit(
                                    {
                                        "ID": "merged_tl_name",
                                        "Text": "merged",
                                        "Weight": 0.5,
                                    }
                                ),
                            ],
                        ),
                        self.ui_manager.HGroup(
                            {"Spacing": 5, "Weight": 0},
                            [
                                self.ui_manager.CheckBox(
                                    {
                                        "ID": "skip_clip_color",
                                        "Text": "Skip Clip Color:",
                                        "Checked": False,
                                        "AutoExclusive": True,
                                        "Checkable": True,
                                        "Events": {"Toggled": True},
                                    }
                                ),
                                self.ui_manager.ComboBox(
                                    {
                                        "ID": "clip_colors",
                                        "Weight": 0.8,
                                    }
                                ),
                            ],
                        ),
                        self.ui_manager.Label(
                            {
                                "StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"
                            }
                        ),
                        self.ui_manager.HGroup(
                            {"Spacing": 5, "Weight": 0},
                            [
                                self.ui_manager.Label(
                                    {"Text": "Merge Gap:", "Weight": 0}
                                ),
                                self.ui_manager.SpinBox(
                                    {
                                        "ID": "merge_gap",
                                        "Value": 10,
                                        "Minimum": 0,
                                        "Maximum": 100000,
                                        "SingleStep": 1,
                                    }
                                ),
                            ],
                        ),
                        self.ui_manager.HGroup(
                            {"Spacing": 5, "Weight": 0},
                            [
                                self.ui_manager.Label(
                                    {
                                        "Text": "Merge By:",
                                        "Alignment": {"AlignLeft": True},
                                        "Weight": 0.1,
                                    }
                                ),
                                self.ui_manager.ComboBox(
                                    {
                                        "ID": "merge_key",
                                        "Alignment": {"AlignLeft": True},
                                        "Weight": 0.5,
                                    }
                                ),
                            ],
                        ),
                        self.ui_manager.Label(
                            {
                                "StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"
                            }
                        ),
                    ],
                )
            ],
        )
        self.window_01 = self.ui_manager.VGroup(
            [
                self.ui_manager.HGroup(
                    {"Spacing": 1},
                    [
                        self.ui_manager.VGroup(
                            {"Spacing": 15, "Weight": 3},
                            [
                                self.selection_group,
                                self.ui_manager.Button(
                                    {
                                        "ID": "merge_button",
                                        "Text": "Merge",
                                        "Weight": 0,
                                        "Enabled": True,
                                    }
                                ),
                                self.ui_manager.Label(
                                    {
                                        "ID": "status",
                                        "Text": "",
                                        "Alignment": {"AlignCenter": True},
                                    }
                                ),
                                self.ui_manager.Label(
                                    {"StyleSheet": "max-height: 5px;"}
                                ),
                            ],
                        ),
                    ],
                )
            ]
        )
        self.main_window = self.ui_dispatcher.AddWindow(
            {
                "WindowTitle": "Merge Timelines",
                "ID": "ui.main",
                "Geometry": [
                    800,
                    500,  # position when starting
                    450,
                    275,  # width, height
                ],
            },
            self.window_01,
        )

    def init_ui_defaults(self):
        items = self.main_window.GetItems()
        items["clip_colors"].AddItems(clipcolor_names)
        items["merge_key"].AddItems(merge_names)

    def init_ui_callbacks(self):
        self.main_window.On["ui.main"].Close = self.destroy
        self.main_window.On["merge_button"].Clicked = self.merge
        self.main_window.On["include_only"].TextChanged = self.update

    @property
    # ? should we really call the filter include_only
    # ? should we combine timeline and color filter into 1 object
    def filter(self) -> str:
        return str(self.main_window.Find("include_only").Text)

    @property
    def color_to_skip(self) -> str:
        return str(self.main_window.Find("clip_colors").CurrentText)

    @property
    def timeline_in(self) -> str:
        return str(self.main_window.Find("timelines").CurrentText)

    @property
    #! might require getter
    def timeline_out(self) -> str:
        return str(self.main_window.Find("merged_tl_name").Text)

    @property
    def merge_gap(self) -> int:
        return int(self.main_window.Find("merge_gap").Value)

    @property
    def merge_mode(self) -> str:
        return str(self.main_window.Find("merge_key").CurrentText)

    def start(self):
        self.main_window.Show()
        self.ui_dispatcher.RunLoop()
        self.main_window.Hide()

    def destroy(self, event=None):
        self.ui_dispatcher.ExitLoop()
        if event:
            print(event)

    def merge(self, event=None):
        if event:
            print(event)

        # prepare timeline merger
        self.merger.timeline_in = self.timeline_in
        self.merger.timeline_out = self.timeline_out
        self.merger.timeline_filter = self.filter
        self.merger.color_to_skip = self.color_to_skip
        self.merger.mode = self.merge_mode
        self.merger.gapsize = self.merge_gap

        # do the merge
        self.merger.merge()

    def update(self, event=None):
        if event:
            print(event)


app = UI(bmd.scriptapp("Fusion"))
app.start()
