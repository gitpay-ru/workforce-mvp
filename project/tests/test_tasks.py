from project.tests.body_for_shifts import maxWorkingHours, minWorkingHours, shifts
from project.tests.body_for_pandas import employeeId, shiftId, id, shiftTimeStart, scheduleTimeStart, scheduleTimeEndStart


def test_actual_time_one_employee_one_month():

    expected_time = 198
    actual_time = employeeId.count() * 3
    assert int(actual_time) == int(expected_time)


def test_first_employees_working_hours():

    actual_time = len(list(shifts)) * 9 - 22
    assert actual_time <= maxWorkingHours
    assert actual_time >= minWorkingHours


def test_shift_time_start():

    assert shiftId == id
    assert shiftTimeStart >= scheduleTimeStart
    assert shiftTimeStart <= scheduleTimeEndStart


