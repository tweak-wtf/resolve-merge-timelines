# -*- coding:utf-8 -*-
# fmt: off
# Author: Jiri Sindelar

# Thanks to Zhang Laichi for numerous code pieces
# https://github.com/laciechang/resolve_batch_io_point/tree/main

# Thanks to Igor Ridanovic for providing the timecode conversion method
# https://github.com/IgorRidanovic/smpte

from operator import index
import pprint
import logging
import sys

fu = bmd.scriptapp('Fusion')
ui = fu.UIManager
disp = bmd.UIDispatcher(ui)
resolve = bmd.scriptapp('Resolve')

clipcolor_names = [
    'Orange',
    'Apricot',
    'Yellow',
    'Lime',
    'Olive',
    'Green',
    'Teal',
    'Navy',
    'Blue',
    'Purple',
    'Violet',
    'Pink',
    'Tan',
    'Beige',
    'Brown',
    'Chocolate'
]

merge_names = [
    'Reel Name',
    'Source File'
]


class SMPTE(object):
    '''Frames to SMPTE timecode converter and reverse.'''
    def __init__(self):
        self.fps = 24.0
        self.df  = False

    def get_frames(self, tc):
        '''Converts SMPTE timecode to frame count.'''

        if not tc or tc == '':
            return None
        
        if int(tc[9:]) > self.fps:
            raise ValueError('SMPTE timecode to frame rate mismatch.', tc, self.fps)

        hours   = int(tc[:2])
        minutes = int(tc[3:5])
        seconds = int(tc[6:8])
        frames  = int(tc[9:])

        totalMinutes = int(60 * hours + minutes)
        
        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.df:
            dropFrames = int(round(self.fps * 0.066666))
            timeBase   = int(round(self.fps))
            hourFrames   = int(timeBase * 60 * 60)
            minuteFrames = int(timeBase * 60)
            frm = int(((hourFrames * hours) + (minuteFrames * minutes) + (timeBase * seconds) + frames) - (dropFrames * (totalMinutes - (totalMinutes // 10))))
        # Non drop frame calculation.
        else:
            self.fps = int(round(self.fps))
            frm = int((totalMinutes * 60 + seconds) * self.fps + frames)

        return frm

    def get_tc(self, frames):
        '''Converts frame count to SMPTE timecode.'''

        frames = abs(frames)

        # Drop frame calculation using the Duncan/Heidelberger method.
        if self.df:

            spacer = ':'
            spacer2 = ';'

            dropFrames         = int(round(self.fps * .066666))
            framesPerHour      = int(round(self.fps * 3600))
            framesPer24Hours   = framesPerHour * 24
            framesPer10Minutes = int(round(self.fps * 600))
            framesPerMinute    = int(round(self.fps) * 60 - dropFrames)

            frames = frames % framesPer24Hours

            d = frames // framesPer10Minutes
            m = frames % framesPer10Minutes

            if m > dropFrames:
                frames = frames + (dropFrames * 9 * d) + dropFrames * ((m - dropFrames) // framesPerMinute)
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
            spacer  = ':'
            spacer2 = spacer

            frHour = self.fps * 3600
            frMin  = self.fps * 60

            hr = int(frames // frHour)
            mn = int((frames - hr * frHour) // frMin)
            sc = int((frames - hr * frHour - mn * frMin) // self.fps)
            fr = int(round(frames -  hr * frHour - mn * frMin - sc * self.fps))

        # Return SMPTE timecode string.
        return(
                str(hr).zfill(2) + spacer +
                str(mn).zfill(2) + spacer +
                str(sc).zfill(2) + spacer2 +
                str(fr).zfill(2)
                )


class ResolveProject:
    def __init__(self) -> None:
        self.project_manager = resolve.GetProjectManager()
        self.current_project = self.project_manager.GetCurrentProject()
        self.project_name = self.current_project.GetName()

        # list of timelines in the project
        self.all_timelines = []

        # filtered timeline names
        self.selected_tl_names = []
        self.selected_timelines = []

        # list of all plates that are in filtered timelines
        self.plates = []

        # plates grouped by key
        # keys are reel id's or source files
        self.plate_groups = {}

        # reel : long name <- included long names
        self.merge_summary = {}

        self.fps_mapping = {
        '16': 16.0,     '18': 18.0,
        '23': 23.976,   '24': 24.0,
        '24.0': 24.0,
        '25.0': 25.0,     '29': 29.97,
        '30': 30.0,     '30.0': 30.0,
        '47': 47.952,
        '48': 48.0,     '50': 50.0,
        '59': 59.94,    '60': 60.0,
        '72': 72.0,     '95': 95.904,
        '96': 96.0,     '100': 100.0,
        '119': 119.88,  '120': 120.0
        }
        self.smpte = SMPTE()

    def current_timeline(self):
        return self.project_manager.GetCurrentProject().GetCurrentTimeline()

    def get_all_timelines_in_current_project(self):

        all_tl = []
        for i in range(1, self.current_project.GetTimelineCount()+1):
            tl = self.current_project.GetTimelineByIndex(i)
            tl_info = {
                    'item': tl,
                    'name': str(tl.GetName()),
                    'fps': str(tl.GetSetting('timelineFrameRate')),
                    'drop': bool(int(tl.GetSetting('timelineDropFrameTimecode'))),
                    'in': int(tl.GetStartFrame()),
                    'out': int(tl.GetEndFrame()),
                    'v_tracks': int(tl.GetTrackCount('video')),
                    'markers': tl.GetMarkers(),
                    'to_merge' : False
                }
            all_tl.append(tl_info)
            self.all_timelines = sorted(all_tl, key=lambda k: (k['name'], k['in']))
        return self.all_timelines
    
    def filter_timelines(self, include=''):

        self.get_all_timelines_in_current_project()
        tl_to_merge = []
        if self.all_timelines:
            for one in self.all_timelines:
                if (str(include) in str(one['name'])) or include == '':
                    one['to_merge'] = True
                    tl_to_merge.append(one['name'])
                else:
                    one['to_merge'] = False
        self.selected_tl_names = sorted(tl_to_merge)
        return self.selected_tl_names
    
    def get_plates(self, skip_color='Orange'):

        plate_list = []
        for one_tl in self.all_timelines:
            if not one_tl['to_merge']:
                continue
            self.smpte.fps = int(self.fps_mapping[one_tl['fps']])
            self.smpte.df = one_tl['drop']
            for trck in range(1, one_tl['v_tracks'] + 1):
                trck_name = one_tl['item'].GetTrackName('video', trck)
                print(f"{trck_name = }")
                trck_items = one_tl['item'].GetItemListInTrack('video', trck)
                for itm in trck_items:
                    pool_item = itm.GetMediaPoolItem()
                    clip_color = itm.GetClipColor()
                    ignore = False
                    if skip_color:
                        if skip_color == clip_color:
                            ignore = True
                    if not ignore:
                        clip_info = {
                            'timeline': one_tl['item'],
                            'timeline_name': one_tl['name'],
                            'item': itm,
                            'pool_item': pool_item,
                            'track_number': trck,
                            'track_name': trck_name,
                            'track_index': str(trck_items.index(itm)).zfill(4),
                            'name': itm.GetName(),
                            'color': clip_color,
                            'in': itm.GetStart(),
                            'out': itm.GetEnd(),
                            'head': itm.GetLeftOffset(),
                            'tail': itm.GetRightOffset(),
                            'duration': itm.GetDuration(),
                            'pool_name': pool_item.GetClipProperty('Clip Name') if pool_item is not None else None,
                            'pool_file_name': pool_item.GetClipProperty('File Name') if pool_item is not None else None,
                            'pool_reel': pool_item.GetClipProperty('Reel Name') if pool_item is not None else None,
                            'start_tc': pool_item.GetClipProperty('Start TC') if pool_item is not None else None,
                            'end_tc': pool_item.GetClipProperty('End TC') if pool_item is not None else None,
                            'merge_children': [],
                            'merge_children_names': [],
                            'merge_parent': None,
                            'merge_out':0
                        }

                        clip_info['long_name'] = '-'.join([clip_info['timeline_name'], str(clip_info['track_number']), clip_info['track_index'], clip_info['name']])
                        clip_info['start_tc_num'] = self.smpte.get_frames(clip_info['start_tc'])
                        clip_info['end_tc_num'] = self.smpte.get_frames(clip_info['end_tc'])
                        plate_list.append(clip_info)
        self.plates = plate_list

    def split_plates_by_reel(self, key='pool_reel'):

        # group plates by reel
        plate_grps = {}
        if self.plates and len(self.plates) > 0:
            for one in self.plates:
                if one[key] not in plate_grps.keys():
                    plate_grps[one[key]] = [one]
                else:
                    plate_grps[one[key]].append(one)
        # sort plate groups by in point
        for k, v in plate_grps.items():
            plate_grps[k] = sorted(v, key=lambda kk: (kk['in'], kk['duration']))

        self.plate_groups = plate_grps

    def merge_plates(self, max_gap=10):

        self.merge_summary = {}
        if self.plate_groups and len(self.plate_groups) > 0:
            for k, v in self.plate_groups.items():
                merge_index = 0
                for plate in v:
                    group_index = v.index(plate)
                    if group_index == 0:
                        plate['merge_children'] = []
                        plate['merge_parent'] = None
                        plate['merge_out'] =  plate['out']
                        merge_index = group_index
                        continue

                    if plate['in'] - max_gap <= v[merge_index]['merge_out']:
                        # to be merged
                        v[merge_index]['merge_children'].append(group_index)
                        v[merge_index]['merge_children_names'].append(plate['long_name'])
                        plate['merge_parent'] = merge_index
                        if plate['out'] > v[merge_index]['merge_out']:
                            v[merge_index]['merge_out'] = plate['out']
                    else:
                        # not merged, new parent
                        plate['merge_parent'] = None
                        plate['merge_out'] =  plate['out']
                        merge_index = group_index

            # sum up plates that are "included"
            for k, v in self.plate_groups.items():
                if k not in self.merge_summary.keys():
                    self.merge_summary[k] = []
                for plate in v:
                    plate_index = v.index(plate)
                    if plate['merge_parent']:
                        pass
                        
                    else:
                        if plate['merge_children_names']:
                            self.merge_summary[k].append('{} <- {}'.format(plate['long_name'], ', '.join(plate['merge_children_names'])))
                        else:
                            self.merge_summary[k].append('{} ^'.format(plate['long_name']))


selection_group = ui.HGroup({"Spacing": 5, "Weight": 0},[
    ui.VGroup({"Spacing": 5, "Weight": 1},[
        ui.Label({"StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"}),
        ui.HGroup({"Spacing": 5, "Weight": 0},[
            ui.Label({"Text": "Timeline Filter:", "Alignment": {"AlignLeft": True}, "Weight": 0.1,}),
            ui.LineEdit({"ID": 'include_only', "Text": "", "Weight": 0.5,}),
        ]),
        ui.HGroup({"Spacing": 5, "Weight": 0},[
            ui.Label({"Text": "Pick Master Timeline:", "Alignment": {"AlignLeft": True}, "Weight": 0.1,}),
            ui.ComboBox({"ID": 'timelines', "Alignment": {"AlignLeft": True}, "Weight": 0.5,}),
        ]),
        ui.HGroup({"Spacing": 5, "Weight": 0},[
            ui.Label({"Text": "Merged Timeline Name:", "Alignment": {"AlignLeft": True}, "Weight": 0.1,}),
            ui.LineEdit({"ID": 'merged_tl_name', "Text": "merged", "Weight": 0.5,}),
        ]),
            ui.HGroup({"Spacing": 5, "Weight": 0},[
            ui.CheckBox({"ID": 'skip_clip_color', "Text": "Skip Clip Color:", "Checked": False, "AutoExclusive": True, "Checkable": True, "Events": {"Toggled": True}}),
            ui.ComboBox({"ID": 'clip_colors', "Weight": 0.8,}),
        ]),
        ui.Label({"StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"}),
        ui.HGroup({"Spacing": 5, "Weight": 0},[
            ui.Label({"Text": 'Merge Gap:',  "Weight": 0}),
            ui.SpinBox({"ID": 'merge_gap', "Value": 10, "Minimum": 0, "Maximum": 100000, "SingleStep": 1}),
        ]),
        ui.HGroup({"Spacing": 5, "Weight": 0},[
            ui.Label({"Text": "Merge By:", "Alignment": {"AlignLeft": True}, "Weight": 0.1,}),
            ui.ComboBox({"ID": 'merge_key', "Alignment": {"AlignLeft": True}, "Weight": 0.5,}),
        ]),
        ui.Label({"StyleSheet": "max-height: 1px; background-color: rgb(10,10,10)"}),
    ])
])

window_01 = ui.VGroup([
    ui.HGroup({"Spacing": 1},
        [
            ui.VGroup({"Spacing": 15, "Weight": 3},[
                selection_group,
                ui.Button({"ID": "merge_button", "Text": "Merge", "Weight": 0, "Enabled": True}),
                ui.Label({"ID": 'status', "Text": "", "Alignment": {"AlignCenter": True}}),
                ui.Label({"StyleSheet": "max-height: 5px;"}),
            ]),       
        ]
    )
])


dlg = disp.AddWindow({ 
                        'WindowTitle': 'Merge Timelines', 
                        'ID': 'MyWin',
                        'Geometry': [ 
                                    800, 500, # position when starting
                                    450, 275 # width, height
                         ], 
                        },
    window_01)


def _timelines_update(*ev):
    itm['timelines'].Clear()
    itm['timelines'].AddItems(PRJ.filter_timelines(str(dlg.Find('include_only').Text)))
    dlg.Find('status').Text = "{} timelines to merge.".format(len(PRJ.selected_tl_names))


def _merge(ev):
    print(ev)
    try:
        filter_color = bool(itm['skip_clip_color'].Checked)
        filtered_color = itm['clip_colors'].CurrentText
        if not filter_color:
            filtered_color = None

        mrg_by = itm['merge_key'].CurrentText
        if mrg_by == 'Reel Name':
            mrg = 'pool_reel'
        elif mrg_by == 'Source File':
            mrg = 'pool_file_name'

        gap = int(itm['merge_gap'].Value)

        PRJ.get_plates(filtered_color)
        PRJ.split_plates_by_reel(mrg)
        PRJ.merge_plates(gap)
        pprint.pprint(PRJ.plate_groups)
        pprint.pprint(PRJ.merge_summary)

        reels = 0
        shots = 0
        for k, v in PRJ.plate_groups.items():
            reels +=1
            for o in v:
                shots +=1
        plates = 0
        for k, v in PRJ.merge_summary.items():
            plates = plates + len(v)
        _m = "{} sources, {} shots {} plates".format(reels, shots, plates)
        print(_m)
        dlg.Find('status').Text = _m
    except Exception as err:
        log.exception(err, stack_info=True)
        print(err)

    # TODO actually make a new timeline and add plates to it



def _exit(ev):
    disp.ExitLoop()


def _run(ev):
    print('I run!')


PRJ = ResolveProject()
itm = dlg.GetItems()
itm['clip_colors'].AddItems(clipcolor_names)
itm['merge_key'].AddItems(merge_names)

dlg.On.MyWin.Close = _exit
dlg.On["Run"].Clicked = _run
dlg.On["merge_button"].Clicked = _merge

dlg.On['include_only'].TextChanged = _timelines_update
_timelines_update()

current_folder_name = str(PRJ.project_manager.GetCurrentFolder())


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


log.setLevel(logging.DEBUG)


dlg.Show()
disp.RunLoop()
dlg.Hide()
