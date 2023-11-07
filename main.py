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


class SMPTE(object):
    """Frames to SMPTE timecode converter and reverse."""

    # ! everything in here should be classmethods,vars since we don't need to instantiate an object ever

    def __init__(self):
        self.__fps = 24.0
        self.__is_dropframe = False

    @property
    def fps(self) -> float:
        return self.__fps

    @fps.setter
    def fps(self, val):
        val = float(val)
        self.__fps = val

    @property
    def is_dropframe(self) -> float:
        return self.__is_dropframe

    @is_dropframe.setter
    def is_dropframe(self, val):
        val = float(val)
        self.__is_dropframe = val

    def get_frames(self, tc: str) -> int:
        """Converts SMPTE timecode to frame count."""

        if not tc or tc == "":
            return None

        if int(tc[9:]) > self.fps:
            raise ValueError("SMPTE timecode to frame rate mismatch.", tc, self.fps)

        hours = int(tc[:2])
        minutes = int(tc[3:5])
        seconds = int(tc[6:8])
        frames = int(tc[9:])

        totalMinutes = int(60 * hours + minutes)

        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.is_dropframe:
            dropFrames = int(round(self.fps * 0.066666))
            timeBase = int(round(self.fps))
            hourFrames = int(timeBase * 60 * 60)
            minuteFrames = int(timeBase * 60)
            frm = int(
                (
                    (hourFrames * hours)
                    + (minuteFrames * minutes)
                    + (timeBase * seconds)
                    + frames
                )
                - (dropFrames * (totalMinutes - (totalMinutes // 10)))
            )
        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            frm = int((totalMinutes * 60 + seconds) * self.fps + frames)

        return frm

    def get_tc(self, frames: int) -> str:
        """Converts frame count to SMPTE timecode."""

        frames = abs(frames)

        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.is_dropframe:
            spacer = ":"
            spacer2 = ";"

            dropFrames = int(round(self.fps * 0.066666))
            framesPerHour = int(round(self.fps * 3600))
            framesPer24Hours = framesPerHour * 24
            framesPer10Minutes = int(round(self.fps * 600))
            framesPerMinute = int(round(self.fps) * 60 - dropFrames)

            frames = frames % framesPer24Hours

            d = frames // framesPer10Minutes
            m = frames % framesPer10Minutes

            if m > dropFrames:
                frames = (
                    frames
                    + (dropFrames * 9 * d)
                    + dropFrames * ((m - dropFrames) // framesPerMinute)
                )
            else:
                frames = frames + dropFrames * 9 * d

            frRound = int(round(self.fps))
            hr = int(frames // frRound // 60 // 60)
            mn = int((frames // frRound // 60) % 60)
            sc = int((frames // frRound) % 60)
            fr = int(frames % frRound)

        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            spacer = ":"
            spacer2 = spacer

            frHour = self.fps * 3600
            frMin = self.fps * 60

            hr = int(frames // frHour)
            mn = int((frames - hr * frHour) // frMin)
            sc = int((frames - hr * frHour - mn * frMin) // self.fps)
            fr = int(round(frames - hr * frHour - mn * frMin - sc * self.fps))

        # Return SMPTE timecode string.
        return (
            str(hr).zfill(2)
            + spacer
            + str(mn).zfill(2)
            + spacer
            + str(sc).zfill(2)
            + spacer2
            + str(fr).zfill(2)
        )


class DVR_ProjectManager:
    def __init__(self) -> None:
        self.__manager = bmd.scriptapp("Resolve").GetProjectManager()
        self.__current_project = self.manager.GetCurrentProject()
        self.__mediapool = self.current_project.GetMediaPool()

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

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name}@{self.id}"

    @property
    def id(self) -> str:
        return self.__dvr_obj.GetUniqueId()

    @property
    def name(self):
        return self.__dvr_obj.GetName()

    @property
    def clip_properties(self):
        return self.__dvr_obj.GetClipProperty()

    @property
    def properties(self):
        result = self.__dvr_obj.GetMetadata()
        result.update(self.__dvr_obj.GetClipProperty())
        return dict(sorted(result.items()))

    @property
    def pls_work(self):
        return self.__dvr_obj


class DVR_Clip:
    def __init__(self, dvr_obj) -> None:
        self.__dvr_obj = dvr_obj
        self.__used_timeline: DVR_Timeline
        self.smpte = SMPTE()
        self.smpte.fps = float(self.source.properties.get("Camera FPS"))

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"{self.name}@{self.src_in}"

    @property
    def id(self):
        return self.__dvr_obj.GetUniqueId()

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
    def edit_in(self) -> int:
        return self.__dvr_obj.GetStart()

    @property
    def edit_out(self) -> int:
        return self.__dvr_obj.GetEnd()

    @property
    def head_in(self) -> int:
        return self.smpte.get_frames(str(self.source.properties.get("Start TC")))

    @property
    def tail_out(self) -> int:
        return self.smpte.get_frames(str(self.source.properties.get("End TC")))

    @property
    def left_offset(self) -> int:
        return int(self.__dvr_obj.GetLeftOffset())

    @property
    def right_offset(self) -> int:
        return int(self.__dvr_obj.GetRightOffset())

    @property
    def src_in(self) -> int:
        return self.head_in + self.left_offset

    @property
    def src_out(self) -> int:
        # log.debug(f"{self.duration = }")
        # log.debug(f"{self.src_in = }")
        # ? why doesn't this here work: self.tail_out - self.right_offset
        return self.src_in + self.duration

    @property
    def duration(self):
        return self.__dvr_obj.GetDuration()

    @property
    def color(self):
        return self.__dvr_obj.GetClipColor()

    @property
    def properties(self):
        return dict(self.__dvr_obj.GetProperty())


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
        return bool(result)

    @property
    def video_tracks(self) -> list[str]:
        result = []
        for i in range(0, self.__dvr_obj.GetTrackCount("video")):
            result.append(self.__dvr_obj.GetTrackName("video", i + 1))
        return result

    @property
    def markers(self):
        return self.__dvr_obj.GetMarkers()

    @property
    def clips(self) -> list[DVR_Clip]:
        result = []
        log.debug(f"{self.video_tracks = }")
        # TODO: exclude video_tracks as filter
        for i in range(len(self.video_tracks)):
            for c in self.__dvr_obj.GetItemListInTrack("video", i + 1):
                clip = DVR_Clip(c)
                clip.used_in_timeline = self
                result.append(clip)
        return result


# class DVR_MediaPoolItem:
#     def __init__(self) -> None:
#         pass

#     @property
#     # ! yo this might be in source.properties["clip"]["Usage"]
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
        smpte = SMPTE()
        smpte.fps = 25
        # query all timelines that match the given filters
        # TODO: implement regex include and exclude
        all_timelines = [
            tl for tl in pmanager.all_timelines if self.timeline_filter in tl.name
        ]

        # TODO: make sure occs has no duplicate values
        # build dict with source mediapool item: clip item
        log.info("================================================")
        occs = {}  # occurrences per mediapoolitem
        for tl in all_timelines:
            log.debug("------------------------------------------------")
            log.debug(f"analyzing timeline: {tl.name}")
            for tl_clip in tl.clips:
                src_clip = tl_clip.source
                # never seen this MPI before... add it
                if not src_clip.id in occs.keys():
                    occs.update(
                        {
                            src_clip.id: {
                                "source": src_clip,
                                "usages": {
                                    tl_clip.id: {
                                        "clip": tl_clip,
                                        "usage": (tl_clip.src_in, tl_clip.src_out),
                                    }
                                },
                            }
                        }
                    )
                else:
                    occs[src_clip.id]["usages"].update(
                        {
                            tl_clip.id: {
                                "clip": tl_clip,
                                "usage": (tl_clip.src_in, tl_clip.src_out),
                            }
                        }
                    )

        # sort occurrences and remove duplicates
        clip_map = {}
        for src_id, src_v in occs.items():
            clip_set = set([u["usage"] for u in src_v["usages"].values()])
            clip_map[src_id] = sorted(clip_set, key=lambda k: k[0])
        log.info(f"{occs = }")
        log.info(f"{clip_map = }")

        # {'74c773df-4b70-41e0-a0a4-c2f0e25f0414': [(1755093, 1755137), (1755237, 1755394)]}
        foo = [
            (1755093, 1755113),
            (1755244, 1755344),
            (1755293, 1755318),
            (1755416, 1755436),
        ]
        bar = (
            {
                "mediaPoolItem": "foo",
                "startFrame": 1755093,
                "endFrame": 1755113,
                "mediaType": 1,
                "trackIndex": 1,
            },
            {
                "mediaPoolItem": "foo",
                "startFrame": 1755293,
                "endFrame": 1755318,
                "mediaType": 1,
                "trackIndex": 1,
            },
            {
                "mediaPoolItem": "foo",
                "startFrame": 1755416,
                "endFrame": 1755436,
                "mediaType": 1,
                "trackIndex": 1,
            },
        )
        blis = {k: list() for k in clip_map.keys()}
        log.debug(f"initialized blis: {blis}")
        for src, clips in clip_map.items():
            start, end = clips[0][0], clips[0][1]
            for i in range(1, len(clips)):
                this_occ = clips[i]
                last_occ = clips[i - 1]
                curr_diff = this_occ[0] - last_occ[1]
                if curr_diff > self.gapsize:
                    # shall create new plate
                    log.debug(f"found new plate...")
                    log.debug(f"{curr_diff = }")
                    blis[src].append(
                        {
                            "mediaPoolItem": occs[src]["source"].pls_work,
                            "startFrame": last_occ[0],
                            "endFrame": last_occ[1],
                            "mediaType": 1,
                            "trackIndex": 1,
                        }
                    )
                    # update start
                    log.debug(f"> GAPSIZE resetting to: {this_occ}")
                    start, end = this_occ[0], this_occ[1]
                    continue
                else:
                    # update end
                    end = this_occ[1] if this_occ[1] > end else end
                    log.debug(f"< GAPSIZE current bli {start} - {end}")
            blis[src].append(
                {
                    "mediaPoolItem": occs[src]["source"].pls_work,
                    "startFrame": start,
                    "endFrame": end,
                    "mediaType": 1,
                    "trackIndex": 1,
                }
            )
            # got 1 element if no weird shit hap[penning]
        log.debug(f"{blis = }")

        results = []
        for bli in blis.values():
            for b in bli:
                results.append(b)
        # results = [zip(i) for i in blis.values()]
        log.debug(f"{results = }")

        # create timeline
        pmanager.mediapool.CreateEmptyTimeline("lel2")
        pmanager.mediapool.AppendToTimeline(results)

        return

        _occs = {}
        for src_id, src_v in occs.items():
            src_v["usages"] = dict(sorted())
            for clip_id, clip_v in src_v["usages"].items():
                pass
            s_occs = sorted(v, key=lambda clip: clip.src_in)
            _occs.update({k: s_occs})
        log.info(f"{_occs = }")
        log.info(len(occs))

        # ? do i need to sort the tl_clips by cut in
        # --> yeah i think so, but by src_in
        log.info("================================================")

        for src_id, occs in occs.items():
            bli = []
            _in, _out = sys.maxsize, 0
            for i in range(1, len(occs)):
                this_occ = occs[i]
                last_occ = occs[i - 1]
                curr_diff = this_occ.src_in - last_occ.src_out
                if curr_diff > self.gapsize:
                    log.debug(f"{curr_diff = }")
                else:
                    log.debug(f"{curr_diff = }")

        log.info("================================================")

        # apply algo... get lower cut in and highest cut out
        #               keep gap_size in mind
        result = {}  # src_clip: [(edit_in, edit_out)]
        for src_id, tl_clips in occs.items():
            result[src_id] = []
            _in, _out, curr_gap = sys.maxsize, 0, None
            for c in tl_clips:
                if c.src_in < _in:
                    _in = c.src_in
                else:
                    #! oh oh... gotta do the same for right side
                    curr_gap = c.src_in - _out
                    log.debug(f"{curr_gap = }")
                    if curr_gap > self.gapsize:
                        log.debug("FOUND weirdo clip... splitting...")
                        if not (c.src_in, c.src_out) in result[src_id]:
                            log.debug("adding weirdo to list")
                            result[src_id].append(
                                (c.src_in, c.src_out)
                            )  # ! splits clip, effectively getting a new one
                            continue
                if c.src_out > _out:
                    _out = c.src_out
            # TODO: check if previous src_ins are within gapsize
            # ?how tf
            result[src_id].append((_in, _out))
            log.debug(result[src_id])

        # result = {}  # src_id: [(edit_in, edit_out)]
        log.debug(result)
        for src, occs in result.items():
            log.info(src)
            ins = [o[0] for o in occs]
            outs = [o[1] for o in occs]

            log.debug(f"{ins = }")
            log.debug(f"{outs = }")

        bestlength_items = []
        for k, v in result.items():
            for i in v:
                bestlength_items.append(
                    {
                        "mediaPoolItem": k.pls_work,
                        "startFrame": i[0],
                        "endFrame": i[1],
                        "mediaType": 1,
                        "trackIndex": 1,
                    }
                )
                log.info(f"{k}: {smpte.get_tc(i[0])} - {smpte.get_tc(i[1])}")
                log.info(f"{k}: {i}")
        log.debug(bestlength_items)
        log.debug(len(bestlength_items))

        # # ! goofy loop again lol
        # for

        # bestLengthItems.append(
        #                 {
        #                     'mediaPoolItem': mediaPoolItem,
        #                     'startFrame': startFrame,
        #                     'endFrame': endFrame,
        #                     'mediaType': 1,
        #                     'trackIndex': 1,
        #                 })

        # create new timeline
        # append all clips in their best length to timeline
        pmanager.mediapool.CreateEmptyTimeline("lel2")
        pmanager.mediapool.AppendToTimeline(bestlength_items)
        log.debug("YAYA?!")
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

        try:
            # prepare timeline merger
            self.merger.timeline_in = self.timeline_in
            self.merger.timeline_out = self.timeline_out
            self.merger.timeline_filter = self.filter
            self.merger.color_to_skip = self.color_to_skip
            self.merger.mode = self.merge_mode
            self.merger.gapsize = self.merge_gap

            # do the merge
            self.merger.merge()
        except Exception as err:
            log.exception(err, stack_info=True)

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
