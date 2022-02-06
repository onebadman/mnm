import json
import math

import numpy as np
import pulp

from functools import reduce

from server.meta_data import MetaData, Restriction, OperatorEnum


class Data:
    """
    Класс для промежуточной подготовки исходных данных.
    """

    x: np.ndarray
    y: np.ndarray
    r: float
    delta: float
    omega: np.ndarray
    restriction: Restriction

    def __init__(self, meta_data: MetaData, restriction: Restriction):
        self.restriction = restriction
        self.delta = meta_data.delta
        self._set_y(meta_data)
        self._set_x(meta_data)
        self._calculation_omega()

    def _set_x(self, meta_data: MetaData):
        x = []
        for array in meta_data.load_data:
            index = 0
            arr = []
            for item in array:
                if index != meta_data.var_y - 1:
                    arr.append(item)
                index += 1
            x.append(arr)

        if meta_data.free_chlen:
            _x = []
            for items in x:
                line = [1]
                line.extend(items)
                _x.append(line)
            x = _x

        self.x = np.array(x)

    def _set_y(self, meta_data: MetaData):
        y = []
        for array in meta_data.load_data:
            index = 0
            for item in array:
                if index == meta_data.var_y - 1:
                    y.append(item)
                index += 1

        self.y = np.array(y)

    def _calculation_omega(self):
        omega = []

        n = self.y.size
        for k in range(n - 1):
            for s in range(k + 1, n):
                exp = self.y[k] - self.y[s]
                if exp > 0:
                    omega.append(1)
                elif exp < 0:
                    omega.append(-1)
                else:  # == 0
                    omega.append(0)

        self.omega = np.array(omega)


class Result:
    a: list
    eps: list
    l: list
    yy: list
    e: float
    osp: float
    count_rows: int
    N: float

    def __init__(self):
        self.a = []
        self.eps = []
        self.yy = []

    @staticmethod
    def new_result(data=None):
        result = Result()
        if data is not None:
            result.a = Result.get_value(data, 'a')
            result.eps = Result.get_value(data, 'eps')
            result.yy = Result.get_value(data, 'yy')
            result.e = Result.get_value(data, 'e')
            result.osp = Result.get_value(data, 'osp')
            result.count_rows = Result.get_value(data, 'count_rows')

        return result

    @staticmethod
    def get_value(data, key):
        try:
            return data[key]
        except KeyError:
            return None

    @property
    def m(self) -> float:
        """
        Получает сумму модулей ошибок.
        """
        m = 0
        for item in self.eps:
            m += abs(item)

        return m

    def calculation(self, _x: np.ndarray, _y: np.ndarray):
        """
        Шаблонный метод для вычисления агрегированных результатов вычислений.
        """
        self._set_yy(_x)
        self._epsilon_e(_y)
        self._set_max_rows()
        self._set_osp(_y)

    def _set_osp(self, y: np.ndarray):
        """
        Обобщенный критерий согласованности поведения.
        """
        a = []
        for i in range(len(y) - 1):
            for j in range(i + 1, len(y)):
                a.append(self._sign((self.yy[i] - self.yy[j]) * (y[i] - y[j])))

        self.osp = sum(a)

    def _set_yy(self, _x: np.ndarray):
        self.yy = list(map(lambda item: sum(list(map(lambda x, a: x * a, item, self.a))), _x))

    def _epsilon_e(self, _y: np.ndarray):
        """
        Расчёт оценки ошибки аппроксимации.
        """
        self.e = 1 / len(_y) * reduce(
            lambda x, y: x + y, list(map(lambda x, y: math.fabs((y - x) / y), self.yy, _y))) * 100

    def _set_max_rows(self):
        self.count_rows = max(len(self.a), len(self.yy), len(self.eps))

    def get_max_rows(self):
        return list(map(int, range(self.count_rows)))

    def print(self) -> list:
        arr = []

        for index in range(self.count_rows):
            line = []

            if index < len(self.a):
                line.append(self.a[index])
            else:
                line.append(None)

            if index < len(self.eps):
                line.append(self.eps[index])
            else:
                line.append(None)

            if index == 0:
                line.append(self.e)
            else:
                line.append(None)

            if index == 0:
                line.append(self.osp)
            else:
                line.append(None)

            if index == 0:
                line.append(self.m)
            else:
                line.append(None)

            arr.append(line)
        return arr

    @staticmethod
    def _sign(x) -> int:
        return 1 if x > 0 else 0

    class DataEncoder(json.JSONEncoder):
        """
        Класс кодирует модель MetaData в JSON формат.
        """

        def default(self, obj):
            if isinstance(obj, Result):
                return obj.__dict__
            return json.JSONEncoder.default(self, obj)


