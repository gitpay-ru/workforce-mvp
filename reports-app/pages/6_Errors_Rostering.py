import pandas
import streamlit as st
import plotly.express as px
import pandas as pd
import json
import datetime
import plost

def hh_mm(time_string):
    hh = int(time_string.split(":")[0])
    mm = int(time_string.split(":")[1])

    return (hh, mm)

@st.cache_data
def get_meta_schemas(meta):
    meta_schemas = {}
    for s in meta['schemas']:
        schemas_id = s['id']

        meta_schemas[schemas_id] = dict(
            shifts_count=len(s['shifts']),
            shift_id=s['shifts'][0]['shiftId']
        )

    return meta_schemas

@st.cache_data
def get_meta_shifts(meta):
    meta_shifts = {}
    for s in meta['shifts']:
        shift_id = s['id']

        meta_shifts[shift_id] = dict(
            activities_count=len(s['activities']),
            time_start=s['scheduleTimeStart'],
            time_start_end=s['scheduleTimeEndStart']
        )

    return meta_shifts


@st.cache_data
def get_meta_employees(meta, meta_schemas, meta_shifts):
    meta_employees = {}
    for e in meta['employees']:
        _employee_id = e['id']
        _employee_schema_id = e['schemas'][0]
        _employee_shift_id = meta_schemas[_employee_schema_id]['shift_id']

        _employee_utc = e['utc']
        _shift_time_start = meta_shifts[_employee_shift_id]['time_start']
        _shift_time_start_end = meta_shifts[_employee_shift_id]['time_start_end']

        _offset = datetime.timedelta(hours=e['utc'])
        _tz = datetime.timezone(_offset)

        (hh, mm) = hh_mm(_shift_time_start)
        dt_start = datetime.time(hour=hh, minute=mm, tzinfo=_tz)

        (hh, mm) = hh_mm(_shift_time_start_end)
        dt_start_end = datetime.time(hour=hh, minute=mm, tzinfo=_tz)

        meta_employees[_employee_id] = dict(
            schema_id=_employee_schema_id,
            shift_id=_employee_shift_id,
            employee_utc=_employee_utc,
            shift_time_start=_shift_time_start,
            dt_shift_time_start=dt_start,
            shift_time_start_end=_shift_time_start_end,
            dt_shift_time_start_end=dt_start_end,
            tz = _tz
        )

    return meta_employees


@st.cache_data
def get_errors_df(rostering, meta_employees, ):
    # (employee_id, error_text, expected, actual)
    errors = []

    # check rostering data
    campaign_utc = rostering['campainUtc']
    campaign_tz = datetime.timezone(datetime.timedelta(hours=campaign_utc))
    for s in rostering['campainSchedule']:

        employee_id = s['employeeId']
        e = meta_employees[employee_id]

        if s['employeeUtc'] != e['employee_utc']:
            errors.append((
                employee_id, f'Wrong employeeUtc', e['employee_utc'], s['employeeUtc']
            ))

        if s['schemaId'] != e['schema_id']:
            errors.append((
                employee_id, f'Wrong schemaId', e['schema_id'], s['schemaId']
            ))

        if s['shiftId'] != e['shift_id']:
            errors.append((
                employee_id, f'Wrong shiftId', e['shift_id'], s['shiftId']
            ))

        shift_date = datetime.datetime.strptime(s['shiftDate'], '%d.%m.%y')
        (hh, mm) = hh_mm(s['shiftTimeStart'])
        dt_shift_time_start = datetime.datetime(
            year=shift_date.year, month=shift_date.month, day=shift_date.day, hour=hh, minute=mm, tzinfo=campaign_tz)

        # campain-based time start
        shift_time_start_tz = dt_shift_time_start.timetz()
        # employee-based time start
        shift_time_start_tz_e = dt_shift_time_start.astimezone(e['tz']).timetz()

        if (shift_time_start_tz_e < e['dt_shift_time_start']) or (shift_time_start_tz_e > e['dt_shift_time_start_end']):
            errors.append((
                employee_id,
                f'Wrong shift start time',
                f"{e['dt_shift_time_start']} – {e['dt_shift_time_start_end']}",
                f"{shift_time_start_tz} ({shift_time_start_tz_e})"
            ))

    # employees in rostering should equal to employees from meta file
    df_rostering = pandas.DataFrame(rostering['campainSchedule'])
    rostering_count = len(df_rostering['employeeId'].unique())
    meta_count = len(meta_employees)
    if rostering_count != meta_count:
        errors.append(
            ('', 'Wrong employees number', meta_count, rostering_count)
        )


    df_errors = pd.DataFrame(errors, columns=['Employee Id', 'Error Type', 'Expected', 'Actual'])
    df_errors = df_errors.drop_duplicates()

    return df_errors


st.set_page_config(
    page_title="Errors report",
    page_icon="📈",
)

st.header("Errors (Rostering) report")

rostering_file = st.sidebar.file_uploader("Upload 'rostering.json' file: ")
meta_file = st.sidebar.file_uploader("Upload 'meta_file.json' file: ")

if rostering_file is not None and meta_file is not None:

    rostering = json.load(rostering_file)
    meta = json.load(meta_file)

    meta_schemas = get_meta_schemas(meta)
    meta_shifts = get_meta_shifts(meta)
    meta_employees = get_meta_employees(meta, meta_schemas, meta_shifts)

    # (employee_id, error_text, expected, actual)
    errors = []
    df_errors = get_errors_df(rostering, meta_employees)

    if len(df_errors) > 0:

        # filter widget by Error Type:
        if error_type := st.multiselect("Error Type", df_errors['Error Type'].unique().tolist(), key=1):
            df_errors = df_errors[df_errors['Error Type'].isin(error_type)]

        if employee_search := st.text_input("Employee Id"):
            df_errors = df_errors[df_errors['Employee Id'].str.contains(employee_search, case=False, na=False)]

        st.dataframe(df_errors)

        col1, = st.columns(1)
        col1.metric('Errors count', len(df_errors))

    # # Plotly!
    # fig = px.timeline(df, x_start="Start", x_end="Finish", y="Employee", color="Activity", height=num_employees*16)
    # fig.update_yaxes(autorange="reversed", visible=False, showticklabels=False)
    # fig.update_layout(showlegend=False)
    # for i, d in enumerate(fig.data):
    #     d.width = df[df['Activity'] == d.name]['width']
    # # fig.update_xaxes(rangeslider_visible=True)
    #
    # st.subheader('Shifts with activities plot')
    # st.plotly_chart(fig, use_container_width=True)
    # st.caption('Shifts with activities plot')

# Streamlit widgets automatically run the script from top to bottom. Since
# this button is not connected to any other logic, it just causes a plain
# rerun.
# st.button("Re-run")