from pathlib import Path
import sys
# this is a hack to make streamlit working with common 'modules'
# need to include in every streamlit page
sys.path.append(str(Path(__file__).resolve().parent))

import json
import plotly.graph_objects as go
import plotly.express as px

import streamlit as st
import pandas as pd
import datetime as dt

from utils.helpers import hh_mm, hh_mm_time, hh_mm_timedelta, get_1Day_df, roll
from utils.data_loaders import get_statistics_df


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

meta_file = st.sidebar.file_uploader("Файл метаданных (meta_file.json):")
statistics_file = st.sidebar.file_uploader("Файл статистики (statistics_output.json):")

if meta_file is None:
    st.warning('Для продолжения работы укажите файл с метаданными.', icon="⚠️")
    st.stop()

st.header('Анализ смен')

# ----------------------------------------------
# Capacity graph
# ----------------------------------------------
st.subheader('Емкость смен (совокупная, дневная)')
st.write(
    """
    Данный график отображает емкость смен в разрезе разных часовых поясов. Данные отображены в тамйзоне кампании.
    График отображает дневные данные, т.к. нет правил регламентирующих иное распределение ресурсов, т.е. все дни месяца - одинаковые.
    """
)

df_meta_capacity = get_meta_capacity_df(meta_file)

fig = px.area(df_meta_capacity, y="works", color="utc", line_group="shiftName")
fig.update_layout(legend=dict(orientation="h"), title_text='Доступность ресурсов по сменам')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

if statistics_file is None:
    st.warning('Для продолжения работы укажите файл со статистикой.', icon="⚠️")
    st.stop()

col1, col2 = st.columns(2)

df_stats = get_statistics_df(statistics_file)
min_day = df_stats.head(1).iloc[0]['tc_date']
max_day = df_stats.tail(1).iloc[0]['tc_date']
d = col1.date_input(
    "Выберите день, для сравнения нагрузки и фактической емкости смен",
    min_value=min_day,
    max_value=max_day,
    value=min_day)

df_day_stat = df_stats[df_stats['tc_date'] == d].copy()

df = df_meta_capacity.copy()
df = df.reset_index()

if s := col2.multiselect('Выберите смену', df_meta_capacity['shiftName'].unique()):
    df = df[df['shiftName'].isin(s)]

df = df.groupby(['tc'], as_index=False)['works'].sum()

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = go.Figure()
fig.add_trace(go.Scatter(x=df["tc"], y=df["works"], fill='tozeroy', line_color="lightgray", name="Shifts capacity"))
fig.add_trace(go.Scatter(x=df_day_stat["tc_time"], y=df_day_stat["Required positions"], name="Required positions"))
# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"), title_text='Покрытие сменами')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')
