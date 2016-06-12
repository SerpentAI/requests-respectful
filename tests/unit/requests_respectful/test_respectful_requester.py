# -*- coding: utf-8 -*-
import pytest

from requests_respectful import RespectfulRequester
from requests_respectful import RequestsRespectfulError, RequestsRespectfulConfigError, RequestsRespectfulRateLimitedError

import redis

import requests
import requests as r


# Tests
def test_setup():
    rr = RespectfulRequester()
    rr.unregister_realm("TEST123")

    RespectfulRequester.configure_default()


def test_the_class_should_accept_configuration_values():
    rr = RespectfulRequester()

    assert rr._config()["safety_threshold"] == 10
    assert rr._config()["requests_module_name"] == "requests"

    RespectfulRequester.configure(safety_threshold=20)
    RespectfulRequester.configure(requests_module_name="r")
    RespectfulRequester.configure(redis={"host": "0.0.0.0", "port": 6379, "database": 1})

    assert rr._config()["safety_threshold"] == 20
    assert rr._config()["requests_module_name"] == "r"
    assert rr._config()["redis"]["host"] == "0.0.0.0"
    assert rr._config()["redis"]["database"] == 1

    RespectfulRequester.configure_default()


def test_the_class_should_validate_provided_configuration_values():
    with pytest.raises(RequestsRespectfulConfigError):
        RespectfulRequester.configure(redis="REDIS")

    with pytest.raises(RequestsRespectfulConfigError):
        RespectfulRequester.configure(redis=dict())

    with pytest.raises(RequestsRespectfulConfigError):
        RespectfulRequester.configure(redis={"host": "localhost", "port": 6379})

    RespectfulRequester.configure(redis={"host": "localhost", "port": 6379, "database": 0})

    with pytest.raises(RequestsRespectfulConfigError):
        RespectfulRequester.configure(safety_threshold="SAFETY")

    with pytest.raises(RequestsRespectfulConfigError):
        RespectfulRequester.configure(safety_threshold=-15)

    RespectfulRequester.configure(safety_threshold=10)

    with pytest.raises(RequestsRespectfulConfigError):
        RespectfulRequester.configure(requests_module_name=100)

    RespectfulRequester.configure(requests_module_name="requests")

    RespectfulRequester.configure_default()


def test_the_class_should_be_able_to_restore_the_default_configuration_values():
    rr = RespectfulRequester()

    RespectfulRequester.configure(safety_threshold=20)
    RespectfulRequester.configure(requests_module_name="r")
    RespectfulRequester.configure(redis={"host": "0.0.0.0", "port": 6379, "database": 1})

    RespectfulRequester.configure_default()

    assert rr._config()["safety_threshold"] == 10
    assert rr._config()["requests_module_name"] == "requests"
    assert rr._config()["redis"]["host"] == "localhost"
    assert rr._config()["redis"]["database"] == 0


def test_the_instance_should_have_a_property_that_holds_a_redis_object():
    rr = RespectfulRequester()
    assert type(rr.redis) == redis.StrictRedis


def test_the_instance_should_have_a_property_that_holds_a_redis_prefix():
    rr = RespectfulRequester()
    assert rr.redis_prefix == "RespectfulRequester"


def test_the_instance_should_be_able_to_access_the_global_config():
    rr = RespectfulRequester()

    assert "redis" in rr._config()
    assert "safety_threshold" in rr._config()
    assert "requests_module_name" in rr._config()


def test_the_instance_should_be_able_to_generate_a_redis_key_when_provided_with_a_realm():
    rr = RespectfulRequester()

    assert rr._realm_redis_key("TEST") == "%s:REALMS:TEST" % rr.redis_prefix
    assert rr._realm_redis_key("TEST2") == "%s:REALMS:TEST2" % rr.redis_prefix
    assert rr._realm_redis_key("TEST SPACED") == "%s:REALMS:TEST SPACED" % rr.redis_prefix
    assert rr._realm_redis_key("TEST ÉÉÉ") == "%s:REALMS:TEST ÉÉÉ" % rr.redis_prefix


def test_the_instance_should_be_able_to_register_a_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)

    assert rr.realm_max_requests("TEST123") == 100
    assert rr.realm_timespan("TEST123") == 300
    assert rr.redis.sismember("%s:REALMS" % rr.redis_prefix, "TEST123")

    rr.unregister_realm("TEST123")


def test_the_instance_should_not_overwrite_when_registering_a_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)
    rr.register_realm("TEST123", max_requests=1000, timespan=3000)

    assert rr.realm_max_requests("TEST123") == 100
    assert rr.realm_timespan("TEST123") == 300

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_update_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)
    rr.update_realm("TEST123", max_requests=1000, timespan=3000)

    assert rr.realm_max_requests("TEST123") == 1000
    assert rr.realm_timespan("TEST123") == 3000

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_fetch_a_list_of_registered_realms():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)

    assert "TEST123" in rr.fetch_registered_realms()

    rr.unregister_realm("TEST123")


def test_the_instance_should_ignore_invalid_values_when_updating_a_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)
    rr.update_realm("TEST123", max_requests="FOO", timespan="BAR", fake=True)

    assert rr.realm_max_requests("TEST123") == 100
    assert rr.realm_timespan("TEST123") == 300

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_unregister_a_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)

    request_func = lambda: requests.get("http://google.com")
    rr._perform_request(request_func, "TEST123")

    rr.unregister_realm("TEST123")

    assert rr.redis.get(rr._realm_redis_key("TEST123")) is None
    assert not rr.redis.sismember("%s:REALMS" % rr.redis_prefix, "TEST123")
    assert not len(rr.redis.keys("%s:REQUESTS:%s:*" % (rr.redis_prefix, "TEST123")))


