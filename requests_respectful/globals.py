import yaml
from redis import StrictRedis, ConnectionError

from .exceptions import RequestsRespectfulConfigError, RequestsRespectfulRedisError


# CONFIG
default_config = {
    "redis": {
        "host": "localhost",
        "port": 6379,
        "database": 0
    },
    "safety_threshold": 10,
    "requests_module_name": "requests"
}

try:
    with open("requests-respectful.config.yml", "r") as f:
        config = yaml.load(f)

    if "safety_threshold" not in config:
        config["safety_threshold"] = default_config.get("safety_threshold")
    else:
        if type(config["safety_threshold"]) != int or config["safety_threshold"] < 0:
            raise RequestsRespectfulConfigError(
                "'safety_threshold' key must be a positive integer in 'requests-respectful.config.yml'"
            )

    if "requests_module_name" not in config:
        config["requests_module_name"] = default_config.get("requests_module_name")
    else:
        if type(config["requests_module_name"]) != str:
            raise RequestsRespectfulConfigError(
                "'requests_module_name' key must be a string in 'requests-respectful.config.yml'"
            )

    if "redis" not in config:
        raise RequestsRespectfulConfigError("'redis' key is missing from 'requests-respectful.config.yml'")

    expected_redis_keys = ["host", "port", "database"]
    missing_redis_keys = list()

    for expected_redis_key in expected_redis_keys:
        if expected_redis_key not in config["redis"]:
            missing_redis_keys.append(expected_redis_key)

    if len(missing_redis_keys):
        raise RequestsRespectfulConfigError(
            "'%s' %s missing from the 'redis' configuration key in 'requests-respectful.config.yml'" % (
                ", ".join(missing_redis_keys),
                "is" if len(missing_redis_keys) == 1 else "are"
            )
        )
except FileNotFoundError:
    config = default_config


# REDIS CLIENT
redis = StrictRedis(
    host=config["redis"]["host"],
    port=config["redis"]["port"],
    db=config["redis"]["database"]
)

try:
    redis.echo("Testing Connection")
except ConnectionError:
    raise RequestsRespectfulRedisError("Could not establish a connection to the provided Redis server")
