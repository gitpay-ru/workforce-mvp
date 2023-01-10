import sys

from project.models.monthly_scheduling_sat import MonthlyShiftScheduling


def test_happy_path_1_day():
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=20,
        num_intervals=_1d_intervals,
        intervals_demand=[3 for _ in range(_1d_intervals)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_happy_path_3_days():
    _days = 3
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=20,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[3 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_happy_path_1_week():
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=20,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[3 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_oom_1_week_350employees():
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=350,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[10 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_happy_path_1_month():
    _days = 31
    _intervals = _days * int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=20,
        num_intervals=_intervals,
        intervals_demand=[3 for _ in range(_intervals)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_oom_1_month_350employees():
    _days = 31
    _intervals = _days * int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=350,
        num_intervals=_intervals,
        intervals_demand=[10 for _ in range(_intervals)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()


def test_feasible_light_1_day():
    _days = 1
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=3,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[1 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_nonfeasible_light_1_day():
    _days = 1
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=1,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_feasible_light_3_days():
    _days = 3
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=3,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[1 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_feasible_light_6_days():
    _days = 6
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=3,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[1 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_feasible_light_7_days():
    # starting from a week a new constraint to be applied - min/max working hours
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=6,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[1 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

def test_feasible_light_1_month():
    # starting from a week a new constraint to be applied - min/max working hours
    _days = 31
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=6,
        num_intervals=_1d_intervals*_days,
        intervals_demand=[1 for _ in range(_1d_intervals*_days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_schemas=[]
    )

    model.solve()

