#!/usr/bin/python
#-*- coding: utf-8 -*-

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

from collections import OrderedDict
from socket import gethostname

from supervisor.datatypes import (boolean,
                                  integer,
                                  existing_dirpath,
                                  byte_size,
                                  logging_level,
                                  list_of_strings)
from supervisor.options import ServerOptions

from supvisors.ttypes import ConciliationStrategies, StartingStrategies


# Options of main section
class SupvisorsOptions():
    """ Holder of the Supvisors options.

    Attributes are:

        - address_list: list of host names or IP addresses where supvisors
        will be running,
        - rules_file: absolute or relative path to the XML rules file,
        - internal_port: port number used to publish local events to remote
        Supvisors instances,
        - event_port: port number used to publish all Supvisors events,
        - auto_fence: when True, Supvisors won't try to reconnect to a
        Supvisors instance that has been inactive,
        - synchro_timeout: time in seconds that Supvisors waits for all
        expected Supvisors instances to publish,
        - conciliation_strategy: strategy used to solve conflicts when
        Supvisors has detected that multiple instances of the same program
        are running,
        - starting_strategy: strategy used to start processes on addresses,
        - stats_periods: list of periods for which the statistics will be
        provided in the Supvisors web page,
        - stats_histo: depth of statistics history,
        - logfile: absolute or relative path of the Supvisors log file,
        - logfile_maxbytes: maximum size of the Supvisors log file,
        - logfile_backups: number of Supvisors backup log files,
        - loglevel: logging level,

        - procnumbers: a dictionary giving the number of the program in a
        homogeneous group.
    """

    _Options = ['address_list', 'rules_file', 'internal_port', 'event_port',
                'auto_fence', 'synchro_timeout', 'conciliation_strategy',
                'starting_strategy', 'stats_periods', 'stats_histo',
                'stats_irix_mode', 'logfile', 'logfile_maxbytes',
                'logfile_backups', 'loglevel']

    def __init__(self):
        """ Initialization of the attributes. """
        # option list
        for option in SupvisorsOptions._Options:
            setattr(self, option, None)
        # second parse
        self.procnumbers = {}

    def __str__(self):
        """ Contents as string. """
        return ('address_list={} rules_file={} internal_port={} event_port={} '
                'auto_fence={} synchro_timeout={} conciliation_strategy={} '
                'starting_strategy={} stats_periods={} stats_histo={} '
                'stats_irix_mode={} logfile={} logfile_maxbytes={} '
                'logfile_backups={} loglevel={}'.format(
                    self.address_list, self.rules_file, self.internal_port,
                    self.event_port, self.auto_fence, self.synchro_timeout,
                    self.conciliation_strategy, self.starting_strategy,
                    self.stats_periods, self.stats_histo, self.stats_irix_mode,
                    self.logfile, self.logfile_maxbytes, self.logfile_backups,
                    self.loglevel))


