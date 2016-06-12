# requests-respectful

If you know Python, you know *[Requests](http://docs.python-requests.org/)*. *Requests* is love. *Requests* is life. Depending on your use cases, you may come across scenarios where you need to use *Requests* a lot. Services you consume may have rate-limiting policies in place or you may just happen to be in a good mood and feel like being a good Netizen. This is where *requests-respectful* can come in handy.

***requests-respectul***:

* Is a minimalist wrapper on top of *Requests* to work within rate limits of any amount of services simultaneously
* Can scale out of a single thread, single process or even a single machine
* Enables maximizing your allowed requests without ever going over set limits and having to handle the fallout
* Proxies *Requests* HTTP verb methods (for minimal code changes)
* Works with both Python 2 and 3 and is fully tested
* Is cool (hopefully?)

**Typical *requests* call**

```python
import requests
response = requests.get("http://github.com", params={"foo": "bar"})
```

**Magic *requests-respectful* call** - *requests* verb methods are proxied!

```python
from requests_respectful import RespectfulRequester

rr = RespectfulRequester()

# This can be done elsewhere but the realm needs to be registered!
rr.register_realm("Github", max_requests=100, timespan=60)

response = rr.get("http://github.com", params={"foo": "bar"}, realm="Github", wait=True)
```

**Conservative *requests-respectful* call** - pass a lambda with a *requests* method call

```python
import requests
from requests_respectful import RespectfulRequester

rr = RespectfulRequester()

# This can be done elsewhere but the realm needs to be registered!
rr.register_realm("Github", max_requests=100, timespan=60)

request_func = lambda: requests.get("http://github.com", params={"foo": "bar"})
response = rr.request(request_func, realm="Github", wait=True)
```

## Requirements

* [Redis](http://redis.io/) > 2.8.0 (See FAQ if you are rolling your eyes)

## Installation

```shell
pip install requests-respectful
```

## Configuration

### Default Configuration Values
```python
{
    "redis": {
        "host": "localhost",
        "port": 6379,
        "database": 0
    },
    "safety_threshold": 10,
    "requests_module_name": "requests"
}
```

### Configuration Keys

* **redis**: Provides the `host`, `port`and `database` of the Redis instance
* **safety_threshold**: A rate-limited exception will be raised at *(realm_max_requests - safety_threshold)*. Prevents going over the limit of services in scenarios where a large amount of requests are issued in parallel
* **requests_module_name**: Provides the name of the *Requests* module used in the request lambdas. Should not need to be changed unless you import *Requests* as another name.

### Overriding Configuration Values

#### With *requests-respectful.config.yml*

The library auto-detects the presence of a YAML file named *requests-respectful.config.yml* at the root of your project and will attempt to load configuration values from it.

**Example**:

requests-respectful.config.yml
```yaml
redis:
	host: 0.0.0.0
    port: 6379
    database: 5

safety_threshold: 25
```

#### With the *configure()* class method

If you don't like having an extra file lying around, the library can also be configured at runtime using the *configure()* class method.

```python
RespectfulRequester.configure(
	redis={"host": "0.0.0.0", "port": 6379, "database": 5},
    safety_threshold=25
)
```

**In both cases, the resulting active configuration would be:**
```python
RespectfulRequester._config()

Out[1]: {
    "redis": {
        "host": "0.0.0.0",
        "port": 6379,
        "database": 5
    },
    "safety_threshold": 25,
    "requests_module_name": "requests"
}
```


## Usage

In your quest to use *requests-respectful*, you should only ever have to bother with one class: *RespectfulRequester*. Instance this class and you can perform all important operations.

Before each example, it is assumed that the following code has already been executed.
```python
from requests_respectful import RespectfulRequester
rr = RespectfulRequester()
```

### Realms

Realms are simply named containers that are provided with a maximum requesting rate. You are responsible of the management (i.e. CRUD) of your realms.

Realms track the HTTP requests that are performed under them and will raise a catchable rate limit exception if you are over their allowed requesting rate.

#### Fetching the list of Realms
```python
rr.fetch_registered_realms()
```

This returns a list of currently registered realm names.

#### Registering a Realm
```python
rr.register_realm("Google", max_requests=10, timespan=1)
rr.register_realm("Github", max_requests=100, timespan=60)
rr.register_realm("Twitter", max_requests=150, timespan=300)
```

This register 3 realms:
* *Google* at a maximum requesting rate of 10 requests per second
* *Gihub* at a maximum requesting rate of 100 requests per minute
* *Twitter* at a maximum requesting rate of 150 requests per 5 minutes

#### Updating a Realm
```python
rr.update_realm("Google", max_requests=25, timespan=5)
```

This updates the maximum requesting rate of *Google* to 25 requests per 5 seconds.

#### Getting the maximum requests value of a Realm
```python
rr.realm_max_requests("Google")
```

This would return 25.

#### Getting the timespan value of a Realm
```python
rr.realm_timespan("Google")
```

This would return 5.

#### Unregistering a Realm
```python
rr.unregister_realm("Google")
```

This would unregister the *Google* realm, preventing further queries from executing on it.

### Requesting

#### Using *Requests* HTTP verb methods

The library supports proxying calls to the 7 *Requests* HTTP verb methods (DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT). This is literally a *Requests* method so go crazy with your *params*, *body*, *headers*, *auth* etc. kwargs. The only major difference is that a *realm* kwarg is expected. A *wait* boolean kwargs can also be provided (the behavior is explained later).

These are all valid calls:
```python
rr.get("http://httpbin.org", realm="HTTPBin")
rr.post('http://httpbin.org/post', data = {'key':'value'}, realm="HTTPBin", wait=True)
rr.put('http://httpbin.org/put', data = {'key':'value'}, realm="HTTPBin")
rr.delete('http://httpbin.org/delete', realm="HTTPBin")
```

If not rate-limited, these would return your usual *requests.Response* object.

#### Using a request lamba

If you are a purist and prefer not using fancy proxying, you are also allowed to create a lambda of your *Requests* call and pass it to the *request()* instance method.

```python
request_func = lambda: requests.post('http://httpbin.org/post', data = {'key':'value'})
rr.request(request_func, realm="HTTPBin", wait=True)
```

If not rate-limited, this would return your usual *requests.Response* object.

#### Handling exceptions

Executing these calls will either return a *requests.Response* object with the results of the HTTP call or raise a RequestsRespectfulRateLimitedError exception. This means that you'll likely want to catch and handle that exception.

```python
from requests_respectful import RequestsRespectfulRateLimitedError

try:
	response = rr.get("http://httpbin.org", realm="HTTPBin")
except RequestsRespectfulRateLimitedError:
	pass # Possibly requeue that call or wait.
```

#### The *wait* kwarg

Both ways of requesting accept a *wait* kwarg that defaults to False. If switched on and the realm is currently rate-limited, the process will block, wait until it is safe to send requests again and perform the requests then. Waiting is perfectly fine for scripts or smaller operations but is discouraged for large, multi-realm, parallel tasks (i.e. Background Tasks like Celery workers).

## Tests

* Exist? `Yes`
* Exhaustive? `Yes`
* Facepalm tactics? `Yes -  Redis calls aren't mocked and google.com gets a few friendly calls`

Run them with `python -m pytest tests --spec`

## FAQ

### Whoa, whoa, whoa! Redis?!

Yes. The use of Redis allows for *requests-respectful* to go multi-thread, multi-process and even multi-machine while still respecting the maximum requesting rates of registered realms. Operations like Redis' SETEX are key in designing and working with rate-limiting systems. If you are doing Python development, there is a decent chance you already work with Redis as it is one of the two options to use as Celery's backend and one of the 2 major caching options in Web development. If not, you can always keep things clean and use a [Docker Container](https://hub.docker.com/_/redis/) or even [build it from source](http://redis.io/download#installation). Redis has kept a consistent record over the years of being lightweight, solid software.

### How is this different than other throttling libraries?

* Most other libraries will ask you to specify an interval at which to send requests and will literally loop over `request()...time.sleep(interval)`. This one will allow to send as many as you want, as fast as you want, as long as you are under the maximum requesting rate of your realm.
* Other libraries don't have the concept of realms and separate requesting rate rules.
* Other libraries don't scale outside of the process.
* Most other libraries don't integrate this neatly with *Requests*

## Roadmap / Contribution Ideas

* Provide some introspection methods to get live realm stats
* Create a curses realm stats monitor
* Provide real-life use cases
* Read the Docs RST Documentation
* Mock out the Redis calls in the tests
* Mock out the Requests calls in the tests