class LpSolve:
    """
    Задача линейного программирования.
    """

    data: Data
    result: Result
    _vars: dict
    _problem: pulp.LpProblem

    def __init__(self, data: Data):
        self.data = data
        self.result = Result()
        self._vars = {}
        self._problem = pulp.LpProblem('0', pulp.const.LpMinimize)
        self._create_variable_u_v()
        self._create_variable_beta_gamma()
        self._build_function_c()
        self._build_restrictions()

        self._execute()
        self._set_result()

    def _create_variable_u_v(self):
        for index in range(self.data.y.size):
            var_name_u = f'u{index}'
            var_name_v = f'v{index}'
            self._vars.setdefault(var_name_u, pulp.LpVariable(var_name_u, lowBound=0))
            self._vars.setdefault(var_name_v, pulp.LpVariable(var_name_v, lowBound=0))

    def _create_variable_beta_gamma(self):
        for index in range(len(self.data.x[0])):
            var_name_beta = f'b{index}'
            var_name_gamma = f'g{index}'
            self._vars.setdefault(var_name_beta, pulp.LpVariable(var_name_beta, lowBound=0))
            self._vars.setdefault(var_name_gamma, pulp.LpVariable(var_name_gamma, lowBound=0))

    def _build_function_c(self):
        params = []

        for index in range(self.data.y.size):
            params.append((self._vars.get(f'u{index}'), 1))
        for index in range(self.data.y.size):
            params.append((self._vars.get(f'v{index}'), 1))
        for index in range(len(self.data.x[0])):
            params.append((self._vars.get(f'b{index}'), self.data.delta))
            params.append((self._vars.get(f'g{index}'), self.data.delta))

        self._problem += pulp.LpAffineExpression(params), 'Функция цели'

    def _build_restrictions(self):
        index_restriction = 0
        for index in range(self.data.y.size):
            params = []
            for index_x in range(len(self.data.x[0])):
                params.append((self._vars.get(f'b{index_x}'), self.data.x[index][index_x]))
                params.append((self._vars.get(f'g{index_x}'), -1 * self.data.x[index][index_x]))
            params.append((self._vars.get(f'u{index}'), 1))
            params.append((self._vars.get(f'v{index}'), -1))

            self._problem += pulp.LpAffineExpression(params) == self.data.y[index], str(index_restriction)
            index_restriction += 1

        index_restrictions = 0
        for items in self.data.restriction.data:
            params = []
            for index in range(len(items)):
                if items[index] != 0:
                    params.append((self._vars.get(f'b{index}'), items[index]))
                    params.append((self._vars.get(f'g{index}'), -1 * items[index]))

            if params:
                if self.data.restriction.operators[index_restrictions] == OperatorEnum.EQUALS:
                    self._problem += pulp.LpAffineExpression(params) == self.data.restriction.b[index_restrictions], \
                                     str(index_restriction + index_restrictions)
                elif self.data.restriction.operators[index_restrictions] == OperatorEnum.MORE_OR_EQUAL:
                    self._problem += pulp.LpAffineExpression(params) >= self.data.restriction.b[index_restrictions], \
                                     str(index_restriction + index_restrictions)
                elif self.data.restriction.operators[index_restrictions] == OperatorEnum.LESS_OR_EQUAL:
                    self._problem += pulp.LpAffineExpression(params) <= self.data.restriction.b[index_restrictions], \
                                     str(index_restriction + index_restrictions)
                index_restrictions += 1

    def _execute(self):
        self._problem.solve()

    def _get_var_b_g(self):
        _vars = self._problem.variablesDict()
        b, g = [], []
        for index in range(len(self.data.x[0])):
            b.append(_vars[f'b{index}'].value())
            g.append(_vars[f'g{index}'].value())
        return b, g

    def _get_var_u_v(self):
        _vars = self._problem.variablesDict()
        u, v = [], []
        for index in range(self.data.y.size):
            u.append(_vars[f'u{index}'].value())
            v.append(_vars[f'v{index}'].value())
        return u, v

    def _set_result(self):
        b, g = self._get_var_b_g()
        u, v = self._get_var_u_v()

        for index in range(len(b)):
            self.result.a.append(b[index] - g[index])
        for index in range(len(u)):
            self.result.eps.append(u[index] - v[index])

        self.result.calculation(self.data.x, self.data.y)


