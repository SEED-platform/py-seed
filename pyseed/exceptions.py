"""
copyright (c) 2016-2017 Earth Advantage.
All rights reserved

..codeauthor::Paul Munday <paul@paulmunday.net>
"""


# Setup

# Constants

# Data Structure Definitions

# Private Functions

# Public Classes and Functions


class APIClientError(Exception):
    """Indicates errors when calling an API"""

    def __init__(self, error, service=None, url=None, caller=None, verb=None, status_code=None, **kwargs):
        self.error = error
        self.service = service
        self.url = url
        self.caller = caller
        self.verb = verb
        self.status_code = status_code
        args = (error, service, url, caller, verb.upper() if verb else None, status_code)
        self.kwargs = kwargs
        super().__init__(*args)

    def __str__(self):
        msg = f"{self.__class__.__name__}: {self.error}"
        if self.service:
            msg = f"{msg}, calling service {self.service}"
        if self.caller:
            msg = f"{msg} as {self.caller}"
        if self.url:
            msg = f"{msg} with url {self.url}"
        if self.verb:
            msg = f"{msg}, http method: {self.verb.upper()}"
        if self.kwargs:
            arguments = ", ".join([f"{key!s}={val!s}" for key, val in self.kwargs.items()])
            msg = f"{msg} supplied with {arguments}"
        if self.status_code:
            msg = f"{msg} http status code: {self.status_code}"
        return msg


class SEEDError(APIClientError):
    """Indicates Error interacting with SEED API"""

    def __init__(self, error, url=None, caller=None, verb=None, status_code=None, **kwargs):
        super().__init__(error, service="SEED", url=url, caller=caller, verb=verb, status_code=status_code, **kwargs)
