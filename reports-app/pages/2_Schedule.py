from pathlib import Path
import sys
# this is a hack to make streamlit working with common 'modules'
# need to include in every streamlit page
sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
import plotly.express as px
import pandas as pd
import json
import datetime

from utils.helpers import parse_datetime

st.set_page_config(
    page_title="Schedule summary",
    page_icon="📈",
)

st.header("Schedule summary")

col1, col2, col3 = st.columns(3)

st.write(
    """
    This graph illustrates a combination of resource shifts & breaks assigned per employee. 
    for shifts and breaks the following rules are applied:
     - shifts: min/max shifts per month
     - shifts: min/max wordays & holdiays in row
     - breaks: number of breaks per shift
     - breaks: min/max start time per break
     - min/max intervals between breaks
     
    You can use a full-screen view to investigate results in details.
    """
)

status_text = st.sidebar.empty()
status_text.markdown("**Waiting for files upload**")

rostering_file = st.sidebar.file_uploader("Upload 'rostering.json' file: ")
meta_file = st.sidebar.file_uploader("Upload 'meta_file.json' file: ")
if rostering_file is not None and meta_file is not None:

    status_text.markdown("**Start processing ..**")

    rostering = json.load(rostering_file)
    meta = json.load(meta_file)

    num_employees = len(meta['employees'])
    col1.metric("Total Employees", num_employees)

    shifts_duration = {}
    for s in meta['shifts']:
        shifts_duration[s['id']] = datetime.timedelta(minutes= int(s['duration'][:-3]) * 60+ int(s['duration'][-2:]))

    # shifts to dataframe
    format = '%d.%m.%y %H:%M:%S'
    shifts = map(
            lambda x: dict(Employee = str(x['employeeId']),
                           Start = parse_datetime(f"{x['shiftDate']} {x['shiftTimeStart']}"),
                           Finish = parse_datetime(f"{x['shiftDate']} {x['shiftTimeStart']}") + shifts_duration[x['shiftId']],
                           Activity = x['shiftId'],
                           width = 0.4)
            , rostering['campainSchedule']
    )

    # breaks
    df_shifts = pd.DataFrame(shifts)

    num_shifts = len(df_shifts)
    col2.metric("Shifts scheduled", num_shifts)

    # breaks to dataframe
    breaks = []

    for s in rostering['campainSchedule']:
        for a in s['activities']:
            employee_id = s['employeeId']
            activity_id = a['activityId']

            shift_start = parse_datetime(f"{s['shiftDate']} {s['shiftTimeStart']}")
            activity_start = parse_datetime(f"{s['shiftDate']} {a['activityTimeStart']}")
            activity_end = parse_datetime(f"{s['shiftDate']} {a['activityTimeEnd']}")

            if activity_end < activity_start:
                # if activity start time < shift start time => its overnight activity and just +1 day
                activity_end += datetime.timedelta(days=1)

            if activity_start < shift_start:
                # if activity start time < shift start time => its overnight activity and just +1 day
                activity_start += datetime.timedelta(days=1)
                activity_end += datetime.timedelta(days=1)

            breaks.append(
                dict(Employee = str(employee_id),
                     Start = activity_start,
                     Finish = activity_end,
                     Activity = activity_id,
                     width = 0.6)
            )

    df_breaks = pd.DataFrame(breaks)

    num_breaks = len(df_breaks)
    col3.metric("Breaks scheduled", num_breaks)

    df = pd.concat([df_shifts, df_breaks])

    status_text.markdown("**Preparing graph ..**")

    # Plotly!
    fig = px.timeline(df, x_start="Start", x_end="Finish", y="Employee", color="Activity", height=num_employees*16)
    fig.update_yaxes(autorange="reversed", visible=False, showticklabels=False)
    fig.update_layout(showlegend=False)
    for i, d in enumerate(fig.data):
        d.width = df[df['Activity'] == d.name]['width']
    # fig.update_xaxes(rangeslider_visible=True)

    st.subheader('Shifts with activities plot')
    st.plotly_chart(fig, use_container_width=True)
    st.caption('Shifts with activities plot')

    status_text.markdown("**Done**")
