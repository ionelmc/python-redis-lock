import functools
import inspect
from logging import getLogger

import redis
from retrying import retry

logger = getLogger(__name__)


def check_if_connection_exception(exception):
    return isinstance(exception, redis.exceptions.ConnectionError) \
           or isinstance(exception, TimeoutError) \
           or isinstance(exception, redis.exceptions.TimeoutError)


def renew_old_redis_connection(meth, args, e):
    cls = get_class_from_method(meth)
    current_conn = getattr(cls, "conn", None)
    if not current_conn:
        cls = args[0]
        current_conn = getattr(cls, "conn", None)
    if current_conn:
        logger.error("Got connection error, renewing old connection to DB\n\n%s", e)
        redis_kwargs = getattr(cls, "redis_kwargs", None)
        if redis_kwargs:
            cls.conn = type(current_conn)(**redis_kwargs)


def register_scripts(meth, args, e):
    cls = get_class_from_method(meth)
    current_conn = getattr(cls, "conn", None)
    if not current_conn:
        cls = args[0]
        current_conn = getattr(cls, "conn", None)
    if current_conn:
        force_register_scripts_func = getattr(cls, "force_register_scripts", None)
        if force_register_scripts_func:
            logger.error("Got No matching script error, registering scripts again\n\n%s", e)
            force_register_scripts_func(current_conn)
        else:
            logger.exception("Got class without force_register_scripts, can't reregister", e)


def handle_redis_exception(method):
    @functools.wraps(method)
    @retry(retry_on_exception=check_if_connection_exception, stop_max_attempt_number=2)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (redis.exceptions.ConnectionError, TimeoutError, redis.exceptions.TimeoutError) as e:
            renew_old_redis_connection(method, args, e)
            try:
                return method(*args, **kwargs)
            except Exception as e:
                logger.error("Got another excpetion after renew")
                raise e
        except redis.exceptions.NoScriptError as e:
            register_scripts(method, args, e)

    return wrapper


def get_class_from_method(meth):
    if isinstance(meth, functools.partial):
        return get_class_from_method(meth.func)
    if inspect.ismethod(meth) or (inspect.isbuiltin(meth) and getattr(meth, '__self__', None) is not None
                                  and getattr(meth.__self__, '__class__', None)):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)


def wrap_all_class_methods(decorator):
    def decorate(cls):
        for attr in cls.__dict__:
            _obj = getattr(cls, attr)
            if callable(_obj):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate
