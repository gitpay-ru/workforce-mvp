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
def build_shift_meta(meta):
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
def min_max_hours(meta):
    df = pd.DataFrame(meta['employees'])
    min_hours_sum = df['minWorkingHours'].sum()
    max_hours_sum = df['maxWorkingHours'].sum()

    return (min_hours_sum, max_hours_sum)


@st.cache_data
def get_meta_capacity_df(meta) -> pd.DataFrame:
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

@st.cache_data
def get_shift_quantiles_df(quantile_files, convert_to_tz = None) -> pd.DataFrame:
    dfs = []
    for quantile_file in quantile_files:
        _df = pd.read_csv(quantile_file, encoding="utf-8")
        _df = _df[['tc', 'capacity', 'positions_quantile']]

        _df['tc'] = pd.to_datetime(_df['tc'])

        if convert_to_tz:
            _df['tc'] = _df['tc'].dt.tz_convert(tz=convert_to_tz)
            # _df.set_index('tc', inplace=True)

        dfs.append(_df)

    aggregated_df = pd.concat(dfs)

    df = aggregated_df.groupby(by='tc').sum().reset_index()

    # df = df.groupby(by='tc').sum().reset_index()
    # df.reset_index(inplace=True)

    df['tc_date'] = df['tc'].dt.date
    df['tc_time'] = df['tc'].dt.time

    return df

# недостаток в позициях, missed = required - scheduled
def shortage_stat(df: pd.DataFrame):
    avg = df[df['Missed positions'] > 0.0]['Missed positions'].mean()
    sum_hr = df[df['Missed positions'] > 0.0]['Missed positions'].sum() // 4

    return (avg, sum_hr)

# перебор
def excess_stat(df: pd.DataFrame):
    avg = -1 * df_stats[df_stats['Missed positions'] < 0.0]['Missed positions'].mean()
    sum_hr = -1 * df_stats[df_stats['Missed positions'] < 0.0]['Missed positions'].sum() // 4

    return (avg, sum_hr)

# =============================================================
### File loading
meta_file = st.sidebar.file_uploader("Файл метаданных (meta_file.json):")
statistics_file = st.sidebar.file_uploader("Файл статистики (statistics_output.json):")
rostering_file = st.sidebar.file_uploader("Файл расписания (rostering.json):")

if meta_file is None:
    st.warning('Для продолжения работы укажите файлы метаданных.', icon="⚠️")
    st.stop()

meta = json.load(meta_file)
campaign_utc = meta['campainUtc']
campaign_tz = dt.timezone(dt.timedelta(hours=campaign_utc))
df_meta_capacity = get_meta_capacity_df(meta)

if statistics_file is None:
    st.warning('Для продолжения работы укажите файлы со статистикой.', icon="⚠️")
    st.stop()

df_stats = get_statistics_df(statistics_file)

# ----------------------------------------------
# Daioly graphs & compare
# ----------------------------------------------

st.header('Месячные данные')

# ----------------------------------------------
# 1. FTE basis vs target
# ----------------------------------------------
st.subheader('Результаты планирования (по статистике)')
st.write(
    """
    Данный график отображает запланированные ресурсы (**FTE план**) для двух версий расчетов: базового (baseline) и целевого. 
    и сравнивает их с требуемым количеством ресурсов (**FTE требуемый**), рассчитанных по Эрлангу С.
    """
)

tot_sum_hr = df_stats['Scheduled positions'].sum() // 4
tot_emp_meta = len(meta['employees'])
min_hrs, max_hrs = min_max_hours(meta)


col1, col2, col3, col4, col5 = st.columns(5)
col1.metric(label="Всего запланировано", value=f"{tot_sum_hr:.2f} чел./ч.")
col2.metric(label="Всего сотрудников (мета)", value=f"{tot_emp_meta} чел.")
col3.metric(label="Минимум (мета)", value=f"{min_hrs} ч.")
col4.metric(label="Максимум (мета)", value=f"{max_hrs} ч.")
col5.metric(label="Утилизация часов", value=f"{(100*tot_sum_hr/max_hrs):.2f}%")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Required positions'], name='FTE треб', fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['zero_level_positions'], name='0% SL', line_color='gray', line_dash='dash'))
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Scheduled positions'], name='FTE план'))
fig.update_layout(legend=dict(orientation="h"))
# fig.update_xaxes(rangeslider_visible=True)

st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 1.1. Missed FTA basis vs target
# ----------------------------------------------

mp_shortage_avg, mp_shortage_sum_hr = shortage_stat(df_stats)  # недостаток в позициях, missed = required - scheduled
mp_excess_avg, mp_excess_sum_hr = excess_stat(df_stats)  # перебор

col1, col2, col3, col4 = st.columns(4)
col1.metric(label="Недобор средн.", value=f"{mp_shortage_avg:.2f} поз.")
col2.metric(label="Недобор всего", value=f"{mp_shortage_sum_hr} чел/ч.")
col3.metric(label="Перебор средн.", value=f"{mp_excess_avg:.2f} поз.")
col4.metric(label="Перебор всего", value=f"{mp_excess_sum_hr} чел/ч.")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Missed positions'], name='ΔFTE'))
fig2.update_layout(legend=dict(orientation="h"), title_text='ΔFTE = FTE треб - FTE план')
st.plotly_chart(fig2, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 1.2. By schedule
# ----------------------------------------------
st.subheader('Результаты планирования (по расписанию)')

if rostering_file is None:
    st.warning('Для продолжения работы укажите файлы ростеринга.', icon="⚠️")
    st.stop()

shift_meta = build_shift_meta(meta)
df_rostering = get_rostering_schedule_df(shift_meta, rostering_file)

fig = px.area(df_rostering, y="works", color="utc", line_group="shiftName")
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Required positions'], name='FTE требуемый', line_color="gray"))
fig.update_layout(legend=dict(orientation="h"), title_text='Расписание')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 2. Service level
# ----------------------------------------------

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['service_level'], name='SL треб.)', line_color='lightgray'))
fig2.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['scheduled_service_level'], name='SL'))
fig2.update_layout(legend=dict(orientation="h"), title_text='Service level')
st.plotly_chart(fig2, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Daily graphs & compare
# ----------------------------------------------

st.header('Дневные данные')

# ----------------------------------------------
# 4. Daily schedules
# ----------------------------------------------

st.header('Загрузка на день')

col1, col2 = st.columns(2)

min_day = df_stats.head(1).iloc[0]['tc_date']
max_day = df_stats.tail(1).iloc[0]['tc_date']

day_filter = col1.date_input("Выберите день, для сравнения плановых нагрузков и фактической емкости смен", min_value=min_day, max_value=max_day, value=min_day)
shift_filter = col2.multiselect('Выберите смену', df_meta_capacity['shiftName'].unique())
quantile_files = st.file_uploader("Файл позиций смены (required_positions_*.csv):", accept_multiple_files=True)

if day_filter is None:
    st.warning('Для продолжения работы выберите день, на который провести анализ', icon="⚠️")
    st.stop()

# ----------------------------------------------
# 4.1 Daily by statistics with filters
# ----------------------------------------------

df = df_meta_capacity.copy()
df = df.reset_index()

df_stats_daily = df_stats[df_stats['tc_date'] == day_filter].copy()
df_stats_daily["tc_time"] = df_stats_daily["tc"].dt.time

df_rostering_daily = df_rostering[df_rostering['tc_date'] == day_filter].copy()
df_rostering_daily["tc_time"] = df_rostering_daily.index.time
df_rostering_daily.reset_index(inplace=True)

if shift_filter:
    df_rostering_daily = df_rostering_daily[df_rostering_daily['shiftName'].isin(shift_filter)]
    df = df[df['shiftName'].isin(shift_filter)]

df_shift_quantiles_daily = None
if len(quantile_files) > 0:
    df_shift_quantiles = get_shift_quantiles_df(quantile_files, convert_to_tz = campaign_tz)
    df_shift_quantiles_daily = df_shift_quantiles[df_shift_quantiles['tc_date'] == day_filter]

    df_shift_quantiles_daily
    df_rostering_daily

    df_shift_quantiles_daily['Missed positions'] = df_shift_quantiles_daily['positions_quantile'] - df_rostering_daily['works']

    mp_shortage_avg, mp_shortage_sum_hr = shortage_stat(df_shift_quantiles_daily)  # недостаток в позициях, missed = required - scheduled
    mp_excess_avg, mp_excess_sum_hr = excess_stat(df_shift_quantiles_daily)  # перебор

    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label="Недобор средн.", value=f"{mp_shortage_avg:.2f} поз.")
    col2.metric(label="Недобор всего", value=f"{mp_shortage_sum_hr} чел/ч.")
    col3.metric(label="Перебор средн.", value=f"{mp_excess_avg:.2f} поз.")
    col4.metric(label="Перебор всего", value=f"{mp_excess_sum_hr} чел/ч.")

df_sum = df.groupby(['tc'], as_index=False)['works'].sum()
df_rostering_daily = df_rostering_daily.groupby(['tc_time'], as_index=False)['works'].sum()

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = go.Figure()

fig.add_trace(go.Scatter(x=df_stats_daily["tc_time"], y=df_stats_daily["Required positions"], name="FTE треб", fill='tozeroy', line_color="lightgray"))
if df_shift_quantiles_daily is not None: fig.add_trace(go.Scatter(x=df_shift_quantiles_daily["tc_time"], y=df_shift_quantiles_daily["positions_quantile"], name="FTE треб (смена)", line_color='gray', line_dash='dash'))

fig.add_trace(go.Scatter(x=df_sum["tc"], y=df_sum["works"], name="Емкость смен(ы)", line_color='turquoise'))
if df_shift_quantiles_daily is not None: fig.add_trace(go.Scatter(x=df_shift_quantiles_daily["tc_time"], y=df_shift_quantiles_daily["capacity"], name="Емкость (смена)", line_color='turquoise', line_dash='dash'))

fig.add_trace(go.Scatter(x=df_stats_daily["tc_time"], y=df_stats_daily["Scheduled positions"], name="FTE эфф (по статистике)", line_color='crimson', line_dash='dot'))
fig.add_trace(go.Scatter(x=df_rostering_daily["tc_time"], y=df_rostering_daily["works"], name="FTE план (по расписанию)", line_color='crimson'))

# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"), title_text='Ресурсы на день (расписание + статистика)')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')




