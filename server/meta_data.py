import enum
import json


class MenuTypes(enum.Enum):
    MAIN = 'MAIN'
    LOAD = 'LOAD'
    DATA = 'DATA'
    ANSWER = 'ANSWER'
    RESTRICTIONS = 'RESTRICTIONS'


class MetaData:
    """
    Сущность для хранения и взаимодействия с клиентскими метаданными.
    Используется как хранилище состояний клиента.
    """

    menu_active_main: bool
    menu_active_load: bool
    menu_active_data: bool
    menu_active_answer: bool
    menu_active_restrictions: bool

    load_data: list

    free_chlen: bool
    delta: float  # Малая положительная величина.
    var_y: int  # Индекс столбца, зависимой переменной. Начинается с 1.

    def __init__(self, data=None):
        if data is not None:
            self.menu_active_main = MetaData.get_value(data, 'menu_active_main')
            self.menu_active_load = MetaData.get_value(data, 'menu_active_load')
            self.menu_active_data = MetaData.get_value(data, 'menu_active_data')
            self.menu_active_answer = MetaData.get_value(data, 'menu_active_answer')
            self.menu_active_restrictions = MetaData.get_value(data, 'menu_active_restrictions')

            self.load_data = MetaData.get_value(data, 'load_data')

            self.free_chlen = MetaData.get_value(data, 'free_chlen')
            self.delta = MetaData.get_value(data, 'delta')
            self.var_y = MetaData.get_value(data, 'var_y')

    def get_load_data_len(self):
        """
        Получает массив индексов столбцов загруженной матрицы.
        Значения в массиве начинается с 1.
        """
        return list(map(int, range(1, len(self.load_data[0]) + 1)))

    def get_load_data_rows_len(self):
        """
        Получает массив индексов строк загруженной матрицы.
        Значения в массиве начинается с 1.
        """
        return list(map(int, range(1, len(self.load_data) + 1)))

    def get_load_data_free_chlen_len(self):
        """
        Получает массив индексов столбцов загруженной матрицы.
        Значения в массиве начинается с 1.
        """
        if self.free_chlen:
            return list(map(int, range(len(self.load_data[0]) + 1)))
        return list(map(int, range(1, len(self.load_data[0]) + 1)))

    def get_work_data_free_chlen_len(self):
        """
        Получает массив индексов столбцов загруженной матрицы.
        Значения в массиве начинается с 1.
        """
        if self.free_chlen:
            return list(map(int, range(len(self.load_data[0]))))
        return list(map(int, range(1, len(self.load_data[0]))))

    def set_active_menu(self, menu_type: MenuTypes):
        self._drop_active_menu()

        if menu_type == MenuTypes.MAIN:
            self.menu_active_main = True
        elif menu_type == MenuTypes.LOAD:
            self.menu_active_load = True
        elif menu_type == MenuTypes.DATA:
            self.menu_active_data = True
        elif menu_type == MenuTypes.ANSWER:
            self.menu_active_answer = True
        elif menu_type == MenuTypes.RESTRICTIONS:
            self.menu_active_restrictions = True

    def set_free_chlen(self, form):
        if self.get_value(form, 'free_chlen'):
            self.free_chlen = True
        else:
            self.free_chlen = False

    def set_data(self, form):
        self.set_free_chlen(form)
        self.delta = float(self.get_value(form, 'delta')) if self.get_value(form, 'delta') else 0.1
        self.var_y = int(self.get_value(form, 'var_y')) if self.get_value(form, 'var_y') else 1

    def _drop_active_menu(self):
        self.menu_active_main = False
        self.menu_active_load = False
        self.menu_active_data = False
        self.menu_active_answer = False
        self.menu_active_restrictions = False

    @staticmethod
    def get_value(data, key):
        try:
            return data[key]
        except KeyError:
            return None

    def __str__(self):
        return json.dumps(self, cls=MetaData.DataEncoder)

    class DataEncoder(json.JSONEncoder):
        """
        Класс кодирует модель MetaData в JSON формат.
        """

        def default(self, obj):
            if isinstance(obj, MetaData):
                return obj.__dict__
            return json.JSONEncoder.default(self, obj)


class OperatorEnum(str, enum.Enum):
    EQUALS = 'EQUALS'
    MORE_OR_EQUAL = 'MORE_OR_EQUAL'
    LESS_OR_EQUAL = 'LESS_OR_EQUAL'

    @staticmethod
    def build(value):
        if not value:
            return OperatorEnum.EQUALS
        return OperatorEnum(value)


class Restriction:
    """
    Сущность ограничений.
    """

    x: int  # количество элементов в строке
    y: int  # количество строк
    data: list
    operators: list
    b: list

    def __init__(self, x: int = 0, data=None):
        if data is not None:
            self.data = Restriction.get_value(data, 'data')
            self.x = Restriction.get_value(data, 'x')
            self.y = Restriction.get_value(data, 'y')
            self.operators = Restriction.get_value(data, 'operators')
            self.b = Restriction.get_value(data, 'b')
        else:
            self.x = x
            self.y = 1
            self.data = []
            self.operators = []
            self.b = []

    @staticmethod
    def get_value(data, key):
        try:
            return data[key]
        except KeyError:
            return None

    def get_data_len(self):
        """
        Получает массив индексов столбцов загруженной матрицы.
        Значения в массиве начинается с 0.
        """
        return list(map(int, range(0, self.x)))

    def get_data_rows_len(self):
        """
        Получает массив индексов строк загруженной матрицы.
        Значения в массиве начинается с 0.
        """
        return list(map(int, range(0, self.y)))

    def get_item_data(self, y: int, x: int) -> float:
        try:
            return self.data[y][x]
        except Exception:
            return 0

    def get_item_b(self, y: int) -> float:
        try:
            return self.b[y]
        except Exception:
            return 0

    def get_operator(self, y: int):
        if len(self.operators) == 0 or y > len(self.operators):
            return OperatorEnum.EQUALS

        return self.operators[y]

    def add_restriction(self):
        self.y += 1
        self.operators.append(OperatorEnum.EQUALS)

    def remove_restriction(self):
        self.y -= 1
        self.y = self.y if self.y >= 0 else 0

        if self.y == 0:
            self.data = []
            self.operators = []
            self.b = []
        else:
            del self.data[-1]
            del self.operators[-1]
            del self.b[-1]

    def set_data(self, form):
        self.data = []
        self.b = []
        self.operators = []

        for y in range(self.y):
            line = []
            for x in range(self.x):
                line.append(float(self.get_value(form, f'a_{y}_{x}')))
            self.data.append(line)

            self.b.append(float(self.get_value(form, f'b_{y}')))
            self.operators.append(OperatorEnum.build(self.get_value(form, f'operator_{y}')))

    class DataEncoder(json.JSONEncoder):
        """
        Класс кодирует модель Restriction в JSON формат.
        """

        def default(self, obj):
            if isinstance(obj, Restriction):
                return obj.__dict__
            return json.JSONEncoder.default(self, obj)
