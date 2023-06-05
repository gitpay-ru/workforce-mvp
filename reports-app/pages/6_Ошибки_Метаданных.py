from pathlib import Path
import sys
# this is a hack to make streamlit working with common 'modules'
# need to include in every streamlit page
sys.path.append(str(Path(__file__).resolve().parent))

import streamlit as st
import json
import datetime

from utils.helpers import hh_mm

@st.cache_data
def get_meta_schemas(meta: dict):
    meta_schemas = {}
    for s in meta['schemas']:
        schemas_id = s['id']

        schema_shifts = []
        for shift in s['shifts']:
            schema_shifts.append(shift['shiftId'])

        meta_schemas[schemas_id] = dict(
            shifts_count=len(s['shifts']),
            shift_id=s['shifts'][0]['shiftId'],
            schema_shift_ids = schema_shifts
        )

    return meta_schemas

@st.cache_data
def get_meta_shifts(meta: dict, meta_schemas):
    meta_shifts = {}
    for s in meta['shifts']:
        shift_id = s['id']

        schemas_ids = [k for k, v in meta_schemas.items() if shift_id in v['schema_shift_ids']]

        meta_shifts[shift_id] = dict(
            activities_count=len(s['activities']),
            time_start=s['scheduleTimeStart'],
            time_start_end=s['scheduleTimeEndStart'],
            schema_ids = schemas_ids
        )

    return meta_shifts


@st.cache_data
def get_meta_employees(meta: dict, meta_schemas, meta_shifts):
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


st.set_page_config(
    page_title="Ошибки в метаданных",
    page_icon="📈",
)

st.header("Ошибки в метаданных")

meta_file = st.sidebar.file_uploader("Выберите файл метаданных 'meta_file.json': ")

if meta_file is not None:

    meta = json.load(meta_file)

    meta_schemas = get_meta_schemas(meta)
    meta_shifts = get_meta_shifts(meta, meta_schemas)
    meta_employees = get_meta_employees(meta, meta_schemas, meta_shifts)

    st.subheader('Схемы')
    col1, col2, col3 = st.columns(3)
    col1.metric('Всего схем', len(meta_schemas))
    col2.metric('Смены не заданы', len(list(filter(lambda x: meta_schemas[x]['shifts_count'] == 0, meta_schemas))))
    col3.metric('Несколько смен', len(list(filter(lambda x: meta_schemas[x]['shifts_count'] > 1, meta_schemas))))
    with st.expander("Показать метаданные схем"):
        meta_schemas

    st.subheader('Смены')
    col1, col2, col3, col4 = st.columns(4)
    col1.metric('Всего смен', len(meta_shifts))
    col2.metric('Всего активностей', len(list(filter(lambda x: meta_shifts[x]['activities_count'] == 0, meta_shifts))))
    col3.metric('Схемы не заданы', len(list(filter(lambda x: len(meta_shifts[x]['schema_ids']) == 0, meta_shifts))))
    col4.metric('Несколько схем', len(list(filter(lambda x: len(meta_shifts[x]['schema_ids']) > 1, meta_shifts))))
    with st.expander("Показать метаданные смен"):
        meta_shifts

    st.subheader('Сотрудники')
    col1, *_ = st.columns(3)
    col1.metric("Всего сотрудников", len(meta_employees))
    with st.expander("Показать метаданные по сотрудникам"):
        meta_employees
