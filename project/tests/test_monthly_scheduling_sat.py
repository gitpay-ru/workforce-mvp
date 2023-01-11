import sys

from project.models.monthly_scheduling_sat import MonthlyShiftScheduling, filter_none, replace_none_with_v


def test_happy_path_1_day():
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=20,
        num_intervals=_1d_intervals,
        intervals_demand=[3 for _ in range(_1d_intervals)],
    )

    model.solve()


def test_happy_path_1_week():
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=20,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[3 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_oom_1_week_350employees():
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=350,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[10 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_oom_1_month_350employees():
    _days = 31
    _intervals = _days * int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=350,
        num_intervals=_intervals,
        intervals_demand=[10 for _ in range(_intervals)],
    )

    model.solve()


def test_1_day_3_employees():
    _days = 1
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=3,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_nonfeasible_1_day():
    _days = 1
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=1,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_3_days_3_employees():
    _days = 3
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=3,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_6_days_3_emplyees():
    _days = 6
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=3,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_7_days_6_employees():
    # starting from a week a new constraint to be applied - min/max working hours
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=6,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_7_days_6_employees_9h_12h_shifts():
    # starting from a week a new constraint to be applied - min/max working hours
    _days = 7
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=6,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts={
            0: [1],  # 9h day
            1: [3],  # 9h night
            2: [2],  # 12h day
            3: [4],  # 12h night
        }
    )

    model.solve()


def test_feasible_light_1_month():
    # starting from a week a new constraint to be applied - min/max working hours
    _days = 31
    _1d_intervals = int(24 * 60 / 15)

    model = MonthlyShiftScheduling(
        num_employees=6,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
    )

    model.solve()


def test_filter_none_1():
    a = [1, 2, 3]
    a_filtered = filter_none(a)

    expected = [1, 2, 3]

    # check no replacements
    assert len(a_filtered) == len(expected)
    assert all([a == b for a, b in zip(a_filtered, expected)])

    print(all([a == b for a, b in zip(a_filtered, expected)]))

def test_filter_none_2():
    b = [1, None, 2, 3, None]
    b_filtered = filter_none(b)

    expected = [1, 2, 3]

    # check filterings are applied
    assert len(b_filtered) == len(expected)
    assert all([a == b for a, b in zip(b_filtered, expected)])

    print(all([a == b for a, b in zip(b_filtered, expected)]))

def test_replace_none_with_v_1():
    a = [1, 2, 3]
    a_replaced = replace_none_with_v(a, 0)
    expected = [1, 2, 3]

    # check no replacements
    assert len(a_replaced) == len(expected)
    assert all([a == b for a, b in zip(a_replaced, expected)])
    print(all([a == b for a, b in zip(a_replaced, expected)]))

def test_replace_none_with_v_2():
    b = [1, None, 2, 3, None]
    b_replaced = replace_none_with_v(b, 0)
    expected = [1, 0, 2, 3, 0]

    # check filterings are applied
    assert len(b_replaced) == len(expected)
    assert all([a == b for a, b in zip(b_replaced, expected)])
    print(all([a == b for a, b in zip(b_replaced, expected)]))

