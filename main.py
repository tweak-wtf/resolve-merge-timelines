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


class Merger:
    def __init__(self, fu) -> None:
        self.fu = fu


class UI:
    def __init__(self, fu) -> None:
        self.fu = fu
        self.renamer = Merger(fu)
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
        pass

    def init_ui_callbacks(self):
        self.main_window.On["ui.main"].Close = self.destroy
        # self.main_window.On["Run"].Clicked = self.run
        self.main_window.On["merge_button"].Clicked = self.merge
        self.main_window.On["include_only"].TextChanged = self.update

    def start(self):
        self.main_window.Show()
        self.ui_dispatcher.RunLoop()
        self.main_window.Hide()

    def destroy(self, event=None):
        self.ui_dispatcher.ExitLoop()
        if event:
            print(event)

    def run(self):
        pass

    def merge(self):
        pass

    def update(self):
        pass


app = UI(bmd.scriptapp("Fusion"))
app.start()
