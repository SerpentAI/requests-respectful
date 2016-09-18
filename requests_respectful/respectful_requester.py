from .globals import default_config, config, redis
from .exceptions import RequestsRespectfulError, RequestsRespectfulConfigError, RequestsRespectfulRateLimitedError, RequestsRespectfulRedisError

from redis import StrictRedis, ConnectionError

import uuid
import inspect
import time

import requests

import warnings


class RespectfulRequester:

    def __init__(self):
        self.redis = redis

        try:
            self.redis.echo("Testing Connection")
        except ConnectionError:
            raise RequestsRespectfulRedisError("Could not establish a connection to the provided Redis server")

    def __getattr__(self, attr):
        if attr in ["delete", "get", "head", "options", "patch", "post", "put"]:
            return getattr(self, "_requests_proxy_%s" % attr)
        else:
            raise AttributeError()

    @property
    def redis_prefix(self):
        return "RespectfulRequester"

    def request(self, request_func, realm=None, realms=None, wait=False):
        if realm is not None:
            warnings.warn("'realm' kwarg will be removed in favor of providing a 'realms' list starting in 0.3.0", DeprecationWarning)
            realms = [realm]

        registered_realms = self.fetch_registered_realms()

        for r in realms:
            if r not in registered_realms:
                raise RequestsRespectfulError("Realm '%s' hasn't been registered" % realm)

        if wait:
            while True:
                try:
                    return self._perform_request(request_func, realms=realms)
                except RequestsRespectfulRateLimitedError:
                    pass

                time.sleep(1)
        else:
            return self._perform_request(request_func, realms=realms)

    def fetch_registered_realms(self):
        return list(map(lambda k: k.decode("utf-8"), self.redis.smembers("%s:REALMS" % self.redis_prefix)))

    def register_realm(self, realm, max_requests, timespan):
        redis_key = self._realm_redis_key(realm)

        if not self.redis.hexists(redis_key, "max_requests"):
            self.redis.hmset(redis_key, {"max_requests": max_requests, "timespan": timespan})
            self.redis.sadd("%s:REALMS" % self.redis_prefix, realm)

        return True

    def register_realms(self, realm_tuples):
        for realm_tuple in realm_tuples:
            self.register_realm(*realm_tuple)

        return True

    def update_realm(self, realm, **kwargs):
        redis_key = self._realm_redis_key(realm)
        updatable_keys = ["max_requests", "timespan"]

        for updatable_key in updatable_keys:
            if updatable_key in kwargs and type(kwargs[updatable_key]) == int:
                self.redis.hset(redis_key, updatable_key, kwargs[updatable_key])

        return True

    def unregister_realm(self, realm):
        self.redis.delete(self._realm_redis_key(realm))
        self.redis.srem("%s:REALMS" % self.redis_prefix, realm)

        request_keys = self.redis.keys("%s:REQUEST:%s:*" % (self.redis_prefix, realm))
        [self.redis.delete(k) for k in request_keys]

        return True

    def unregister_realms(self, realms):
        for realm in realms:
            self.unregister_realm(realm)

        return True

    def realm_max_requests(self, realm):
        realm_info = self._fetch_realm_info(realm)
        return int(realm_info["max_requests".encode("utf-8")].decode("utf-8"))

    def realm_timespan(self, realm):
        realm_info = self._fetch_realm_info(realm)
        return int(realm_info["timespan".encode("utf-8")].decode("utf-8"))

    @classmethod
    def configure(cls, **kwargs):
        if "redis" in kwargs:
            if type(kwargs["redis"]) != dict:
                raise RequestsRespectfulConfigError("'redis' key must be a dict")

            expected_redis_keys = ["host", "port", "database"]
            missing_redis_keys = list()

            for expected_redis_key in expected_redis_keys:
                if expected_redis_key not in kwargs["redis"]:
                    missing_redis_keys.append(expected_redis_key)

            if len(missing_redis_keys):
                raise RequestsRespectfulConfigError("'%s' %s missing from the 'redis' configuration key" % (
                    ", ".join(missing_redis_keys),
                    "is" if len(missing_redis_keys) == 1 else "are"
                ))

            config["redis"] = kwargs["redis"]

            global redis
            redis = StrictRedis(
                host=config["redis"]["host"],
                port=config["redis"]["port"],
                db=config["redis"]["database"]
            )

        if "safety_threshold" in kwargs:
            if type(kwargs["safety_threshold"]) != int or kwargs["safety_threshold"] < 0:
                raise RequestsRespectfulConfigError("'safety_threshold' key must be a positive integer")

            config["safety_threshold"] = kwargs["safety_threshold"]

        if "requests_module_name" in kwargs:
            if type(kwargs["requests_module_name"]) != str:
                raise RequestsRespectfulConfigError("'requests_module_name' key must be string")

            config["requests_module_name"] = kwargs["requests_module_name"]

        return config

    @classmethod
    def configure_default(cls):
        for key in config:
            config[key] = default_config[key]

        return config

    def _perform_request(self, request_func, realms=None):
        self._validate_request_func(request_func)

        rate_limited_realms = list()

        for realm in realms:
            if not self._can_perform_request(realm):
                rate_limited_realms.append(realm)

        if not len(rate_limited_realms):
            for realm in realms:
                request_uuid = str(uuid.uuid4())

                self.redis.setex(
                    name="%s:REQUEST:%s:%s" % (self.redis_prefix, realm, request_uuid),
                    time=self.realm_timespan(realm),
                    value=request_uuid
                )

            return request_func()
        else:
            raise RequestsRespectfulRateLimitedError("Currently rate-limited on Realm(s): %s" % ", ".join(rate_limited_realms))

    def _realm_redis_key(self, realm):
        return "%s:REALMS:%s" % (self.redis_prefix, realm)

    def _fetch_realm_info(self, realm):
        redis_key = self._realm_redis_key(realm)
        return self.redis.hgetall(redis_key)

    def _requests_in_timespan(self, realm):
        return len(
            self.redis.scan(
                cursor=0,
                match="%s:REQUEST:%s:*" % (self.redis_prefix, realm),
                count=self._redis_keys_in_db() + 100
            )[1]
        )

    def _redis_keys_in_db(self):
        return self.redis.info().get("db%d" % config["redis"]["database"]).get("keys")

    def _can_perform_request(self, realm):
        return self._requests_in_timespan(realm) < (self.realm_max_requests(realm) - config["safety_threshold"])

    # Requests proxy
    def _requests_proxy(self, method, *args, **kwargs):
        realm = kwargs.pop("realm", None)
        realms = kwargs.pop("realms", list())

        if realm:
            warnings.warn("'realm' kwarg will be removed in favor of providing a 'realms' list starting in 0.3.0", DeprecationWarning)
            realms.append(realm)

        if not len(realms):
            raise RequestsRespectfulError("'realms' is a required kwarg")

        wait = kwargs.pop("wait", False)

        return self.request(lambda: getattr(requests, method)(*args, **kwargs), realms=realms, wait=wait)

    def _requests_proxy_delete(self, *args, **kwargs):
        return self._requests_proxy("delete", *args, **kwargs)

    def _requests_proxy_get(self, *args, **kwargs):
        return self._requests_proxy("get", *args, **kwargs)

    def _requests_proxy_head(self, *args, **kwargs):
        return self._requests_proxy("head", *args, **kwargs)

    def _requests_proxy_options(self, *args, **kwargs):
        return self._requests_proxy("options", *args, **kwargs)

    def _requests_proxy_patch(self, *args, **kwargs):
        return self._requests_proxy("patch", *args, **kwargs)

    def _requests_proxy_post(self, *args, **kwargs):
        return self._requests_proxy("post", *args, **kwargs)

    def _requests_proxy_put(self, *args, **kwargs):
        return self._requests_proxy("put", *args, **kwargs)

    @staticmethod
    def _validate_request_func(request_func):
        request_func_string = inspect.getsource(request_func)
        post_lambda_string = request_func_string.split(":")[1].strip()

        if not post_lambda_string.startswith(config["requests_module_name"]) and not post_lambda_string.startswith("getattr(requests"):
            raise RequestsRespectfulError("The request lambda can only contain a requests function call")

    @staticmethod
    def _config():
        return config
