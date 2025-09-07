# Create a new parser that outputs TWO CSVs:
#  - NowData.csv (one row per snapshot, minimal dynamic fields)
#  - ForecastWide.csv (one row per snapshot, 24 hourly columns H00..H23 with forecast clouds;
#                      values are filled only for hours within the daily glare window, else 0)
#
# Usage:
#   python log_parser_wide.py --in sunshade.log --outdir ./out
# Optional:
#   --tz America/Los_Angeles
#   --datefmt "%Y-%m-%d %H:%M:%S,%f"
#

#
import os
import re
import csv
import argparse
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

LINE_TS = re.compile(r'^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[INFO\] (?P<msg>.*)$')
RE_GW = re.compile(r"Today's glare window in .*?: (?P<start>\d{2}:\d{2}) -> (?P<end>\d{2}:\d{2})")
RE_TABLE_HEADER = re.compile(r"Time\s+\|\s+Elev \(Deg\)\s+\|\s+Azim \(Deg\)\s+\|\s+Clouds \(%\)\s+\|\s+UVI")
RE_SEP = re.compile(r"^-{5,}$")
RE_NOWROW = re.compile(
    r'^Now\s+\|\s+(?P<elev>-?\d+(\.\d+)?)\s+\[?(OK|NO)?\]?\s+\|\s+'
    r'(?P<azim>-?\d+(\.\d+)?)\s+\[?(OK|NO)?\]?\s+\|\s+'
    r'(?P<cloud>-?\d+(\.\d+)?)\s+\[?(OK|NO)?\]?\s+\|\s+'
    r'(?P<uvi>-?\d+(\.\d+)?)\s*$'
)
RE_FROW = re.compile(
    r'^(?P<hh>\d{2}):(?P<mm>\d{2})\s+\|\s+'
    r'(?P<elev>-?\d+(\.\d+)?)\s+\|?\s*(?:\[(OK|NO)\])?\s*\|\s+'
    r'(?P<azim>-?\d+(\.\d+)?)\s+\|?\s*(?:\[(OK|NO)\])?\s*\|\s+'
    r'(?P<cloud>-?\d+(\.\d+)?)\s+\|?\s*(?:\[(OK|NO)\])?\s*\|\s+'
    r'(?P<uvi>-?\d+(\.\d+)?)\s*$'
)
RE_ACTION = re.compile(r"Triggering webhook (?P<action>ON|OFF)")

def hour_in_window(hh:int, start:str, end:str)->bool:
    # start/end are "HH:MM". If start <= end (same day), include any hour
    # whose interval [hh:00, hh:59] intersects [start, end].
    sh, sm = map(int, start.split(':'))
    eh, em = map(int, end.split(':'))
    # Treat simple (no wrap past midnight) since glare window is daytime.
    # Include hour if any overlap:
    hour_start = hh*60
    hour_end = hh*60 + 59
    win_start = sh*60 + sm
    win_end = eh*60 + em
    return not (hour_end < win_start or hour_start > win_end)

