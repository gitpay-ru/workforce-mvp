import math

from ortools.sat.python import cp_model


# https://github.com/google/or-tools/blob/master/examples/python/shift_scheduling_sat.py
def negated_bounded_span(works, start, length):
    """Filters an isolated sub-sequence of variables assined to True.
  Extract the span of Boolean variables [start, start + length), negate them,
  and if there is variables to the left/right of this span, surround the span by
  them in non negated form.
  Args:
    works: a list of variables to extract the span from.
    start: the start to the span.
    length: the length of the span.
  Returns:
    a list of variables which conjunction will be false if the sub-list is
    assigned to True, and correctly bounded by variables assigned to False,
    or by the start or end of works.
  """
    sequence = []
    # Left border (start of works, or works[start - 1])
    if start > 0:
        sequence.append(works[start - 1])
    for i in range(length):
        sequence.append(works[start + i].Not())
    # Right border (end of works or works[start + length])
    if start + length < len(works):
        sequence.append(works[start + length])
    return sequence


def add_soft_sequence_constraint(model, works, hard_min, soft_min, min_cost,
                                 soft_max, hard_max, max_cost, prefix):
    """Sequence constraint on true variables with soft and hard bounds.
  This constraint look at every maximal contiguous sequence of variables
  assigned to true. If forbids sequence of length < hard_min or > hard_max.
  Then it creates penalty terms if the length is < soft_min or > soft_max.
  Args:
    model: the sequence constraint is built on this model.
    works: a list of Boolean variables.
    hard_min: any sequence of true variables must have a length of at least
      hard_min.
    soft_min: any sequence should have a length of at least soft_min, or a
      linear penalty on the delta will be added to the objective.
    min_cost: the coefficient of the linear penalty if the length is less than
      soft_min.
    soft_max: any sequence should have a length of at most soft_max, or a linear
      penalty on the delta will be added to the objective.
    hard_max: any sequence of true variables must have a length of at most
      hard_max.
    max_cost: the coefficient of the linear penalty if the length is more than
      soft_max.
    prefix: a base name for penalty literals.
  Returns:
    a tuple (variables_list, coefficient_list) containing the different
    penalties created by the sequence constraint.
  """
    cost_literals = []
    cost_coefficients = []

    # Forbid sequences that are too short.
    for length in range(1, hard_min):
        for start in range(len(works) - length + 1):
            model.AddBoolOr(negated_bounded_span(works, start, length))

    # Penalize sequences that are below the soft limit.
    if min_cost > 0:
        for length in range(hard_min, soft_min):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = ': under_span(start=%i, length=%i)' % (start, length)
                lit = model.NewBoolVar(prefix + name)
                span.append(lit)
                model.AddBoolOr(span)
                cost_literals.append(lit)
                # We filter exactly the sequence with a short length.
                # The penalty is proportional to the delta with soft_min.
                cost_coefficients.append(min_cost * (soft_min - length))

    # Penalize sequences that are above the soft limit.
    if max_cost > 0:
        for length in range(soft_max + 1, hard_max + 1):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = ': over_span(start=%i, length=%i)' % (start, length)
                lit = model.NewBoolVar(prefix + name)
                span.append(lit)
                model.AddBoolOr(span)
                cost_literals.append(lit)
                # Cost paid is max_cost * excess length.
                cost_coefficients.append(max_cost * (length - soft_max))

    # Just forbid any sequence of true variables with length hard_max + 1
    for start in range(len(works) - hard_max):
        model.AddBoolOr(
            [works[i].Not() for i in range(start, start + hard_max + 1)])

    return cost_literals, cost_coefficients


