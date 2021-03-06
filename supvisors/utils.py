#!/usr/bin/python
# -*- coding: utf-8 -*-

# ======================================================================
# Copyright 2016 Julien LE CLEACH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ======================================================================

from math import sqrt
from time import gmtime, localtime, strftime, time


class InternalEventHeaders:
    """ Enumeration class for the headers in messages between Listener
    and MainLoop. """
    TICK, PROCESS, STATISTICS = range(3)


class RemoteCommEvents:
    """ Strings used for remote communication between the Supvisors main loop
    and the listener. """
    SUPVISORS_AUTH = u'auth'
    SUPVISORS_EVENT = u'event'
    SUPVISORS_INFO = u'info'


class EventHeaders:
    """ Strings used as headers in messages between EventPublisher
    and Supvisors' Client. """
    SUPVISORS = u'supvisors'
    ADDRESS = u'address'
    APPLICATION = u'application'
    PROCESS_EVENT = u'event'
    PROCESS_STATUS = u'process'


# for deferred XML-RPC requests
class DeferredRequestHeaders:
    """ Enumeration class for the headers of deferred XML-RPC messages sent to MainLoop."""
    CHECK_ADDRESS, ISOLATE_ADDRESSES, START_PROCESS, STOP_PROCESS, RESTART, SHUTDOWN = range(6)


def enumeration_tools(cls):
    """ Decorator for enumeration classes.
    Add class attributes and methods for conversion between string and enum,
    for listing enumeration values and strings. """

    def to_string(cls, value):
        """ Convert the enum value into a string. """
        return cls.enum_map[value]

    def from_string(cls, str_enum):
        """ Convert a string into an enum value. """
        return cls.string_map[str_enum]

    def values(cls):
        """ Return all enum values. """
        return cls.enum_map.keys()

    def strings(cls):
        """ Return all enum values as string. """
        return cls.string_map.keys()

    setattr(cls, 'string_map', {x: y for x, y in cls.__dict__.items()
                                 if not x.startswith('_')})
    setattr(cls, 'enum_map', {y: x for x, y in cls.string_map.items()})
    setattr(cls, 'to_string', classmethod(to_string))
    setattr(cls, 'from_string', classmethod(from_string))
    setattr(cls, 'values', classmethod(values))
    setattr(cls, 'strings', classmethod(strings))
    return cls


def supvisors_shortcuts(instance, lst):
    """ Used to set shortcuts in object attributes against supvisors attributes. """
    for attr in lst:
        setattr(instance, attr, getattr(instance.supvisors, attr))


def simple_localtime(now=None):
    """ Returns the local time as a string, without the date. """
    if now is None:
        now = time()
    return strftime("%H:%M:%S", localtime(now))


def simple_gmtime(now=None):
    """ Returns the UTC time as a string, without the date. """
    if now is None:
        now = time()
    return strftime("%H:%M:%S", gmtime(now))


# Keys of information kept from Supervisor
__Payload_Keys = ('name', 'group', 'state', 'start', 'stop', 'now', 'pid', 'description', 'spawnerr')


def extract_process_info(info):
    """ Returns a subset of Supervisor process information. """
    payload = {key: info[key] for key in __Payload_Keys}
    # expand information with 'expected' (deduced from spawnerr)
    payload['expected'] = not info['spawnerr']
    return payload


# simple functions
def mean(x):
    return sum(x) / float(len(x))


def srate(x, y):
    return 100.0 * x / y - 100.0 if y else float('inf')


def stddev(lst, avg):
    return sqrt(sum((x - avg) ** 2 for x in lst) / len(lst))


# linear regression
def get_linear_regression(xdata, ydata):
    """ Calculate the coefficients of the linear equation corresponding
    to the linear regression of a series of points. """
    try:
        import numpy
        return tuple(numpy.polyfit(xdata, ydata, 1))
    except ImportError:
        # numpy not available
        # try something approximate and simple
        datasize = len(xdata)
        sum_x = float(sum(xdata))
        sum_y = float(sum(ydata))
        sum_xx = float(sum(map(lambda x: x * x, xdata)))
        sum_products = float(sum([xdata[i] * ydata[i]
                                  for i in range(datasize)]))
        a = (sum_products - sum_x * sum_y / datasize) / (sum_xx - (sum_x * sum_x) / datasize)
        b = (sum_y - a * sum_x) / datasize
        return a, b


def get_simple_linear_regression(lst):
    """ Calculate the coefficients of the linear equation corresponding
    to the linear regression of a series of values. """
    # in Supvisors, Y data is periodic
    datasize = len(lst)
    return get_linear_regression([i for i in range(datasize)], lst)


# get statistics from data
def get_stats(lst):
    """ Calculate the following statistics from a series of points:
    - the mean value,
    - the instant rate between the two last values,
    - the coefficients of the linear regression,
    - the standard deviation. """
    rate, a, b, dev = (None,) * 4
    # calculate mean value
    avg = mean(lst)
    if len(lst) > 1:
        # calculate instant rate value between last 2 values
        rate = srate(lst[-1], lst[-2])
        # calculate slope value from linear regression of values
        a, b = get_simple_linear_regression(lst)
        # calculate standard deviation
        dev = stddev(lst, avg)
    return avg, rate, (a, b), dev