def parse_file(infile, outdir, tzname, datefmt):
    tz = ZoneInfo(tzname)

    # relative to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(script_dir, outdir)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    now_fields = ['date', 'time', 'glare_window_start', 'glare_window_end', 'cloud_pct_now', 'action']
    wide_fields = ['snapshot_ts'] + [f'H{h:02d}' for h in range(24)]

    now_rows = []
    wide_rows = []

    # Open input file relative to the script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, infile)

    with open(file_path, 'r', encoding='utf-8') as f:
        gw_start = None
        gw_end = None

        in_table = False
        forecast_dict = None
        snapshot_ts_iso = None
        cloud_now = None
        last_action = ""

        for raw in f:
            raw = raw.rstrip('\n')
            m = LINE_TS.match(raw)
            if not m:
                continue
            ts_str = m.group('ts')
            msg = m.group('msg')
            try:
                dt = datetime.strptime(ts_str, datefmt).replace(tzinfo=tz)
            except Exception:
                continue
            snapshot_ts_iso = dt.isoformat()
            local_date = dt.strftime('%Y-%m-%d')  # Extract local date
            local_time = dt.strftime('%H:%M:%S')  # Extract local time

            mgw = RE_GW.search(msg)
            if mgw:
                gw_start = mgw.group('start')
                gw_end = mgw.group('end')
                continue

            if RE_TABLE_HEADER.search(msg):
                in_table = True
                forecast_dict = {f'H{h:02d}': 0.0 for h in range(24)}
                cloud_now = None
                last_action = ""
                continue

            if RE_SEP.search(msg):
                # either opening or closing separator; we don't toggle here
                continue

            if in_table:
                mnow = RE_NOWROW.match(msg)
                if mnow:
                    cloud_now = float(mnow.group('cloud'))
                    continue

                mf = RE_FROW.match(msg)
                if mf:
                    hh = int(mf.group('hh'))
                    cloud = float(mf.group('cloud'))
                    # Only fill if hour intersects glare window; else keep 0
                    if gw_start and gw_end and hour_in_window(hh, gw_start, gw_end):
                        forecast_dict[f'H{hh:02d}'] = cloud
                    continue

                # if it's not a data row and we're still "in_table", check if we hit end (by action or next header)
                # fallthrough; actions are outside the table

            mact = RE_ACTION.search(msg)
            if mact:
                last_action = mact.group('action')
                # On action we consider the snapshot complete IF we already had a table
                if snapshot_ts_iso and (forecast_dict is not None or cloud_now is not None):
                    # Write rows
                    now_rows.append({
                        'date': local_date,
                        'time': local_time,
                        'glare_window_start': gw_start or '',
                        'glare_window_end': gw_end or '',
                        'cloud_pct_now': cloud_now if cloud_now is not None else '',
                        'action': last_action
                    })
                    if forecast_dict is None:
                        forecast_dict = {f'H{h:02d}': 0.0 for h in range(24)}
                    wr = {'snapshot_ts': snapshot_ts_iso}
                    wr.update({k: forecast_dict[k] for k in sorted(forecast_dict.keys())})
                    wide_rows.append(wr)
                    # reset table state
                    in_table = False
                    forecast_dict = None
                    cloud_now = None
                continue

        # End of file: if a table was open without a trailing action, still flush
        if snapshot_ts_iso and (forecast_dict is not None or cloud_now is not None):
            now_rows.append({
                'date': local_date,
                'time': local_time,
                'glare_window_start': gw_start or '',
                'glare_window_end': gw_end or '',
                'cloud_pct_now': cloud_now if cloud_now is not None else '',
                'action': last_action
            })
            if forecast_dict is None:
                forecast_dict = {f'H{h:02d}': 0.0 for h in range(24)}
            wr = {'snapshot_ts': snapshot_ts_iso}
            wr.update({k: forecast_dict[k] for k in sorted(forecast_dict.keys())})
            wide_rows.append(wr)

    # Write CSVs
    now_path = outdir / 'NowData.csv'
    wide_path = outdir / 'ForecastWide.csv'
    with now_path.open('w', newline='', encoding='utf-8') as g:
        w = csv.DictWriter(g, fieldnames=now_fields)
        w.writeheader()
        for r in now_rows:
            w.writerow(r)
    with wide_path.open('w', newline='', encoding='utf-8') as g:
        w = csv.DictWriter(g, fieldnames=wide_fields)
        w.writeheader()
        for r in wide_rows:
            w.writerow(r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='infile', required=True, help='Input log file')
    ap.add_argument('--outdir', required=True, help='Output directory')
    ap.add_argument('--tz', default='America/Los_Angeles', help='IANA timezone')
    ap.add_argument('--datefmt', default='%Y-%m-%d %H:%M:%S,%f', help='Datetime format')
    args = ap.parse_args()
    parse_file(args.infile, args.outdir, args.tz, args.datefmt)
    print(f"Written NowData.csv and ForecastWide.csv to {args.outdir}")

if __name__ == '__main__':
    main()


