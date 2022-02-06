import datetime
import json

import jwt
import redis

from server.lp import Result
from server.meta_data import MetaData, Restriction
from server.config import REDIS_HOST, REDIS_PORT, SECRET_JWT


class Token:
    """
    Токен для идентификации сессий пользователей.
    """

    body: str
    create_time: datetime.datetime

    def __init__(self, token: str = None):
        if token is None:
            self.create_time = datetime.datetime.now()
            self.body = jwt.encode(payload={'create_time': str(self.create_time)}, key=SECRET_JWT, algorithm="HS512")
        else:
            data = Token.decode(token)
            self.body = token
            self.create_time = datetime.datetime.fromisoformat(data['create_time'])

    @staticmethod
    def decode(token: str):
        return jwt.decode(jwt=token, key=SECRET_JWT, algorithms="HS512")

    def __str__(self):
        return self.body


class Session:
    """
    Кастомная сессия пользователя.
    """

    token: Token
    _meta_data: MetaData
    _result: Result
    _restriction: Restriction

    def __init__(self, token: Token = None):
        if token is None:
            self.create_token()
        else:
            self.token = token

        self._meta_data = None
        self._result = None
        self._restriction = None

    @property
    def meta_data(self) -> MetaData:
        r = Session._get_redis()
        _data = r.get(f'{self.token.body}_metaData')
        if _data != "" and _data is not None and 'meta_data' in json.loads(_data):
            self._meta_data = MetaData(json.loads(_data)['meta_data'])
        else:
            self._meta_data = MetaData()

        return self._meta_data

    @meta_data.setter
    def meta_data(self, new_meta_data: MetaData):
        self._meta_data = new_meta_data

        self.save_meta_data()

    @property
    def result(self) -> Result:
        r = Session._get_redis()
        _data = r.get(f'{self.token.body}_result')
        if _data != "" and _data is not None and 'result' in json.loads(_data):
            self._result = Result.new_result(json.loads(_data)['result'])
        else:
            self._result = Result.new_result()

        return self._result

    @result.setter
    def result(self, new_result: Result):
        self._result = new_result

        self.save_result()

    @property
    def restriction(self) -> Restriction:
        r = Session._get_redis()
        _data = r.get(f'{self.token.body}_restriction')
        if _data != "" and _data is not None and 'restriction' in json.loads(_data):
            self._restriction = Restriction(data=json.loads(_data)['restriction'])
        else:
            self._restriction = Restriction()

        return self._restriction

    @restriction.setter
    def restriction(self, new_restriction: Restriction):
        self._restriction = new_restriction

        self.save_restriction()

    def create_token(self):
        self.token = Token()
        r = Session._get_redis()
        r.set(
            self.token.body, "")
        r.expireat(
            self.token.body,
            datetime.datetime.fromisoformat(f'{datetime.date.today() + datetime.timedelta(days=1)} 04:00:00'))
        r.close()

    @staticmethod
    def get_session(_token: str):
        try:
            token = Token(_token)

            r = Session._get_redis()
            data = r.get(token.body)
            if data is None:
                r.close()
                return Session()
            r.close()
            return Session(token)

        except jwt.exceptions.InvalidSignatureError:
            return Session()

    def save_meta_data(self):
        r = Session._get_redis()
        r.set(f'{self.token.body}_metaData', f'{{"meta_data":{json.dumps(self._meta_data, cls=MetaData.DataEncoder)}}}')
        r.expireat(
            f'{self.token.body}_metaData',
            datetime.datetime.fromisoformat(f'{datetime.date.today() + datetime.timedelta(days=1)} 04:00:00'))
        r.close()

    def save_result(self):
        r = Session._get_redis()
        r.set(f'{self.token.body}_result', f'{{"result":{json.dumps(self._result, cls=Result.DataEncoder)}}}')
        r.expireat(
            f'{self.token.body}_result',
            datetime.datetime.fromisoformat(f'{datetime.date.today() + datetime.timedelta(days=1)} 04:00:00'))
        r.close()

    def save_restriction(self):
        r = Session._get_redis()
        r.set(f'{self.token.body}_restriction', f'{{"restriction":{json.dumps(self._restriction, cls=Restriction.DataEncoder)}}}')
        r.expireat(
            f'{self.token.body}_restriction',
            datetime.datetime.fromisoformat(f'{datetime.date.today() + datetime.timedelta(days=1)} 04:00:00'))
        r.close()

    @staticmethod
    def _get_redis() -> redis.Redis:
        return redis.Redis(decode_responses=True, host=REDIS_HOST, port=REDIS_PORT)

    class DataEncoder(json.JSONEncoder):
        """
        Класс кодирует модель Session в JSON формат.
        """
        def default(self, obj):
            if isinstance(obj, Session):
                return obj.__dict__
            return json.JSONEncoder.default(self, obj)
