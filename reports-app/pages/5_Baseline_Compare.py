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

from utils.helpers import hh_mm, hh_mm_time, hh_mm_timedelta, get_1Day_df, get_emptyMonth_df, roll
from utils.data_loaders import get_statistics_df, get_rostering_schedule_df

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


# =============================================================
### File loading
meta_file = st.sidebar.file_uploader("Upload 'meta_file.json' file: ")

with st.sidebar.expander("Baseline") as c:
    baseline_statistics_file = st.file_uploader("Upload baseline 'statistics.json' file")
    baseline_rostering_file = st.file_uploader("Upload baseline 'rostering.json' file: ")

with st.sidebar.expander("Target"):
    statistics_file = st.file_uploader("Upload 'statistics.json' file")
    rostering_file = st.file_uploader("Upload 'rostering.json' file: ")

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

tot_1_sum_hr = df_b_stats['Scheduled positions'].sum() // 4
tot_2_sum_hr = df_stats['Scheduled positions'].sum() // 4
st.metric(label="Всего запланировано", value=f"{tot_2_sum_hr:.2f} чел/час", delta=f"{(tot_2_sum_hr - tot_1_sum_hr):.2f}")

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Required positions'], name='FTE требуемый (базис)', fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Scheduled positions'], name='FTE план (базис)', fill='tozeroy'))
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Scheduled positions'], name='FTE план'))
fig.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['zero_level_positions'], name='0% SL', line_color='gray', line_dash='dash'))
fig.update_layout(legend=dict(orientation="h"))
# fig.update_xaxes(rangeslider_visible=True)

st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 1.1. Missed FTA basis vs target
# ----------------------------------------------

# недостаток в позициях, missed = required - scheduled
mp_shortage_1_avg = df_b_stats[df_b_stats['Missed positions'] > 0.0]['Missed positions'].mean()
mp_shortage_1_cnt = df_b_stats[df_b_stats['Missed positions'] > 0.0]['Missed positions'].count()
mp_shortage_1_sum_hr = df_b_stats[df_b_stats['Missed positions'] > 0.0]['Missed positions'].sum() // 4
mp_shortage_2_avg = df_stats[df_stats['Missed positions'] > 0.0]['Missed positions'].mean()
mp_shortage_2_cnt = df_stats[df_stats['Missed positions'] > 0.0]['Missed positions'].count()
mp_shortage_2_sum_hr = df_stats[df_stats['Missed positions'] > 0.0]['Missed positions'].sum() // 4

# перебор
mp_excess_1_avg = -1 * df_b_stats[df_b_stats['Missed positions'] < 0.0]['Missed positions'].mean()
mp_excess_1_cnt = df_b_stats[df_b_stats['Missed positions'] < 0.0]['Missed positions'].count()
mp_excess_1_sum_hr = -1 * df_b_stats[df_b_stats['Missed positions'] < 0.0]['Missed positions'].sum() // 4
mp_excess_2_avg = -1 * df_stats[df_stats['Missed positions'] < 0.0]['Missed positions'].mean()
mp_excess_2_cnt = df_stats[df_stats['Missed positions'] < 0.0]['Missed positions'].count()
mp_excess_2_sum_hr = -1 * df_stats[df_stats['Missed positions'] < 0.0]['Missed positions'].sum() // 4