def add_soft_sum_constraint(model, works, hard_min, soft_min, min_cost,
                            soft_max, hard_max, max_cost, prefix):
    """Sum constraint with soft and hard bounds.
  This constraint counts the variables assigned to true from works.
  It forbids sum < hard_min or > hard_max.
  Then it creates penalty terms if the sum is < soft_min or > soft_max.
  Args:
    model: the sequence constraint is built on this model.
    works: a list of Boolean variables.
    hard_min: any sequence of true variables must have a sum of at least
      hard_min.
    soft_min: any sequence should have a sum of at least soft_min, or a linear
      penalty on the delta will be added to the objective.
    min_cost: the coefficient of the linear penalty if the sum is less than
      soft_min.
    soft_max: any sequence should have a sum of at most soft_max, or a linear
      penalty on the delta will be added to the objective.
    hard_max: any sequence of true variables must have a sum of at most
      hard_max.
    max_cost: the coefficient of the linear penalty if the sum is more than
      soft_max.
    prefix: a base name for penalty variables.
  Returns:
    a tuple (variables_list, coefficient_list) containing the different
    penalties created by the sequence constraint.
  """
    cost_variables = []
    cost_coefficients = []
    sum_var = model.NewIntVar(hard_min, hard_max, prefix)
    # This adds the hard constraints on the sum.
    model.Add(sum_var == sum(works))

    cost_variables.append(sum_var)
    cost_coefficients.append(0.0)

    # Penalize sums below the soft_min target.
    if soft_min > hard_min and min_cost > 0:
        delta = model.NewIntVar(-len(works), len(works), '')
        model.Add(delta == soft_min - sum_var)
        # TODO(user): Compare efficiency with only excess >= soft_min - sum_var.
        excess = model.NewIntVar(0, 7, prefix + ': under_sum')
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(min_cost)

    # Penalize sums above the soft_max target.
    if soft_max < hard_max and max_cost > 0:
        delta = model.NewIntVar(-7, 7, '')
        model.Add(delta == sum_var - soft_max)
        excess = model.NewIntVar(0, 7, prefix + ': over_sum')
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(max_cost)

    return cost_variables, cost_coefficients


def add_min_sequence_length_constraint(model, works, hard_min):
    """Sequence constraint on true variables with min hard bound.
  This constraint look at every maximal contiguous sequence of variables
  assigned to true. If forbids sequence of length < hard_min.
  Args:
    model: the sequence constraint is built on this model.
    works: a list of Boolean variables.
    hard_min: any sequence of true variables must have a length of at least
      hard_min.
  """
    # Forbid sequences that are too short.
    for length in range(1, hard_min):
        for start in range(len(works) - length + 1):
            model.AddBoolOr(negated_bounded_span(works, start, length))


# the model tends to minimize the penalties
# => for the desired intervals, we minimize it by setting proper weight
DEFAULT_REQUEST_WEIGHT = -2

# for the stop list => if it matches (i-employee will be set to the interval) =>
# model will get penalty (weight=4) => model would decide to not to make this assignment
DEFAULT_STOP_LIST_WEIGHT = 4

# Max working hours per day
MAX_WORKING_HOURS = 9

INTERVALS_PER_HOUR = 4

_shapes_resting = [u'-', u'+']
_shapes_9h = [u'□', u'■']
_shapes_12h = [u'○', u'●']
_shapes_unknown = 'x'