class SupvisorsServerOptions(ServerOptions):
    """ Class used to parse the options of the 'supvisors' section in the
    supervisor configuration file.

    Attributes are:

        - supvisors_options: the instance holding all Supvisors options,
        - _Section: constant for the name of the Supvisors section in the
        Supervisor configuration file.
    """

    _Section = 'supvisors'

    def __init__(self):
        """ Initialization of the attributes. """
        ServerOptions.__init__(self)
        self.supvisors_options = SupvisorsOptions()

    def _processes_from_section(self, parser, section, group_name, klass=None):
        """ This method is overriden to:
            - add attributes to prepare the extra args functionality
            - store the program number of a homogeneous program.
        This is originally used in Supervisor to set the real program name
        from the format defined in the ini file. However, Supervisor does not
        keep this information in its internal structure. """
        # call super behaviour
        programs = ServerOptions._processes_from_section(
            self, parser, section, group_name, klass)
        # store the number of each program
        for idx, program in enumerate(programs):
            self.supvisors_options.procnumbers[program.name] = idx
        # return original result
        return programs

    def server_configs_from_parser(self, parser):
        """ The following has nothing to deal with Supervisor's server
        configurations.
        It gets Supvisors configuration.
        Supervisor's ServerOptions has not been designed to be specialized.
        This method is overriden just to have an access point to the Supervisor
        parser. """
        configs = ServerOptions.server_configs_from_parser(self, parser)
        # set section
        if not parser.has_section(SupvisorsServerOptions._Section):
            raise ValueError('.ini file ({}) does not include a [{}] section'
                             .format(self.configfile, self._Section))
        temp, parser.mysection = parser.mysection, self._Section
        # get values
        opt = self.supvisors_options
        opt.address_list = list(OrderedDict.fromkeys(filter(
            None, list_of_strings(parser.getdefault('address_list',
                                                    gethostname())))))
        opt.rules_file = parser.getdefault('rules_file', None)
        if opt.rules_file:
            opt.rules_file = existing_dirpath(opt.rules_file)
        opt.internal_port = self.to_port_num(
            parser.getdefault('internal_port', '65001'))
        opt.event_port = self.to_port_num(
            parser.getdefault('event_port', '65002'))
        opt.auto_fence = boolean(
            parser.getdefault('auto_fence', 'false'))
        opt.synchro_timeout = self.to_timeout(
            parser.getdefault('synchro_timeout', '15'))
        opt.conciliation_strategy = self.to_conciliation_strategy(
            parser.getdefault('conciliation_strategy', 'USER'))
        opt.starting_strategy = self.to_starting_strategy(
            parser.getdefault('starting_strategy', 'CONFIG'))
        # configure statistics
        opt.stats_periods = self.to_periods(list_of_strings(
            parser.getdefault('stats_periods', '10')))
        opt.stats_histo = self.to_histo(
            parser.getdefault('stats_histo', 200))
        opt.stats_irix_mode = boolean(
            parser.getdefault('stats_irix_mode', 'false'))
        # configure logger
        opt.logfile = existing_dirpath(
            parser.getdefault('logfile', '{}.log'
                              .format(SupvisorsServerOptions._Section)))
        opt.logfile_maxbytes = byte_size(
            parser.getdefault('logfile_maxbytes', '50MB'))
        opt.logfile_backups = integer(
            parser.getdefault('logfile_backups', 10))
        opt.loglevel = logging_level(
            parser.getdefault('loglevel', 'info'))
        # reset mysection and return original result
        parser.mysection = temp
        return configs

    # conversion utils (completion of supervisor.datatypes)
    @staticmethod
    def to_port_num(value):
        """ Convert a string into a port number. """
        value = integer(value)
        if 0 < value <= 65535:
            return value
        raise ValueError('invalid value for port: %d. '
                         'expected in [1;65535]' % value)

    @staticmethod
    def to_timeout(value):
        """ Convert a string into a timeout value. """
        value = integer(value)
        if 0 < value <= 1000:
            return value
        raise ValueError('invalid value for synchro_timeout: %d. '
                         'expected in [1;1000] (seconds)' % value)

    @staticmethod
    def to_conciliation_strategy(value):
        """ Convert a string into a ConciliationStrategies enum. """
        strategy = ConciliationStrategies._from_string(value)
        if strategy is None:
            raise ValueError('invalid value for conciliation_strategy: {}. '
                             'expected in {}'.format(
                value, ConciliationStrategies._strings()))
        return strategy

    @staticmethod
    def to_starting_strategy(value):
        """ Convert a string into a StartingStrategies enum. """
        strategy = StartingStrategies._from_string(value)
        if strategy is None:
            raise ValueError('invalid value for starting_strategy: {}. '
                             'expected in {}'.format(
                value, StartingStrategies._strings()))
        return strategy

    @staticmethod
    def to_periods(value):
        """ Convert a string into a list of period values. """
        if len(value) == 0:
            raise ValueError('unexpected number of stats_periods: {}. '
                             'minimum is 1'.format(value))
        if len(value) > 3:
            raise ValueError('unexpected number of stats_periods: {}. '
                             'maximum is 3'.format(value))
        periods = []
        for val in value:
            period = integer(val)
            if 5 > period or period > 3600:
                raise ValueError('invalid value for stats_periods: {}. '
                                 'expected in [5;3600] (seconds)'.format(val))
            if period % 5 != 0:
                raise ValueError('invalid value for stats_periods: %d. '
                                 'expected multiple of 5' % period)
            periods.append(period)
        return sorted(filter(None, periods))

    @staticmethod
    def to_histo(value):
        """ Convert a string into a value of historic depth. """
        histo = integer(value)
        if 10 <= histo <= 1500:
            return histo
        raise ValueError('invalid value for stats_histo: {}. '
                         'expected in [10;1500] (seconds)'.format(value))
