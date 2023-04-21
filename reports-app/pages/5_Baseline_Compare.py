import json
import plotly.graph_objects as go
import plotly.express as px

import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt

from itertools import cycle

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

@st.cache_data
def get_statistics_df(statistics_file):
    df = pd.read_json(statistics_file)

    df['tc'] = pd.to_datetime(df['tc'])
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


def roll(df: pd.DataFrame, count: int) -> pd.DataFrame:
    # roll every column,
    # this is like shift() but in a cyclic way
    for column in df:
        df[column] = np.roll(df[column], count)

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
def get_meta_capacity_df(meta_file) -> pd.DataFrame:
    meta = json.load(meta_file)
    campaign_utc = meta['campainUtc']

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

    df_shifts = []
    for s in meta['shifts']:
        hh_duration, _ = hh_mm(s['duration'])
        duration = hh_mm_timedelta(s['duration'])
        start_start = hh_mm_time(s['scheduleTimeStart'])
        start_end = hh_mm_time(s['scheduleTimeEndStart'])
        end = (dt.datetime.combine(dt.date.today(), start_end) + duration).time()

        shift_id = s['id']

        dfs = []

        if shift_id not in shift_employees:  # e.g. we have extra shifts in meta file, not used by employees
            continue

        for e in shift_employees[shift_id]:
            (employee_utc, *_) = e
            delta_utc = campaign_utc - employee_utc

            df = get_1Day_df(start_start, (dt.datetime.combine(dt.date.today(), start_end) + duration).time())
            df = roll(df, delta_utc*4)  # make utc shift from employee local daytime to campaign datetime

            dfs.append(df)

        df_sum = sum(dfs)  # sum all data from all employees, this preserves indexes
        df_sum['shiftId'] = shift_id
        df_sum['start'] = start_start
        df_sum['end'] = end
        df_sum['shiftName'] = f'utc+{employee_utc}, {hh_duration}h: {start_start}-{end}'
        df_sum['utc'] = f'utc+{employee_utc}'

        df_shifts.append(df_sum)

    return pd.concat(df_shifts)

def yes_no_emoji(result: bool):
    if result:
        return ':white_check_mark:'
    else:
        return ':x:'

def columns_equal(df1: pd.DataFrame, df2: pd.DataFrame, column_name: str) -> bool:
    df1 = df1[[column_name]]
    df2 = df2[[column_name]]

    return df1.equals(df2)

@st.cache_data
def get_rostering_schedule_df(shift_meta, rostering_file) -> pd.DataFrame:

    # shift_meta = {}:
    #   shift_id -> (name, utc, utc_text, start_start (time), start_end (time), duration (timedelta), end (time))

    rostering = json.load(rostering_file)
    campaign_utc = rostering['campainUtc']
    campaign_tz = dt.timezone(dt.timedelta(hours=campaign_utc))

    start_month = dt.datetime.strptime(rostering['campainSchedule'][0]['shiftDate'], '%d.%m.%y')
    df_zero_month = get_emptyMonth_df(start_month)
    df_zero_month.index = df_zero_month.index.tz_localize(tz=campaign_tz)
    df_zero_month.sort_index()

    # employee_utc = s['employeeUtc']
    # employee_tz = datetime.timezone(datetime.timedelta(hours=employee_utc))
    # dt_shift_time_start = datetime.datetime(
    #     year=shift_date.year, month=shift_date.month, day=shift_date.day, hour=hh, minute=mm, tzinfo=employee_tz)

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

# =============================================================
### File loading
meta_file = st.sidebar.file_uploader("Upload 'meta_file.json' file: ")
baseline_statistics_file = st.sidebar.file_uploader("Upload baseline 'statistics.json' file")
statistics_file = st.sidebar.file_uploader("Upload 'statistics.json' file")

baseline_rostering_file = st.sidebar.file_uploader("Upload baseline 'rostering.json' file: ")
rostering_file = st.sidebar.file_uploader("Upload 'rostering.json' file: ")

if baseline_statistics_file is None or statistics_file is None:
    st.warning('Для продолжения работы укажите файлы со статистикой (базовый и целевой)', icon="⚠️")
    st.stop()

df_b_stats = get_statistics_df(baseline_statistics_file)
df_stats = get_statistics_df(statistics_file)


# ----------------------------------------------
# Check first whether dataframes are comparable:
# ----------------------------------------------
st.write(
    f"""
    Проверка корректности сравниваемых данных: 
     - Входные данные одинаковые: {yes_no_emoji(columns_equal(df_b_stats, df_stats, "call_volume") and
                                                columns_equal(df_b_stats, df_stats, "aht") and
                                                columns_equal(df_b_stats, df_stats, "service_level") and 
                                                columns_equal(df_b_stats, df_stats, "art"))}
     - Требуемые позиции совпадают: {yes_no_emoji(columns_equal(df_b_stats, df_stats, "Required positions"))}
     - 0 SL: {yes_no_emoji(columns_equal(df_b_stats, df_stats, "zero_level_positions"))}
    """
)

# ----------------------------------------------
# FTE basis vs target
# ----------------------------------------------
st.subheader('Результаты планирования')
st.write(
    """
    Данный график отображает запланированные ресурсы (**FTE план**) для двух версий расчетов: базового (baseline) и целевого. 
    и сравнивает их с требуемым количеством ресурсов (**FTE требуемый**), рассчитанных по Эрлангу С.
    """
)

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Required positions'], name='FTE требуемый (базис)', fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Scheduled positions'], name='FTE план (базис)', fill='tozeroy'))
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Scheduled positions'], name='FTE план'))
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['zero_level_positions'], name='SL 0%', line_color='gray', line_dash='dash'))
fig.update_layout(legend=dict(orientation="h"))
# fig.update_xaxes(rangeslider_visible=True)

