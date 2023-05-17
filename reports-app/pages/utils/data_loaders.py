import json
import pandas as pd
import datetime as dt
import streamlit as st

from .helpers import hh_mm, hh_mm_time, hh_mm_timedelta, get_emptyMonth_df

@st.cache_data
def get_statistics_df(statistics_file):
    df = pd.read_json(statistics_file)

    df['tc'] = pd.to_datetime(df['tc'])
    df["tc_time"] = df["tc"].dt.time
    df['tc_date'] = df['tc'].dt.date
    df.set_index('tc', inplace=False)

    # for better printing in the legend on graph
    df = df.rename(columns={
        'positions': 'Required positions',
        'scheduled_positions': 'Scheduled positions'
    })

    df['Missed positions'] = df['Required positions'] - df['Scheduled positions']

    return df


@st.cache_data
def build_shift_meta(meta_file):
    meta = json.load(meta_file)

    schema_shifts = {}
    for s in meta['schemas']:
        schema_shifts[s['id']] = []
        for ss in s['shifts']:
            schema_shifts[s['id']].append(ss['shiftId'])

    shift_employees = {}
    for e in meta['employees']:
        utc = e['utc']
        min_hours = e['minWorkingHours']
        max_hours = e['maxWorkingHours']

        for s in e['schemas']:
            for ss in schema_shifts[s]:
                if ss not in shift_employees:
                    shift_employees[ss] = []

                shift_employees[ss].append(
                    (utc, min_hours, max_hours)  # add employee meta to shift
                )

    shifts = {}
    for s in meta['shifts']:
        hh_duration, _ = hh_mm(s['duration'])
        duration = hh_mm_timedelta(s['duration'])
        start_start = hh_mm_time(s['scheduleTimeStart'])
        start_end = hh_mm_time(s['scheduleTimeEndStart'])
        end = (dt.datetime.combine(dt.date.today(), start_end) + duration).time()

        if s['id'] not in shift_employees:
            continue

        utc, *_ = shift_employees[s['id']][0]

        # (name, utc, utc_text, start_start (time), start_end (time), duration (timedelta), end (time))
        shifts[s['id']] = (
            f'utc+{utc}, {hh_duration}h: {start_start}-{end}', utc, f'utc+{utc}', start_start, start_end, duration, end
        )

    return shifts


@st.cache_data
def get_rostering_schedule_df(meta_file, rostering_file) -> pd.DataFrame:
    shift_meta = build_shift_meta(meta_file)

    # shift_meta = {}:
    #   shift_id -> (name, utc, utc_text, start_start (time), start_end (time), duration (timedelta), end (time))

    rostering = json.load(rostering_file)

    campaign_utc = rostering['campainUtc']
    campaign_tz = dt.timezone(dt.timedelta(hours=campaign_utc))

    _df = pd.DataFrame(rostering['campainSchedule'])
    _df['shiftDate'] = pd.to_datetime(_df['shiftDate'], format='%d.%m.%y')
    start_month = _df['shiftDate'].min()
    df_zero_month = get_emptyMonth_df(start_month)
    df_zero_month.index = df_zero_month.index.tz_localize(tz=campaign_tz)
    df_zero_month.sort_index()

    df_shifts = {}
    for s in rostering['campainSchedule']:  # this is a single employee day assignment to shift
        shift_id = s['shiftId']
        (shift_name, utc, utc_text, start_start, start_end, duration, end) = shift_meta[shift_id]

        if (shift_id not in df_shifts):
            df = df_zero_month.copy()
            df['shiftId'] = shift_id
            df['shiftName'] = shift_name
            df['utc'] = utc_text
            df_shifts[shift_id] = df

        df = df_shifts[shift_id]

        d = dt.datetime.strptime(s['shiftDate'], '%d.%m.%y')
        hh, mm = hh_mm(s['shiftTimeStart'])
        shift_start = dt.datetime(year = d.year, month=d.month, day=d.day, hour=hh, minute=mm, second=0, tzinfo=campaign_tz)
        shift_end = shift_start + duration

        # mask = df.index.indexer_between(shift_start, shift_end)
        mask = (df.index >= shift_start) & (df.index < shift_end)
        df.loc[mask, ['works']] += 1

        df_shifts[shift_id] = df

    return pd.concat(list(df_shifts.values()))