class MonthlyShiftScheduling:
    def __init__(self, num_employees: int,
                 num_intervals: int,
                 intervals_demand: list,
                 fixed_assignments: list,
                 employee_requests: list,
                 employee_stop_list: list,
                 employee_schemas: list,
                 *args, **kwargs):
        """
        The "optimal" criteria is defined as the number of resources per shift
        that minimize the total absolute difference between the required resources
        per period and the actual scheduling found by the solver

        Parameters
        ----------

        num_days: int,
            Number of days needed to schedule
        periods: int,
            Number of working periods in a day
        shifts_coverage: dict,
            dict with structure {"shift_name": "shift_array"} where "shift_array" is an array of size [periods] (p), 1 if shift covers period p, 0 otherwise
        required_resources: list,
            Array of size [days, periods]
        max_period_concurrency: int,
            Maximum resources that are allowed to shift in any period and day
        max_shift_concurrency: int,
            Number of maximum allowed resources in the same shift
        max_search_time: float, default = 240
            Maximum time in seconds to search for a solution
        num_search_workers: int, default = 2
            Number of workers to search for a solution
        """

        self.shapes = [
            _shapes_resting,  # 0 = resting
            _shapes_9h,       # 1 = 9h working schemas
            _shapes_12h,      # 2 = 12h working schemas
        ]
        self.num_shapes = len(self.shapes)
        self.num_types = len(self.shapes[0])

        self.num_intervals_per_day = INTERVALS_PER_HOUR * 24;
        self.num_days = int(num_intervals / self.num_intervals_per_day)

        self.num_employees = num_employees
        self.intervals_demand = intervals_demand
        self.fixed_assignments = fixed_assignments
        self.employee_requests = employee_requests
        self.employee_stop_list = employee_stop_list

    def solve(self):

        """Solves the shift scheduling problem."""

        # Request: (employee, day, interval, weight)
        # A negative weight indicates that the employee desire this assignment.
        requests = []

        # 1. Requests
        # Add working request to the overall batch of requests
        for (e, i) in self.employee_requests:
            for d in range(self.num_days):
                requests.append((e, d, i, DEFAULT_REQUEST_WEIGHT))

        # Add anti-requests to the overall request list
        for (e, i) in self.employee_stop_list:
            for d in range(self.num_days):
                requests.append((e, d, i, DEFAULT_STOP_LIST_WEIGHT))

        _9h_interval = MAX_WORKING_HOURS * INTERVALS_PER_HOUR
        _1h_interval = 1 * INTERVALS_PER_HOUR
        _12h_interval = 12 * INTERVALS_PER_HOUR
        _total_max_interval = self.num_days * 24 * INTERVALS_PER_HOUR

        # 2.1 Shift constraints on continuous sequence :
        #     (shape_type, work_type, hard_min, soft_min, min_penalty, soft_max, hard_max, max_penalty)
        shift_constraints = [
            # One or two consecutive days of rest, this is a hard constraint.
            # (0, 1, 1, 0, 2, 2, 0),
            # between 2 and 3 consecutive days of night shifts, 1 and 4 are
            # possible but penalized.
            # (3, 1, 2, 20, 3, 4, 5),

            # works no more than 8 intervals.
            # (1, 8, 1, 8, 8, 0),

            # 9h work, 9h, 9h, 1, 9h, 9h, 0
            (1, 0, _9h_interval, _9h_interval, 0, _9h_interval, _9h_interval, 0),

            # 9h rest, 1, 1, 1, 9h, 9h, 0
            (1, 1, 1, 1, 1, 2, _9h_interval, 2),

            # 12h work, 12h, 12h, 1, 12h, 12h, 0
            (2, 0, _12h_interval, _12h_interval, 0, _12h_interval, _12h_interval, 0),

            # 12h rest, 1.5 hrs
            (2, 1, 1, 1, 1, 2, _12h_interval, 2),
        ]

        # 2.2 min length constrains
        #     (shape_type, work_type, min_length
        min_lenght_constrains = [
            # rest should be at least 12 hours
            (0, 0, _12h_interval)
        ]

        # 3. Weekly sum constraints on shifts days:
        #    (shape_type, work_type, hard_min, soft_min, min_penalty, soft_max, hard_max, max_penalty)
        weekly_sum_constraints = [
            # Constraints on rests per week.
            # (0, 1, 2, 7, 2, 3, 4),
            # At least 1 night shift per week (penalized). At most 4 (hard).
            # (3, 0, 1, 3, 4, 4, 0),
            # 9h 4-6 working days per week, (?) todo: if less than 5 days -> penalty, <4 & >6 are not allowed
            (1, 0, 4 * _9h_interval, 4 * _9h_interval, 1, 6 * _9h_interval, 6 * _9h_interval, 0),
        ]

        # 4. Penalized transitions:
        #     (previous_shift, next_shift, penalty (0 means forbidden))
        penalized_transitions = [
            # 9h to 12h is forbidden to morning is forbidden.
            (1, 2, 0),
            (2, 1, 0),
        ]

        # daily demands for work shifts (morning, afternon, night) for each day
        # of the week starting on Monday.
        # weekly_cover_demands = [
        #     (2, 3, 1),  # Monday
        #     (2, 3, 1),  # Tuesday
        #     (2, 2, 2),  # Wednesday
        #     (2, 3, 1),  # Thursday
        #     (2, 2, 2),  # Friday
        #     (1, 2, 3),  # Saturday
        #     (1, 3, 1),  # Sunday
        # ]

        # 5. Penalty for exceeding the cover constraint per shift type.
        # excess_cover_penalties = (2, 2, 5)

        model = cp_model.CpModel()

        # work: employees * days * intervals_per_day * shape_type * type_of_work (working|non-working)
        work = {}
        for e in range(self.num_employees):
            for d in range(self.num_days):
                for i in range(self.num_intervals_per_day):
                    for s in range(self.num_shapes):
                        for t in range(self.num_types):
                            work[e, d, i, s, t] = model.NewBoolVar(f'work_e{e}_d{d}_i{i}_s{s}_t{t}')

        # Linear terms of the objective in a minimization context.
        obj_int_vars = []
        obj_int_coeffs = []
        obj_bool_vars = []
        obj_bool_coeffs = []

        # Exactly one shift per day.
        # for e in range(num_employees):
        #     for d in range(num_days):
        #         model.AddExactlyOne(work[e, s, d] for s in range(num_shifts))

        # Exactly 9h per day and at least 1 hr of breaks
        # This is not needed because sequance constraints are applied
        # for e in range(self.num_employees):
        #     for d in range(self.num_days):
        #         #todo: generalize as daily_sum_costraints
        #         temp_working = [work[e, d, i, 1, 0] for i in range(self.num_intervals_per_day)]
        #         temp_breaks = [work[e, d, i, 1, 1] for i in range(self.num_intervals_per_day)]
        #
        #         model.Add(sum(temp_working) == _9h_interval)
        #         model.Add(sum(temp_breaks) >= _1h_interval)

        # Fixed assignments.
        # for e, s, d in fixed_assignments:
        #     model.Add(work[e, s, d] == 1)

        # Employee requests
        # this covers both positive & negative requests, 9h requests by default
        for (e, d, i, w) in requests:
            obj_bool_vars.append(work[e, d, i, 1, 0])
            # 0 - we ignore last dimension, as it distinguishes only working/resting
            obj_bool_coeffs.append(w)

        # Shift sequence constraints for all employees are same (per day)
        # for ct in shift_constraints:
        #     work_type, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        #     for e in range(self.num_employees):
        #         for d in range(self.num_days):
        #             works = [work[e, d, i, work_type] for i in range(self.num_intervals_per_day)]
        #
        #             variables, coeffs = add_soft_sequence_constraint(
        #                 model, works,
        #                 hard_min, soft_min, min_cost, soft_max, hard_max, max_cost,
        #                 f'shift_constraint(employee {e}, day {d}, work_type {work_type})')
        #
        #             obj_bool_vars.extend(variables)
        #             obj_bool_coeffs.extend(coeffs)

        # Shift sequence constraints -- flattern all intervals
        for ct in shift_constraints:
            shape_type, work_type, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
            for e in range(self.num_employees):
                works = [work[e, d, i, shape_type, work_type] for d in range(self.num_days) for i in
                         range(self.num_intervals_per_day)]

                variables, coeffs = add_soft_sequence_constraint(
                    model, works,
                    hard_min, soft_min, min_cost, soft_max, hard_max, max_cost,
                    f'shift_constraint(employee {e}, shape_type {shape_type}, work_type {work_type})')

                obj_bool_vars.extend(variables)
                obj_bool_coeffs.extend(coeffs)

        # Minimum length constraints on flattern intervals
        for ct in min_lenght_constrains:
            shape_type, work_type, hard_min = ct
            virtual_sequence = [model.NewConstant(True) for _ in range(hard_min)]
            for e in range(self.num_employees):
                works = [work[e, d, i, shape_type, work_type] for d in range(self.num_days) for i in
                         range(self.num_intervals_per_day)]

                all = virtual_sequence + works + virtual_sequence
                add_min_sequence_length_constraint(model, all, hard_min)



        # Weekly sum constraints
        # num_weeks = math.ceil(self.num_days / 7)
        # calculate whole weeks only
        num_weeks = int(self.num_days / 7)
        for ct in weekly_sum_constraints:
            shape_type, work_type, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
            for e in range(self.num_employees):
                for w in range(num_weeks):
                    works = [work[e, dw + w * 7, i, shape_type, work_type] for dw in range(7) for i in
                             range(self.num_intervals_per_day)]
                    variables, coeffs = add_soft_sum_constraint(
                        model, works,
                        hard_min, soft_min, min_cost, soft_max, hard_max, max_cost,
                        f'weekly_sum_constraint(employee {e}, week {w}, shape_type {shape_type}, work_type {work_type})')

                    obj_int_vars.extend(variables)
                    obj_int_coeffs.extend(coeffs)

        # Penalized transitions
        for previous_shift, next_shift, cost in penalized_transitions:
            for e in range(self.num_employees):
                for d in range(self.num_days):
                    for i in range(self.num_intervals_per_day - 1):
                        transition = [
                            work[e, d, i, previous_shift, 0].Not(),
                            work[e, d, i+1, next_shift, 0].Not()
                        ]

                        if cost == 0:
                            model.AddBoolOr(transition)
                        else:
                            trans_var = model.NewBoolVar(
                                f'transition (employee={e}, day={d}, intertval={i}, previous={previous_shift}, next={next_shift})')
                            transition.append(trans_var)
                            model.AddBoolOr(transition)
                            obj_bool_vars.append(trans_var)
                            obj_bool_coeffs.append(cost)

        # if Employee is resting -> should consider work this time
        # otherwise rest dimension & work dimension would mix
        for e in range(self.num_employees):
            for d in range(self.num_days):
                for i in range(self.num_intervals_per_day):
                    for s in range(self.num_shapes):
                        model.AddBoolAnd([work[e, d, i, s, 0], work[e, d, i, s, 1]]).OnlyEnforceIf(work[e, d, i, s, 1])

        # Cover constraints
        # for s in range(1, num_shifts):
        #     for w in range(num_weeks):
        #         for d in range(7):
        #             works = [work[e, s, w * 7 + d] for e in range(num_employees)]
        #             # Ignore Off shift.
        #             min_demand = weekly_cover_demands[d][s - 1]
        #             worked = model.NewIntVar(min_demand, num_employees, '')
        #             model.Add(worked == sum(works))
        #             over_penalty = excess_cover_penalties[s - 1]
        #             if over_penalty > 0:
        #                 name = 'excess_demand(shift=%i, week=%i, day=%i)' % (s, w,
        #                                                                      d)
        #                 excess = model.NewIntVar(0, num_employees - min_demand,
        #                                          name)
        #                 model.Add(excess == worked - min_demand)
        #                 obj_int_vars.append(excess)
        #                 obj_int_coeffs.append(over_penalty)

        # Intervals demand coverage
        for d in range(self.num_days):
            for i in range(self.num_intervals_per_day):
                works = [work[e, d, i, 1, 0] for e in range(self.num_employees)]
                breaks = [work[e, d, i, 1, 1] for e in range(self.num_employees)]

                min_demand = self.intervals_demand[d * self.num_intervals_per_day + i]
                worked = model.NewIntVar(min_demand, self.num_employees, f'demand (day {d}, interval {i})')
                model.Add(worked == (sum(works) - sum(breaks)))

        # Employee either is resting or is working
        for e in range(self.num_employees):
            for d in range(self.num_days):
                for i in range(self.num_intervals_per_day):
                    works = [work[e, d, i, s, 0] for s in range(self.num_shapes)]
                    model.AddExactlyOne(works)

        # Objective
        model.Minimize(
            sum(obj_bool_vars[i] * obj_bool_coeffs[i] for i in range(len(obj_bool_vars))) +
            sum(obj_int_vars[i] * obj_int_coeffs[i] for i in range(len(obj_int_vars)))
        )

        # Solve the model.
        solver = cp_model.CpSolver()
        solution_printer = cp_model.ObjectiveSolutionPrinter()
        solver.parameters.max_time_in_seconds = 3600.0

        status = solver.Solve(model, solution_printer)

        # Print solution.
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print()

            header0 = "Days        ";
            for d in range(self.num_days):
                # print '15' in a header
                # *4, because interval = 15 min
                header0 += f'Day {d + 1}'.rjust(4 * 24)
            print(header0)

            header = "W\\S         ";
            for i in range(self.num_days * 24):
                h = i % 24;
                header += f'{h + 1}h'.rjust(4);
            print(header)

            #onlyRestWithoutWork = 0
            for e in range(self.num_employees):
                scheduleRow = ''

                for d in range(self.num_days):
                    for i in range(self.num_intervals_per_day):

                        if solver.BooleanValue(work[e, d, i, 0, 0]):
                            scheduleRow += _shapes_resting[0]
                        elif solver.BooleanValue(work[e, d, i, 0, 1]):
                            scheduleRow += _shapes_resting[1]
                        elif solver.BooleanValue(work[e, d, i, 1, 0]):
                            if solver.BooleanValue(work[e, d, i, 1, 1]):
                                scheduleRow += _shapes_9h[0]
                            else:
                                scheduleRow += _shapes_9h[1]
                        elif solver.BooleanValue(work[e, d, i, 2, 0]):
                            if solver.BooleanValue(work[e, d, i, 2, 1]):
                                scheduleRow += _shapes_12h[0]
                            else:
                                scheduleRow += _shapes_12h[1]
                        else:
                            scheduleRow += _shapes_unknown
                print(f'worker {e:03d}: {scheduleRow}')

            print()
            #print(f"Only rest, without work: {onlyRestWithoutWork}")
            print('Penalties:')
            for i, var in enumerate(obj_bool_vars):
                if solver.BooleanValue(var):
                    penalty = obj_bool_coeffs[i]
                    if penalty > 0:
                        print(f'  {var.Name()} violated, penalty={penalty}')
                    else:
                        print(f'  {var.Name()} fulfilled, gain={-penalty}')

            for i, var in enumerate(obj_int_vars):
                if solver.Value(var) > 0:
                    print(f'  {var.Name()} violated by {solver.Value(var)}, linear penalty={obj_int_coeffs[i]}')

            print()
            print('Statistics')
            print(f'  - status          : {solver.StatusName(status)}')
            print(f'  - conflicts       : {solver.NumConflicts()}')
            print(f'  - branches        : {solver.NumBranches()}')
            print(f'  - wall time       : {solver.WallTime()} s')
        else:
            print("Solution is not feasible")
