import streamlit as st

import numpy as np
import pandas as pd
import datetime as dt

def hh_mm(time_string):
    hh = int(time_string.split(":")[0])
    mm = int(time_string.split(":")[1])

    return (hh, mm)


def hh_mm_time(time_string) -> dt.time:
    (hh, mm) = hh_mm(time_string)
    return dt.time(hour=hh, minute=mm)


def hh_mm_timedelta(time_string) -> dt.timedelta:
    (hh, mm) = hh_mm(time_string)
    return dt.timedelta(hours=hh, minutes=mm)

def parse_datetime(dt_str: str) -> dt.datetime:
    format_1 = '%d.%m.%y %H:%M:%S'
    format_2 = '%d.%m.%y %H:%M'

    try:
        timestamp = dt.datetime.strptime(dt_str, format_1)
    except ValueError:
        timestamp = dt.datetime.strptime(dt_str, format_2)

    return timestamp


def roll(df: pd.DataFrame, count: int) -> pd.DataFrame:
    # roll every column,
    # this is like shift() but in a cyclic way
    for column in df:
        df[column] = np.roll(df[column], count)

    return df

@st.cache_data
def get_emptyDay_df() -> pd.DataFrame:
    intervals = int(24 * 60 / 15)

    t = [dt.time(hour=int(i*15 / 60), minute=i*15 % 60) for i in range(intervals)]
    presence = [0 for i in range(intervals)]
    data = {
        "tc": t,
        "works": presence
    }

    df = pd.DataFrame(data, columns=['tc', 'works'])
    df.set_index('tc', inplace=True)
    return df


@st.cache_data
def get_emptyMonth_df(start_date: dt.date) -> pd.DataFrame:
    intervals = 31 * int(24 * 60 / 15)
    t = pd.Timedelta("15 minutes")

    tc = [start_date + i*t for i in range(intervals)]
    works = [0 for i in range(intervals)]

    data = {
        "tc": tc,
        "works": works
    }

    df = pd.DataFrame(data, columns=['tc', 'works'])

    df['tc'] = pd.to_datetime(df['tc'])
    df['tc_time'] = df['tc'].dt.time
    df['tc_date'] = df['tc'].dt.date

    df.set_index('tc', inplace=True)
    return df


@st.cache_data
def get_1Day_df(time_start: dt.time, time_end: dt.time) -> pd.DataFrame:
    intervals = int(24*60/15)
    t = [dt.time(hour=int(i * 15 / 60), minute=i * 15 % 60) for i in range(intervals)]

    if time_end > time_start:
        presence = [1 if (t[i] >= time_start and t[i] <= time_end) else 0 for i in range(intervals)]
    else:
        presence = [1 if (t[i] >= time_start or t[i] <= time_end) else 0 for i in range(intervals)]

    data = {
        "tc": t,
        "works": presence
    }

    df = pd.DataFrame(data, columns=['tc', 'works'])
    df.set_index('tc', inplace=True)
    return df