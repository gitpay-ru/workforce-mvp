from project.models.monthly_scheduling_sat import MonthlyShiftScheduling


def get_employee_shifts(total):
    p = [0.25, 0.5, 0.75, 1.0]
    v = [int(i*total) for i in p]

    employee_shifts = {}

    for i in range(0, v[0]):
        employee_shifts[i] = [1]

    for i in range(v[0], v[1]):
        employee_shifts[i] = [2]

    for i in range(v[1], v[2]):
        employee_shifts[i] = [3]

    for i in range(v[2], v[3]):
        employee_shifts[i] = [4]

    return employee_shifts


def test_6_days_400_agents_oom():

    _days = 6
    _1d_intervals = int(24 * 60 / 15)

    es = get_employee_shifts(400)

    model = MonthlyShiftScheduling(
        num_employees=len(es.keys()),
        num_intervals=_1d_intervals * _days,
        intervals_demand=[25 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts=es
    )

    model.solve()

def test_6_days_100_agents():

    _days = 6
    _1d_intervals = int(24 * 60 / 15)

    es = get_employee_shifts(100)

    model = MonthlyShiftScheduling(
        num_employees=len(es.keys()),
        num_intervals=_1d_intervals * _days,
        intervals_demand=[10 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts=es
    )

    model.solve()

def test_31_days_100_agents_oom():

    _days = 31
    _1d_intervals = int(24 * 60 / 15)

    es = get_employee_shifts(100)

    model = MonthlyShiftScheduling(
        num_employees=len(es.keys()),
        num_intervals=_1d_intervals * _days,
        intervals_demand=[10 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts=es
    )

    model.solve()

def test_31_days_100_agents_non_strict():

    _days = 31
    _1d_intervals = int(24 * 60 / 15)

    es = get_employee_shifts(100)

    model = MonthlyShiftScheduling(
        num_employees=len(es.keys()),
        num_intervals=_1d_intervals * _days,
        intervals_demand=[10 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts=es,
        strict_mode=False
    )

    model.solve()

def test_31_days_25_agents_non_strict():

    _days = 31
    _1d_intervals = int(24 * 60 / 15)

    es = get_employee_shifts(25)

    model = MonthlyShiftScheduling(
        num_employees=len(es.keys()),
        num_intervals=_1d_intervals * _days,
        intervals_demand=[5 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts=es,
        strict_mode=False
    )

    model.solve()

def test_31_days_40_agents_non_strict():

    _days = 31
    _1d_intervals = int(24 * 60 / 15)

    es = get_employee_shifts(40)

    model = MonthlyShiftScheduling(
        num_employees=len(es.keys()),
        num_intervals=_1d_intervals * _days,
        intervals_demand=[10 for _ in range(_1d_intervals * _days)],
        fixed_assignments=[],
        employee_requests=[],
        employee_stop_list=[],
        employee_shifts=es,
        strict_mode=False
    )

    model.solve()

