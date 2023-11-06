import sys
import logging
from pathlib import Path

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


class DVR_ProjectManager:
    def __init__(self) -> None:
        self.__manager = bmd.scriptapp("Resolve").GetProjectManager()
        self.__current_project = self.manager.GetCurrentProject()
        self.__mediapool = self.current_project.GetMediaPool()
        log.debug(self.manager)

    @property
    def manager(self):
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
    def mediapool(self):
        return self.__mediapool

    @property
    def all_timelines(self):
        # ! resolve saves Timelines with 1-based indices
        result = []
        for i in range(1, self.current_project.GetTimelineCount() + 1):
            dvrtl = self.current_project.GetTimelineByIndex(i)
            result.append(DVR_Timeline(dvrtl))

        return result


class DVR_SourceClip:
    def __init__(self, dvr_obj) -> None:
        self.__dvr_obj = dvr_obj

    @property
    def name(self):
        return self.__dvr_obj.GetName()


class DVR_Clip:
    def __init__(self, dvr_obj) -> None:
        self.__dvr_obj = dvr_obj
        self.__used_timeline: DVR_Timeline

    def __str__(self) -> str:
        return self.name

    @property
    def name(self):
        return self.__dvr_obj.GetName()

    @property
    def source(self):
        return DVR_SourceClip(self.__dvr_obj.GetMediaPoolItem())

    @property
    def used_in_timeline(self):
        return self.__used_timeline

    @used_in_timeline.setter
    def used_in_timeline(self, val):
        self.__used_timeline = val

    @property
    def edit_in(self):
        return self.__dvr_obj.GetStart()

    @property
    def edit_out(self):
        return self.__dvr_obj.GetEnd()

    @property
    def head_in(self):
        return self.__dvr_obj.GetLeftOffset()

    @property
    def tail_out(self):
        return self.__dvr_obj.GetRightOffset()

    @property
    def duration(self):
        return self.__dvr_obj.GetDuration()

    @property
    def color(self):
        return self.__dvr_obj.GetClipColor()


class DVR_Timeline:
    def __init__(self, dvr_obj) -> None:
        self.__dvr_obj = dvr_obj

    def __str__(self) -> str:
        return self.name

    @property
    def start_frame(self) -> int:
        return int(self.__dvr_obj.GetStartFrame())

    @property
    def end_frame(self) -> int:
        return int(self.__dvr_obj.GetEndFrame())

    @property
    def name(self):
        return str(self.__dvr_obj.GetName())

    @property
    def framerate(self) -> float:
        return float(self.__dvr_obj.GetSetting("timelineFrameRate"))

    @property
    def is_drop_frame(self):
        result = self.__dvr_obj.GetSetting("timelineDropFrameTimecode")
        log.debug(result)
        return bool(result)

    @property
    def video_tracks(self) -> list[str]:
        result = []
        for i in range(1, self.__dvr_obj.GetTrackCount("video")):
            result.append(self.__dvr_obj.GetTrackName("video", i))
        return result

    @property
    def markers(self):
        return self.__dvr_obj.GetMarkers()

    @property
    def clips(self):
        result = []
        # TODO: exclude video_tracks as filter
        log.debug(f"{self.video_tracks = }")
        for vt in self.video_tracks:
            log.debug(f"{vt = }")
            for c in self.__dvr_obj.GetItemListInTrack("video", 1):
                log.debug(f"{c = }")
                clip = DVR_Clip(c)
                clip.used_in_timeline = self
                result.append(clip)
        return result


# class DVR_MediaPoolItem:
#     def __init__(self) -> None:
#         pass

#     @property
#     def occurrences(self):
#         result = []
#         for tl in timelines:
#             if self in timeline:
#                 result.append(self)
#         return result


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
        pmanager = DVR_ProjectManager()

        # query all timelines that match the given filters
        # TODO: implement regex include and exclude
        all_timelines = [
            tl for tl in pmanager.all_timelines if self.timeline_filter in tl.name
        ]

        [log.debug(t) for t in all_timelines]
        # build dict with source mediapool item: clip item
        # ! make sure clip_map has no duplicate keys
        clip_map = {}
        try:
            for tl in all_timelines:
                for tl_clip in tl.clips:
                    src_clip = tl_clip.source.name  # maybe .GetMediaPoolItem()
                    if not clip_map.get(src_clip):
                        clip_map.update({src_clip: [tl_clip]})
                    else:
                        clip_map[src_clip].append(tl_clip)
            log.info(clip_map)
        except Exception as err:
            log.exception(err, stack_info=True)

        # ? do i need to sort the tl_clips by cut in

        # apply algo... get lower cut in and highest cut out
        #               keep gap_size in mind
        result = {}  # src_clip: (cut_in, cut_out)
        for src_clip, tl_clips in clip_map.items():
            result[src_clip] = None
            _in, _out, curr_gap = sys.maxsize, 0, None
            for c in tl_clips:
                if c.edit_in < _in:
                    _in = c.edit_in
                else:
                    curr_gap = c.edit_in - _out
                    if curr_gap > self.gapsize:
                        pass  # ! split clip, effectively getting a new one
                if c.edit_out > _out:
                    _out = c.edit_out
            result[src_clip] = (_in, _out)
        log.debug(result)
        return

        # create new timeline
        # append all clips in their best length to timeline
        try:
            log.debug(self.mode)
        except Exception as err:
            log.debug(err)


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
            log.debug(event)

    def merge(self, event=None):
        if event:
            log.debug(event)

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
            log.debug(event)


# logging.basicConfig(
#     format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
#     datefmt="%Y-%m-%d:%H:%M:%S",
#     level=logging.DEBUG,
# )

log = logging.getLogger(__name__)
formatter = logging.Formatter(
    "%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s"
)
errhandler = logging.StreamHandler(sys.stderr)
errhandler.setLevel(logging.ERROR)
errhandler.setFormatter(formatter)
log.addHandler(errhandler)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
log.addHandler(handler)

filehandler = logging.FileHandler(
    str(
        Path(
            r"C:\Users\tony.dorfmeister\AppData\Roaming\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Comp\resolve-merge-timelines\log.log"
        )
    )
)
filehandler.setLevel(logging.DEBUG)
filehandler.setFormatter(formatter)
log.addHandler(filehandler)

log.setLevel(logging.DEBUG)


app = UI(bmd.scriptapp("Fusion"))
app.start()
