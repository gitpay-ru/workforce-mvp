import json
import plotly.graph_objects as go
import plotly.express as px

import streamlit as st
import pandas as pd
import numpy as np
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

st.write(
    """
    This report compares **Required** positions and **Scheduled** positions by the model.
    It is expected that scheduled positions would be below the required positions line.
    If Scheduled positions are above the required line => this indicates non-optimal scheduling.

    You can use a full-screen view to investigate results in details.
    """
)

meta_file = st.sidebar.file_uploader("Upload 'meta_file.json' file: ")
baseline_statistics_file = st.sidebar.file_uploader("Upload baseline 'statistics.json' file")
statistics_file = st.sidebar.file_uploader("Upload 'statistics.json' file")

baseline_rostering_file = st.sidebar.file_uploader("Upload baseline 'rostering.json' file: ")
rostering_file = st.sidebar.file_uploader("Upload 'rostering.json' file: ")

### FTE basis vs target
st.subheader('Результаты планирования')
st.write(
    """
    Данный график отображает запланированные ресурсы (**FTE план**) для двух версий расчетов: базового (baseline) и целевого. 
    и сравнивает их с требуемым количеством ресурсов (**FTE требуемый**), рассчитанных по Эрлангу С.
    """
)
if baseline_statistics_file is not None and statistics_file is not None:
    df_b_stats = get_statistics_df(baseline_statistics_file)
    df_stats = get_statistics_df(statistics_file)

    # wrong Y axis - replace it with plotly graphs, because area chart shows propotion by default
    # st.area_chart(
    #     data = df_stats,
    #     x = "tc",
    #     y = ["positions", "scheduled_positions"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Required positions'], name='FTE требуемый (базис)', fill='tozeroy'))
    fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Scheduled positions'], name='FTE план (базис)', fill='tozeroy'))
    fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Scheduled positions'], name='FTE план', fill='tozeroy'))

    fig.update_layout(legend=dict(orientation="h"))
    # fig.update_xaxes(rangeslider_visible=True)

    st.plotly_chart(fig, use_container_width=True, theme='streamlit')
else:
    st.warning('Для работы с графиком укажите файлы со статистикой (базовый и целевой)', icon="⚠️")


if meta_file is not None:
    st.subheader('Емкость смен (совокупная, дневная)')
    st.write(
        """
        Данный график отображает емкость смен в разрезе разных часовых поясов. Данные отображены в тамйзоне кампании.
        
        Т.к. все дни считаются равнозначными, то нет необходимости строить месячный график.
        """
    )

    df_meta_capacity = get_meta_capacity_df(meta_file)

    # fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
    fig = px.area(df_meta_capacity, y="works", color="utc", line_group="shiftName")
    # fig.update_xaxes(showticklabels=True)
    fig.update_layout(legend=dict(orientation="h"))
    st.plotly_chart(fig, use_container_width=True, theme='streamlit')

    if statistics_file is not None:
        st.subheader('Дневные данные')
        col1, col2 = st.columns(2)

        df_stats = get_statistics_df(statistics_file)
        min_day = df_stats.head(1).iloc[0]['tc_date']
        max_day = df_stats.tail(1).iloc[0]['tc_date']
        d = col1.date_input(
            "Выберите день, для сравнения нагрузки и фактической емкости смен",
            min_value=min_day,
            max_value=max_day,
            value=min_day)

        df_day_stat = df_stats[df_stats['tc_date'] == d]
        df_day_stat["tc"] = df_day_stat["tc"].dt.time

        df = df_meta_capacity.copy()
        df = df.reset_index()

        if s := col2.multiselect('Выберите смену', df_meta_capacity['shiftName'].unique()):
            df = df[df['shiftName'].isin(s)]

        df = df.groupby(['tc'], as_index=False)['works'].sum()

        # fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_day_stat["tc"], y=df_day_stat["Required positions"], name="Required positions (baseline)",fill='tozeroy', line_color="lightgray"))
        fig.add_trace(go.Scatter(x=df_day_stat["tc"], y=df_day_stat["Required positions"], name="Required positions",fill='tozeroy', line_color="lightgray"))
        fig.add_trace(go.Scatter(x=df["tc"], y=df["works"], name="Shifts capacity (baseline)", line_dash='dash'))
        fig.add_trace(go.Scatter(x=df["tc"], y=df["works"], name="Shifts capacity"))


        # fig.update_xaxes(showticklabels=True)
        fig.update_layout(legend=dict(orientation="h"))
        st.plotly_chart(fig, use_container_width=True, theme='streamlit')