st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Missed FTA basis vs target
# ----------------------------------------------
st.subheader('**Отклонения от FTE треб**')
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Missed positions'], name='FTE отклонения (базис)'))
fig2.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Missed positions'], name='FTE отклонения', line_color='coral'))
fig2.update_layout(legend=dict(orientation="h"))
st.plotly_chart(fig2, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Capacity graph
# ----------------------------------------------
st.subheader('Емкость смен (совокупная, дневная)')
st.write(
    """
    Данный график отображает емкость смен в разрезе разных часовых поясов. Данные отображены в тамйзоне кампании.

    Т.к. все дни считаются равнозначными, то нет необходимости строить месячный график.
    """
)

if meta_file is None:
    st.warning('Для продолжения работы укажите файлы метаданных', icon="⚠️")
    st.stop()

df_meta_capacity = get_meta_capacity_df(meta_file)

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = px.area(df_meta_capacity, y="works", color="utc", line_group="shiftName")
# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Daily by statistics
# ----------------------------------------------
st.subheader('Данные по статистике')
col1, col2 = st.columns(2)

df_b_stats = get_statistics_df(baseline_statistics_file)
df_stats = get_statistics_df(statistics_file)

min_day = df_b_stats.head(1).iloc[0]['tc_date']
max_day = df_b_stats.tail(1).iloc[0]['tc_date']
d = col1.date_input(
    "Выберите день, для сравнения плановых нагрузков и фактической емкости смен",
    min_value=min_day,
    max_value=max_day,
    value=min_day)

df_b_day_stat = df_b_stats[df_b_stats['tc_date'] == d]
df_b_day_stat["tc"] = df_b_day_stat["tc"].dt.time

df_day_stat = df_stats[df_stats['tc_date'] == d]
df_day_stat["tc"] = df_day_stat["tc"].dt.time

df = df_meta_capacity.copy()
df = df.reset_index()

if s := col2.multiselect('Выберите смену', df_meta_capacity['shiftName'].unique()):
    df = df[df['shiftName'].isin(s)]

df = df.groupby(['tc'], as_index=False)['works'].sum()

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_day_stat["tc"], y=df_b_day_stat["Required positions"], name="FTE треб", fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_day_stat["tc"], y=df_b_day_stat["Scheduled positions"], name="FTE план (baseline)"))
fig.add_trace(go.Scatter(x=df_day_stat["tc"], y=df_day_stat["Scheduled positions"], name="FTE план (baseline)"))
fig.add_trace(go.Scatter(x=df["tc"], y=df["works"], name="Емкость смен(ы)", line_dash='dash'))

# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Daily by schedule
# ----------------------------------------------
st.subheader('Данные по расписанию')
if baseline_rostering_file is None or rostering_file is None:
    st.warning('Для продолжения работы укажите файлы ростеринга (базовый и целевой)', icon="⚠️")
    st.stop()

palette_b = cycle(px.colors.colorbrewer.Blues)
palette_t = cycle(px.colors.colorbrewer.Reds)

shift_meta = build_shift_meta(meta_file)
df_b_rostering = get_rostering_schedule_df(shift_meta, baseline_rostering_file)
df_rostering = get_rostering_schedule_df(shift_meta, rostering_file)
df_b_stats = get_statistics_df(baseline_statistics_file)

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = px.area(df_b_rostering, y="works", color="utc", line_group="shiftName")
# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = px.area(df_rostering, y="works", color="utc", line_group="shiftName")
# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Daily by schedule with filters
# ----------------------------------------------

min_day = df_b_rostering.head(1).iloc[0]['tc_date']
max_day = df_b_rostering.tail(1).iloc[0]['tc_date']

col1, col2 = st.columns(2)
d = col1.date_input(
    "Выберите день, для сравнения плановых нагрузков и фактической емкости смен",
    min_value=min_day,
    max_value=max_day,
    value=min_day)

df_b_rostering_daily = df_b_rostering[df_b_rostering['tc_date'] == d]
df_b_rostering_daily["tc_time"] = df_b_rostering_daily.index.time

df_rostering_daily = df_rostering[df_rostering['tc_date'] == d]
df_rostering_daily["tc_time"] = df_rostering_daily.index.time

df_b_stats_daily = df_b_stats[df_b_stats['tc_date'] == d]
df_b_stats_daily["tc_time"] = df_b_stats_daily["tc"].dt.time

if s := col2.multiselect('Выберите смену', df_b_rostering['shiftName'].unique()):
    df_b_rostering_daily = df_b_rostering_daily[df_b_rostering_daily['shiftName'].isin(s)]
    df_rostering_daily = df_rostering_daily[df_rostering_daily['shiftName'].isin(s)]

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_stats_daily["tc_time"], y=df_b_stats_daily["Required positions"], name="FTE треб", fill='tozeroy',
               line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_rostering_daily["tc_time"], y=df_b_rostering_daily["works"], stackgroup  = 'utc', name="Ресурсы по календарю (baseline)"))
fig.add_trace(go.Scatter(x=df_rostering_daily["tc_time"], y=df_rostering_daily["works"], stackgroup ='utc', name="Ресурсы по календарю"))
# fig2.add_trace(go.Scatter(x=df["tc"], y=df["works"], name="Емкость смен(ы)", line_dash='dash'))

# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"))
st.plotly_chart(fig, use_container_width=True, theme='streamlit')