def test_the_instance_should_ignore_invalid_realms_when_attempting_to_unregister():
    rr = RespectfulRequester()

    rr.unregister_realm("TEST123")
    rr.unregister_realm("TEST")
    rr.unregister_realm("TEST12345")


def test_the_instance_should_be_able_to_fetch_the_information_of_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)

    assert b"max_requests" in rr._fetch_realm_info("TEST123")
    assert rr._fetch_realm_info("TEST123")[b"max_requests"] == b"100"

    assert b"timespan" in rr._fetch_realm_info("TEST123")
    assert rr._fetch_realm_info("TEST123")[b"timespan"] == b"300"

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_return_the_max_requests_value_of_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)
    assert rr.realm_max_requests("TEST123") == 100

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_return_the_timespan_value_of_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)
    assert rr.realm_timespan("TEST123") == 300

    rr.unregister_realm("TEST123")


def test_the_instance_should_validate_that_the_request_lambda_is_actually_a_requests_call():
    rr = RespectfulRequester()

    with pytest.raises(RequestsRespectfulError):
        rr._validate_request_func(lambda: 1 + 1)

    rr._validate_request_func(lambda: requests.get("http://google.com"))
    rr._validate_request_func(lambda: getattr(requests, "get")("http://google.com"))


def test_the_instance_should_be_able_to_determine_the_amount_of_requests_performed_in_a_timespan_for_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=1000, timespan=5)

    assert rr._requests_in_timespan("TEST123") == 0

    request_func = lambda: requests.get("http://google.com")

    rr._perform_request(request_func, "TEST123")
    rr._perform_request(request_func, "TEST123")
    rr._perform_request(request_func, "TEST123")

    assert rr._requests_in_timespan("TEST123") == 3

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_determine_if_it_can_perform_a_request_for_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=1000, timespan=5)

    assert rr._can_perform_request("TEST123")

    rr.update_realm("TEST123", max_requests=0)

    assert not rr._can_perform_request("TEST123")

    rr.unregister_realm("TEST123")


def test_the_instance_should_not_allow_a_request_to_be_made_on_an_unregistered_realm():
    rr = RespectfulRequester()

    request_func = lambda: requests.get("http://google.com")

    with pytest.raises(RequestsRespectfulError):
        rr.request(request_func, "TEST123")


def test_the_instance_should_perform_the_request_if_it_is_allowed_to_on_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=1000, timespan=5)

    request_func = lambda: requests.get("http://google.com")
    assert type(rr._perform_request(request_func, "TEST123")) == requests.Response

    rr.unregister_realm("TEST123")


def test_the_instance_should_return_a_rate_limit_exception_if_the_request_is_not_allowed_on_a_registered_realm():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=0, timespan=5)

    request_func = lambda: requests.get("http://google.com")

    with pytest.raises(RequestsRespectfulRateLimitedError):
        rr._perform_request(request_func, "TEST123")

    rr.unregister_realm("TEST123")


def test_the_instance_should_be_able_to_wait_for_a_request_to_be_allowed_on_a_registered_realm():
    rr = RespectfulRequester()

    RespectfulRequester.configure(safety_threshold=0)

    rr.register_realm("TEST123", max_requests=1, timespan=2)

    request_func = lambda: requests.get("http://google.com")

    rr.request(request_func, "TEST123", wait=True)
    rr.request(request_func, "TEST123", wait=True)
    rr.request(request_func, "TEST123", wait=True)

    rr.unregister_realm("TEST123")

    RespectfulRequester.configure_default()


def test_the_instance_should_recognize_the_requests_proxy_methods():
    rr = RespectfulRequester()

    getattr(rr, "delete")
    getattr(rr, "get")
    getattr(rr, "head")
    getattr(rr, "options")
    getattr(rr, "patch")
    getattr(rr, "post")
    getattr(rr, "put")

    with pytest.raises(AttributeError):
        getattr(rr, "foo")


def test_the_instance_should_get_the_same_results_by_using_the_requests_proxy_as_when_using_the_request_method():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=100, timespan=300)

    assert type(rr.get("http://google.com", realm="TEST123")) == requests.Response

    rr.update_realm("TEST123", max_requests=0)

    with pytest.raises(RequestsRespectfulRateLimitedError):
        rr.get("http://google.com", realm="TEST123")

    rr.unregister_realm("TEST123")


def test_the_safety_threshold_configuration_value_should_have_the_expected_effect():
    rr = RespectfulRequester()

    rr.register_realm("TEST123", max_requests=11, timespan=300)

    RespectfulRequester.configure(safety_threshold=10)

    request_func = lambda: requests.get("http://google.com")

    rr.request(request_func, "TEST123")

    with pytest.raises(RequestsRespectfulRateLimitedError):
        rr.request(request_func, "TEST123")

    RespectfulRequester.configure_default()

    rr.unregister_realm("TEST123")


def test_the_requests_module_name_configuration_value_should_have_the_expected_effect():
    rr = RespectfulRequester()

    RespectfulRequester.configure(requests_module_name="r")

    request_func = lambda: r.get("http://google.com")

    rr._validate_request_func(request_func)

    RespectfulRequester.configure_default()


def test_teardown():
    pass