# 5  1 6
# 7  7 8
# 9  4 2
# 3  3 5

# problem = pulp.LpProblem('', pulp.const.LpMinimize)
#
# u1 = pulp.LpVariable('u1', lowBound=0)
# u2 = pulp.LpVariable('u2', lowBound=0)
# u3 = pulp.LpVariable('u3', lowBound=0)
# u4 = pulp.LpVariable('u4', lowBound=0)
# v1 = pulp.LpVariable('v1', lowBound=0)
# v2 = pulp.LpVariable('v2', lowBound=0)
# v3 = pulp.LpVariable('v3', lowBound=0)
# v4 = pulp.LpVariable('v4', lowBound=0)
# l12 = pulp.LpVariable('l12', lowBound=0)
# l13 = pulp.LpVariable('l13', lowBound=0)
# l14 = pulp.LpVariable('l14', lowBound=0)
# l23 = pulp.LpVariable('l23', lowBound=0)
# l24 = pulp.LpVariable('l24', lowBound=0)
# l34 = pulp.LpVariable('l34', lowBound=0)
# b1 = pulp.LpVariable('b1', lowBound=0)
# g1 = pulp.LpVariable('g1', lowBound=0)
# b2 = pulp.LpVariable('b2', lowBound=0)
# g2 = pulp.LpVariable('g2', lowBound=0)
#
# problem += 0.3*u1 + 0.3*u2 + 0.3*u3 + 0.3*u4 + 0.3*v1 + 0.3*v2 + 0.3*v3 + 0.3*v4 \
#     + 0.7*l12 + 0.7*l13 + 0.7*l14 + 0.7*l23 + 0.7*l24 + 0.7*l34 \
#     + 0.000001*b1 + 0.000001*g1 + 0.000001*b2 + 0.000001*g2, 'Function'
#
# problem += 6*b1 - 6*g1 + 2*b2 - 2*g2 + l12 >= 0
# problem += 3*b1 - 3*g1 - 4*b2 + 4*g2 + l13 >= 0
# problem += -2*b1 + 2*g1 + b2 - g2 + l14 >= 0
# problem += -3*b1 + 3*g1 - 6*b2 + 6*g2 + l23 >= 0
# problem += 4*b1 - 4*g1 + 3*b2 - 3*g2 + l24 >= 0
# problem += b1 - g1 - 3*b2 + 3*g2 + l34 >= 0
#
# problem += b1 - g1 + 6*b2 - 6*g2 + u1 - v1 == 5
# problem += 7*b1 - 7*g1 + 8*b2 - 8*g2 + u2 - v2 == 7
# problem += 4*b1 - 4*g1 + 2*b2 - 2*g2 + u3 - v3 == 9
# problem += 3*b1 - 3*g1 + 5*b2 - 5*g2 + u4 - v4 == 3
#
# problem.solve()
# for variable in problem.variables():
#     print(variable.name, "=", variable.varValue)
# print(abs(pulp.value(problem.objective)))

# Результаты решения (совпали с ожидаемыми):
# b1 = 0.64285714
# b2 = 0.21428571
# g1 = 0.0
# g2 = 0.0
# l12 = 0.0
# l13 = 0.0
# l14 = 1.0714286
# l23 = 3.2142857
# l24 = 0.0
# l34 = 0.0
# u1 = 3.0714286
# u2 = 0.78571429
# u3 = 6.0
# u4 = 0.0
# v1 = 0.0
# v2 = 0.0
# v3 = 0.0
# v4 = 0.0
# 5.95714373414285
