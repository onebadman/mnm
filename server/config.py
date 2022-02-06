import os

SECRET_FLASK = os.environ.get('SECRET_FLASK') if os.environ.get('SECRET_FLASK') is not None else 'secret'
SECRET_JWT = os.environ.get('SECRET_JWT') if os.environ.get('SECRET_FLASK') is not None else 'secret'

REDIS_HOST = os.environ.get('REDIS_HOST') if os.environ.get('SECRET_FLASK') is not None else 'localhost'
REDIS_PORT = os.environ.get("REDIS_PORT") if os.environ.get('SECRET_FLASK') is not None else '6379'

SPACE = os.environ.get("SPACE") if os.environ.get('SECRET_FLASK') is not None else 'dev'
