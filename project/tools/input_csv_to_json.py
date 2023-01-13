import pandas
import json
import codecs
import sys

import pandas as pd

# 0. Static configuration

min_working_hours = 176
max_working_hours = 176

known_timezones = {
    'GMT+3': +3,
    'GMT+4': +4,
    'GMT+7': +7,
}

#   (duration, start_from, start_to, paid)
known_breaks = {
    '9 часов день обед': ('00:30', '03:00', '05:30', False),
    '9 часов день перерыв 1': ('00:15', '02:00', '07:00', True),
    '9 часов день перерыв 2': ('00:15', '05:30', '08:00', True),

    '9 часов ночь обед': ('00:30', '03:00', '05:30', False),
    '9 часов ночь перерыв 1': ('00:15', '02:00', '07:00', True),
    '9 часов ночь перерыв 2': ('00:15', '05:30', '08:00', True),
    '9 часов ночь перерыв 3 личн': ('00:15', '01:00', '08:00', False),

    '12 часов день обед 1': ('00:30', '03:00', '05:30', False),
    '12 часов день обед 2': ('00:30', '05:30', '09:00', False),
    '12 часов день перерыв 1': ('00:15', '05:30', '11:00', True),
    '12 часов день перерыв 2': ('00:15', '01:00', '10:00', True),

    '12 часов ночь обед': ('01:00', '04:00', '06:00', False),
    '12 часов ночь перерыв 1': ('00:15', '01:00', '04:00', True),
    '12 часов ночь перерыв 2': ('00:15', '05:30', '11:00', True),
    '12 часов ночь перерыв 3': ('00:15', '08:00', '11:00', True),
    '12 часов ночь перерыв 4': ('00:15', '01:00', '10:00', True),
}

#   (duration, start_from, start_to, step_time, breaks, breaks_min_interval, breaks_max_interval)
known_shifts = {
    '9часов день': ('09:00', '06:00', '13:00', '00:15',
                    ['9 часов день обед 1', '9 часов день перерыв 1', '9 часов день перерыв 2'], '01:30', '03:30'),

    '9часов ночь': ('09:00', '21:00', '22:00', '00:15',
                    ['9 часов ночь обед', '9 часов ночь перерыв 1', '9 часов ночь перерыв 2', '9 часов ночь перерыв 3 личн'], '01:30', '03:30'),

    '12часов день': ('12:00', '06:00', '11:00', '00:15',
                     ['12 часов день обед 1', '12 часов день обед 2', '12 часов день перерыв 1', '12 часов день перерыв 2'], '01:30', '03:30'),

    '12часов ночь': ('12:00', '18:00', '22:00', '00:15',
                     ['12 часов ночь обед', '12 часов ночь перерыв 1', '12 часов ночь перерыв 2', '12 часов ночь перерыв 3', '12 часов ночь перерыв 4'], '01:30', '03:30'),
}

month_days = [(i+1) for i in range(31)]

known_schemas = {
    'MS_9часов день': ['9часов день'],
    'MS_12часов день': ['12часов день'],
    'MS_9часов ночь': ['9часов ночь'],
    'SM_9часов день': ['9часов день'],
    'SM_12часов день': ['12часов день'],
    'SM_9часов ночь': ['9часов ночь'],
    'SM_12часов ночь': ['12часов ночь'],
    'NV_9часов день': ['9часов день'],
    'NV_12часов день': ['12часов день'],
}

# 1. Read excel document
df = pandas.read_excel('../../tmp/Сотрудники_110123 входные данные.xlsx', sheet_name='Схемы работы назначение')

print('Columns:')
print(df.columns.tolist())


# 2. builders
def build_activities():
    activities = []

    for break_id, break_context in known_breaks.items():
        (duration, start_from, start_to, is_paid) = break_context
        activities.append(
            {
                "id": break_id,
                "duration": duration,
                "timeStart": start_from,
                "timeEndStart": start_to,
                "isPaid": is_paid
            }
        )

    return activities

def build_shifts():
    shifts = []

    for shift_id, shift_context in known_shifts.items():
        (duration, start_from, start_to, step_time, breaks, breaks_min_interval, breaks_max_interval) = shift_context
        shifts.append(
            {
                "id": shift_id,
                "duration": duration,
                "stepTime": step_time,
                "scheduleTimeStart": start_from,
                "scheduleTimeEndStart": start_to,
                "minIntervalBetweenActivities": breaks_min_interval,
                "maxIntervalBetweenActivities": breaks_max_interval,
                "activities": breaks
            }
        )

    return shifts

def build_schemas():
    schemas = []

    for schema_id, shifts in known_schemas.items():
        schema_shifts = []
        for shift_id in shifts:
            schema_shifts.append(
                {
                    "days": month_days,
                    "minDaysInRow": 1,
                    "maxDaysInRow": 5,
                    "shiftId": shift_id
                }
            )

        schemas.append(
            {
                "id": schema_id,
                "holidays": {
                    "days": month_days,
                    "minDaysInRow": 1,
                    "maxDaysInRow": 5
                },
                "shifts": schema_shifts
            }
        )

    return schemas

def build_employees(df: pd.DataFrame):

    employees = []

    for _,row in df.iterrows():
        tz = row['Имя']
        if tz not in known_timezones.keys():
            print(f'Unkown timezone: {tz}')
            break;

        schema_name = row['Схема 1']
        if schema_name not in known_schemas.keys():
            print(f'Unkown schema: {schema_name}')
            break;

        employees.append(
            {
                "id": row['Фамилия'],
                "utc": known_timezones[tz],
                "minWorkingHours": 176,
                "maxWorkingHours": 176,
                "schemas": [schema_name]
            }
        )

    return employees

# 3. create output object

request = {
    "campainUtc": 3,
    "activities": build_activities(),
    "shifts": build_shifts(),
    "schemas": build_schemas(),
    "employees": build_employees(df)
}

# 4. store it as a file

_file_name = '../../tmp/data.json'
print(f"Writing to file: {_file_name}")

# Define file to write to and 'w' for write option -> json.dump()
with codecs.open(_file_name, 'w', encoding='utf-8') as json_file:
    json.dump(request, json_file, ensure_ascii=False)

print('Done!')