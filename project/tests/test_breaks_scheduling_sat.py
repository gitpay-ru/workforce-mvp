from project.models.breaks_scheduling_sat import BreaksScheduling


def test_1_day_3_employee():
    _days = 1
    _1h_interval = int(1 * 60 / 15)
    _9h_intervals = 9*_1h_interval
    _1d_intervals = 24 * _1h_interval

    # employee shifts
    calendar = {
        0: [
            (8 * _1h_interval, 17 * _1h_interval)
        ],
        1: [
            (9 * _1h_interval, 18 * _1h_interval)
        ],
        2: [
            (12 * _1h_interval, 21 * _1h_interval)
        ],
    }

    # break rules
    breaks = [
        # 1 lunch break - 30 mins
        (1, 2),
        # 2 small breaks by 15 mins
        (2, 1)
    ]

    model = BreaksScheduling(
        num_employees=3,
        num_intervals=_1d_intervals * _days,
        intervals_demand=[1 for _ in range(_1d_intervals * _days)],
        employee_calendar=calendar,
        breaks=breaks
    )

    model.solve()