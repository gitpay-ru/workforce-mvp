from google.protobuf import text_format
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
  If forbids sum < hard_min or > hard_max.
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
    sum_var = model.NewIntVar(hard_min, hard_max, '')
    # This adds the hard constraints on the sum.
    model.Add(sum_var == sum(works))

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


INTERVALS_PER_HOUR = 4
# the model tends to minimize the penalties
# => for the desired intervals, we minimize it by setting proper weight
DEFAULT_REQUEST_WEIGHT = -2
# for the stop list => if it matches (i-employee will be set to the interval) =>
# model will get penalty (weight=4) => model would decide to not to make this assignment
DEFAULT_STOP_LIST_WEIGHT = 4;

class MonthlyShiftScheduling():
    def __init__(self, num_employees: int,
                 num_intervals: int,
                 intervals_demand: list,
                 fixed_assignments: list,
                 employee_requests: list,
                 employee_stop_list: list,
                 employee_schemas: list,
                 num_days: int,
                 periods: int,
                 shifts_coverage: dict,
                 required_resources: list,
                 max_period_concurrency: int,
                 max_shift_concurrency: int,
                 max_search_time: float = 120.0,
                 num_search_workers=2,
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

        num_intervals_per_day = INTERVALS_PER_HOUR * 24;
        self.num_days = num_intervals / num_intervals_per_day

        self.num_employees = num_employees
        self.intervals_demand = intervals_demand
        self.fixed_assignments = fixed_assignments
        self.employee_requests = employee_requests
        self.employee_stop_list = employee_stop_list

    def solve(self):
        """Solves the shift scheduling problem."""

        # Fixed assignment: (employee, shift, day).
        # This fixes the first 2 days of the schedule.
        fixed_assignments = [
            (0, 0, 0),
            (1, 0, 0),
            (2, 1, 0),
            (3, 1, 0),
            (4, 2, 0),
            (5, 2, 0),
            (6, 2, 3),
            (7, 3, 0),
            (0, 1, 1),
            (1, 1, 1),
            (2, 2, 1),
            (3, 2, 1),
            (4, 2, 1),
            (5, 0, 1),
            (6, 0, 1),
            (7, 3, 1),
        ]

        # Request: (employee, day, interval, weight)
        # A negative weight indicates that the employee desire this assignment.
        requests = []

        # Add working request to the overall batch of requests
        for (e, i) in self.employee_requests:
            for d in range(self.num_days):
                requests.append((e, d, i, DEFAULT_REQUEST_WEIGHT))

        # Add anti-requests to the overall request list
        for (e, i) in self.employee_stop_list:
            for d in range(self.num_days):
                requests.append((e, d, i, DEFAULT_STOP_LIST_WEIGHT))

        # Shift constraints on continuous sequence :
        #     (shift, hard_min, soft_min, min_penalty,
        #             soft_max, hard_max, max_penalty)
        shift_constraints = [
            # One or two consecutive days of rest, this is a hard constraint.
            (0, 1, 1, 0, 2, 2, 0),
            # between 2 and 3 consecutive days of night shifts, 1 and 4 are
            # possible but penalized.
            (3, 1, 2, 20, 3, 4, 5),
        ]

        # Weekly sum constraints on shifts days:
        #     (shift, hard_min, soft_min, min_penalty,
        #             soft_max, hard_max, max_penalty)
        weekly_sum_constraints = [
            # Constraints on rests per week.
            (0, 1, 2, 7, 2, 3, 4),
            # At least 1 night shift per week (penalized). At most 4 (hard).
            (3, 0, 1, 3, 4, 4, 0),
        ]

        # Penalized transitions:
        #     (previous_shift, next_shift, penalty (0 means forbidden))
        penalized_transitions = [
            # Afternoon to night has a penalty of 4.
            (2, 3, 4),
            # Night to morning is forbidden.
            (3, 1, 0),
        ]

        # daily demands for work shifts (morning, afternon, night) for each day
        # of the week starting on Monday.
        weekly_cover_demands = [
            (2, 3, 1),  # Monday
            (2, 3, 1),  # Tuesday
            (2, 2, 2),  # Wednesday
            (2, 3, 1),  # Thursday
            (2, 2, 2),  # Friday
            (1, 2, 3),  # Saturday
            (1, 3, 1),  # Sunday
        ]

        # Penalty for exceeding the cover constraint per shift type.
        excess_cover_penalties = (2, 2, 5)

        num_days = num_weeks * 7
        num_shifts = len(shifts)

        model = cp_model.CpModel()

        work = {}
        for e in range(num_employees):
            for s in range(num_shifts):
                for d in range(num_days):
                    work[e, s, d] = model.NewBoolVar('work%i_%i_%i' % (e, s, d))

        # Linear terms of the objective in a minimization context.
        obj_int_vars = []
        obj_int_coeffs = []
        obj_bool_vars = []
        obj_bool_coeffs = []

        # Exactly one shift per day.
        for e in range(num_employees):
            for d in range(num_days):
                model.AddExactlyOne(work[e, s, d] for s in range(num_shifts))

        # Fixed assignments.
        for e, s, d in fixed_assignments:
            model.Add(work[e, s, d] == 1)

        # Employee requests
        for e, s, d, w in requests:
            obj_bool_vars.append(work[e, s, d])
            obj_bool_coeffs.append(w)

        # Shift constraints
        for ct in shift_constraints:
            shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
            for e in range(num_employees):
                works = [work[e, shift, d] for d in range(num_days)]
                variables, coeffs = add_soft_sequence_constraint(
                    model, works, hard_min, soft_min, min_cost, soft_max, hard_max,
                    max_cost,
                    'shift_constraint(employee %i, shift %i)' % (e, shift))
                obj_bool_vars.extend(variables)
                obj_bool_coeffs.extend(coeffs)

        # Weekly sum constraints
        for ct in weekly_sum_constraints:
            shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
            for e in range(num_employees):
                for w in range(num_weeks):
                    works = [work[e, shift, d + w * 7] for d in range(7)]
                    variables, coeffs = add_soft_sum_constraint(
                        model, works, hard_min, soft_min, min_cost, soft_max,
                        hard_max, max_cost,
                        'weekly_sum_constraint(employee %i, shift %i, week %i)' %
                        (e, shift, w))
                    obj_int_vars.extend(variables)
                    obj_int_coeffs.extend(coeffs)

        # Penalized transitions
        for previous_shift, next_shift, cost in penalized_transitions:
            for e in range(num_employees):
                for d in range(num_days - 1):
                    transition = [
                        work[e, previous_shift, d].Not(), work[e, next_shift,
                                                               d + 1].Not()
                    ]
                    if cost == 0:
                        model.AddBoolOr(transition)
                    else:
                        trans_var = model.NewBoolVar(
                            'transition (employee=%i, day=%i)' % (e, d))
                        transition.append(trans_var)
                        model.AddBoolOr(transition)
                        obj_bool_vars.append(trans_var)
                        obj_bool_coeffs.append(cost)

        # Cover constraints
        for s in range(1, num_shifts):
            for w in range(num_weeks):
                for d in range(7):
                    works = [work[e, s, w * 7 + d] for e in range(num_employees)]
                    # Ignore Off shift.
                    min_demand = weekly_cover_demands[d][s - 1]
                    worked = model.NewIntVar(min_demand, num_employees, '')
                    model.Add(worked == sum(works))
                    over_penalty = excess_cover_penalties[s - 1]
                    if over_penalty > 0:
                        name = 'excess_demand(shift=%i, week=%i, day=%i)' % (s, w,
                                                                             d)
                        excess = model.NewIntVar(0, num_employees - min_demand,
                                                 name)
                        model.Add(excess == worked - min_demand)
                        obj_int_vars.append(excess)
                        obj_int_coeffs.append(over_penalty)

        # Objective
        model.Minimize(
            sum(obj_bool_vars[i] * obj_bool_coeffs[i]
                for i in range(len(obj_bool_vars))) +
            sum(obj_int_vars[i] * obj_int_coeffs[i]
                for i in range(len(obj_int_vars))))

        if output_proto:
            print('Writing proto to %s' % output_proto)
            with open(output_proto, 'w') as text_file:
                text_file.write(str(model))

        # Solve the model.
        solver = cp_model.CpSolver()
        if params:
            text_format.Parse(params, solver.parameters)
        solution_printer = cp_model.ObjectiveSolutionPrinter()
        status = solver.Solve(model, solution_printer)

        # Print solution.
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print()

            header0 = "Days        ";
            for d in range(num_days):
                # print '15' in a header
                # *4, because interval = 15 min
                header0 += f'Day {d+1}'.zfill(4*24)
            print(header0)

            header = "W\\S         ";
            for i in range(num_days*24):
                h = i % 24;
                header += f'{h+1}h'.zfill(4);
            print(header)

            onlyRestWithoutWork = 0
            for e in range(num_employees):
                scheduleRow = ''

                for d in range(num_days):
                    for i int range(num_intervals_per_day):
                        if solver.BooleanValue(work[e, d, i, 0]):
                            if solver.BooleanValue(work[e, d, i, 1]):
                                scheduleRow += '□';
                            else:
                                scheduleRow += '■';
                        else:
                            if solver.BooleanValue(work[e, d, i, 1]:
                                onlyRestWithoutWork++
                            scheduleRow += '-';

                print(f'worker {i:03d}: {scheduleRow}')

            print()
            print(f"Only rest, without work: {onlyRestWithoutWork}")
            print('Penalties:')
            for i, var in enumerate(obj_bool_vars):
                if solver.BooleanValue(var):
                    penalty = obj_bool_coeffs[i]
                    if penalty > 0:
                        print('  %s violated, penalty=%i' % (var.Name(), penalty))
                    else:
                        print('  %s fulfilled, gain=%i' % (var.Name(), -penalty))

            for i, var in enumerate(obj_int_vars):
                if solver.Value(var) > 0:
                    print('  %s violated by %i, linear penalty=%i' %
                          (var.Name(), solver.Value(var), obj_int_coeffs[i]))

            print()
            print('Statistics')
            print(f'  - status          : {solver.StatusName(status)}')
            print(f'  - conflicts       : {solver.NumConflicts()}')
            print(f'  - branches        : {solver.NumBranches()}')
            print(f'  - wall time       : {solver.WallTime()} s')
        else:
            print("Solution is not feasible")