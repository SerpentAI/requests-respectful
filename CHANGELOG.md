## 0.2.0

* Added multiple realm per request support. Thanks to @beaugunderson for idea and use case!
* Added bulk realm registering/unregistering
* Deferred the Redis Connection check from module loading to instance initialization, giving time to the user to manually configure
* Now using copy.deepcopy to create a config from the default config
* Deprecated 'realm' kwarg on request methods in favor of the new 'realms' list

## 0.1.2

* Fixed an important issue with the way the Redis scans were performed in databases with a lot of keys

## 0.1.1

* Fixed an issue in package file (setup.py)

## 0.1.0

* Initial Release