col1, col2, col3, col4 = st.columns(4)
col1.metric(label="Недобор средн.", value=f"{mp_shortage_2_avg:.2f} поз.", delta=f"{(mp_shortage_2_avg - mp_shortage_1_avg):.2f}", delta_color="inverse")
col2.metric(label="Недобор всего", value=f"{mp_shortage_2_sum_hr:.2f} чел/час", delta=f"{(mp_shortage_2_sum_hr - mp_shortage_1_sum_hr):.2f}", delta_color="inverse")
col3.metric(label="Перебор средн.", value=f"{mp_excess_2_avg:.2f} поз.", delta=f"{(mp_excess_2_avg - mp_excess_1_avg):.2f}", delta_color="inverse")
col4.metric(label="Перебор всего", value=f"{mp_excess_2_sum_hr:.2f} чел/час", delta=f"{(mp_excess_2_sum_hr - mp_excess_1_sum_hr):.2f}", delta_color="inverse")

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Missed positions'], name='ΔFTE (базис)'))
fig2.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['Missed positions'], name='ΔFTE', line_color='coral'))
fig2.update_layout(legend=dict(orientation="h"), title_text='ΔFTE = FTE треб - FTE план')
st.plotly_chart(fig2, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 1.2. By schedule
# ----------------------------------------------
st.subheader('Результаты планирования (по расписанию)')

if baseline_rostering_file is None or rostering_file is None:
    st.warning('Для продолжения работы укажите файлы ростеринга (базовый и целевой)', icon="⚠️")
    st.stop()

df_b_rostering = get_rostering_schedule_df(meta_file, baseline_rostering_file)
df_rostering = get_rostering_schedule_df(meta_file, rostering_file)

# Rostering 1
fig = px.area(df_b_rostering, y="works", color="utc", line_group="shiftName")
fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Required positions'], name='FTE требуемый', line_color="gray"))
fig.update_layout(legend=dict(orientation="h"), title_text='Расписание 1 (baseline)')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# Rostering 2
fig = px.area(df_rostering, y="works", color="utc", line_group="shiftName")
fig.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['Required positions'], name='FTE требуемый', line_color="gray"))
fig.update_layout(legend=dict(orientation="h"), title_text='Расписание 2')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')
px.area()


# ----------------------------------------------
# 2. Service level
# ----------------------------------------------

fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['service_level'], name='SL (базис)', line_color='lightgray'))
fig2.add_trace(go.Scatter(x=df_b_stats['tc'], y=df_b_stats['scheduled_service_level'], name='SL (базис)'))
fig2.add_trace(go.Scatter(x=df_stats['tc'], y=df_stats['scheduled_service_level'], name='SL'))
fig2.update_layout(legend=dict(orientation="h"), title_text='Service level')
st.plotly_chart(fig2, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# Daioly graphs & compare
# ----------------------------------------------

st.header('Дневные данные')

# ----------------------------------------------
# 3. Capacity graph
# ----------------------------------------------
st.subheader('Емкость смен (совокупная, дневная)')
st.write(
    """
    Данный график отображает емкость смен в разрезе разных часовых поясов. Данные отображены в тамйзоне кампании.
    График отображает дневные данные, т.к. нет правил регламентирующих иное распределение ресурсов, т.е. все дни месяца - одинаковые.
    """
)

if meta_file is None:
    st.warning('Для продолжения работы укажите файлы метаданных', icon="⚠️")
    st.stop()

df_meta_capacity = get_meta_capacity_df(meta_file)

fig = px.area(df_meta_capacity, y="works", color="utc", line_group="shiftName")
fig.update_layout(legend=dict(orientation="h"), title_text='Доступность ресурсов по сменам')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 4. Daily schedules
# ----------------------------------------------

st.header('Загрузка на день')

col1, col2 = st.columns(2)

min_day = df_b_stats.head(1).iloc[0]['tc_date']
max_day = df_b_stats.tail(1).iloc[0]['tc_date']

df = df_meta_capacity.copy()
df = df.reset_index()

day_filter = col1.date_input("Выберите день, для сравнения плановых нагрузков и фактической емкости смен", min_value=min_day, max_value=max_day, value=min_day)
shift_filter = col2.multiselect('Выберите смену', df_meta_capacity['shiftName'].unique())

if day_filter is None:
    st.warning('Для продолжения работы выберите день, на который провести анализ', icon="⚠️")
    st.stop()

# ----------------------------------------------
# 4.1 Daily by statistics with filters
# ----------------------------------------------

df_b_stats_daily = df_b_stats[df_b_stats['tc_date'] == day_filter].copy()
df_stats_daily = df_stats[df_stats['tc_date'] == day_filter].copy()

if shift_filter:
    df = df[df['shiftName'].isin(shift_filter)]

df_sum = df.groupby(['tc'], as_index=False)['works'].sum()

# fig = px.bar(df_meta_capacity, y="works", color="shiftId")  # x == 'tc', this is an index
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_stats_daily["tc_time"], y=df_b_stats_daily["Required positions"], name="FTE треб", fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_stats_daily["tc_time"], y=df_b_stats_daily["Scheduled positions"], name="FTE план (baseline)", line_color='dodgerblue'))
fig.add_trace(go.Scatter(x=df_stats_daily["tc_time"], y=df_stats_daily["Scheduled positions"], name="FTE план", line_color='crimson'))
fig.add_trace(go.Scatter(x=df_sum["tc"], y=df_sum["works"], name="Емкость смен(ы)", line_color='turquoise', line_dash='dash'))

# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"), title_text='Ресурсы на день (по статистике)')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 4.2 Daily by schedule with filters
# ----------------------------------------------

df_b_rostering_daily = df_b_rostering[df_b_rostering['tc_date'] == day_filter].copy()
df_b_rostering_daily["tc_time"] = df_b_rostering_daily.index.time

df_rostering_daily = df_rostering[df_rostering['tc_date'] == day_filter].copy()
df_rostering_daily["tc_time"] = df_rostering_daily.index.time

if shift_filter:
    df_b_rostering_daily = df_b_rostering_daily[df_b_rostering_daily['shiftName'].isin(shift_filter)]
    df_rostering_daily = df_rostering_daily[df_rostering_daily['shiftName'].isin(shift_filter)]
    df = df[df['shiftName'].isin(shift_filter)]

df_b_rostering_daily = df_b_rostering_daily.groupby(['tc_time'], as_index=False)['works'].sum()
df_rostering_daily = df_rostering_daily.groupby(['tc_time'], as_index=False)['works'].sum()

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_stats_daily["tc_time"], y=df_b_stats_daily["Required positions"], name="FTE треб", fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_rostering_daily["tc_time"], y=df_b_rostering_daily["works"], name="Ресурсы по календарю (baseline)", line_color='dodgerblue'))
fig.add_trace(go.Scatter(x=df_rostering_daily["tc_time"], y=df_rostering_daily["works"], name="Ресурсы по календарю", line_color='crimson'))
fig.add_trace(go.Scatter(x=df_sum["tc"], y=df_sum["works"], name="Емкость смен(ы)", line_color='turquoise', line_dash='dash'))

# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"), title_text='Ресурсы на день (по расписанию)')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')

# ----------------------------------------------
# 4.3 Daily by schedule with filters
# ----------------------------------------------

fig = go.Figure()
fig.add_trace(go.Scatter(x=df_b_stats_daily["tc_time"], y=df_b_stats_daily["Required positions"], name="FTE треб", fill='tozeroy', line_color="lightgray"))
fig.add_trace(go.Scatter(x=df_b_rostering_daily["tc_time"], y=df_b_rostering_daily["works"], name="FTE план (по расписанию) (baseline)", line_color='dodgerblue'))
fig.add_trace(go.Scatter(x=df_b_stats_daily["tc_time"], y=df_b_stats_daily["Scheduled positions"], name="FTE эфф (по статистике) (baseline)", line_color='dodgerblue', line_dash='dash'))
fig.add_trace(go.Scatter(x=df_rostering_daily["tc_time"], y=df_rostering_daily["works"], name="FTE план (по расписанию)", line_color='crimson'))
fig.add_trace(go.Scatter(x=df_stats_daily["tc_time"], y=df_stats_daily["Scheduled positions"], name="FTE эфф (по статистике)", line_color='crimson', line_dash='dash'))

# fig.update_xaxes(showticklabels=True)
fig.update_layout(legend=dict(orientation="h"), title_text='Ресурсы на день (статистика - расписание)')
st.plotly_chart(fig, use_container_width=True, theme='streamlit')


