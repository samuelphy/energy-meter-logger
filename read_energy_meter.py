#!/usr/bin/env python

from influxdb import InfluxDBClient
from datetime import datetime, timedelta
from os import path
import sys
import os
import minimalmodbus
import time
import yaml
import logging

# Change working dir to the same dir as this script
os.chdir(sys.path[0])

class DataCollector:
    def __init__(self, influx_client, meter_yaml):
        self.influx_client = influx_client
        self.meter_yaml = meter_yaml
        self.max_iterations = None  # run indefinitely by default
        self.meter_map = None
        self.meter_map_last_change = -1
        log.info('Meters:')
        for meter in sorted(self.get_meters()):
            log.info('\t {} <--> {}'.format( meter['id'], meter['name']))

    def get_meters(self):
        assert path.exists(self.meter_yaml), 'Meter map not found: %s' % self.meter_yaml
        if path.getmtime(self.meter_yaml) != self.meter_map_last_change:
            try:
                log.info('Reloading meter map as file changed')
                new_map = yaml.load(open(self.meter_yaml))
                self.meter_map = new_map['meters']
                self.meter_map_last_change = path.getmtime(self.meter_yaml)
            except Exception as e:
                log.warning('Failed to re-load meter map, going on with the old one.')
                log.warning(e)
        return self.meter_map

    def collect_and_store(self):
        #instrument.debug = True
        meters = self.get_meters()
        t_utc = datetime.utcnow()
        t_str = t_utc.isoformat() + 'Z'

        instrument = minimalmodbus.Instrument('/dev/ttyAMA0', 1) # port name, slave address (in decimal)
        instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
        datas = dict()
        meter_id_name = dict() # mapping id to name

        for meter in meters:
            meter_id_name[meter['id']] = meter['name']
            instrument.serial.baudrate = meter['baudrate']
            instrument.serial.bytesize = meter['bytesize']
            if meter['parity'] == 'none':
                instrument.serial.parity = minimalmodbus.serial.PARITY_NONE
            elif meter['parity'] == 'odd':
                instrument.serial.parity = minimalmodbus.serial.PARITY_ODD
            elif meter['parity'] == 'even':
                instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
            else:
                log.error('No parity specified')
                raise
            instrument.serial.stopbits = meter['stopbits']
            instrument.serial.timeout  = meter['timeout']    # seconds
            instrument.address = meter['id']    # this is the slave address number

            log.debug('Reading meter %s.' % (meter['id']))
            start_time = time.time()
            parameters = yaml.load(open(meter['type']))
            datas[meter['id']] = dict()

            for parameter in parameters:
                # If random readout errors occour, e.g. CRC check fail, test to uncomment the following row
                #time.sleep(0.01) # Sleep for 10 ms between each parameter read to avoid errors
                retries = 10
                while retries > 0:
                    try:
                        retries -= 1
                        datas[meter['id']][parameter] = instrument.read_float(parameters[parameter], 4, 2)
                        retries = 0
                        pass
                    except ValueError as ve:
                        log.warning('Value Error while reading register {} from meter {}. Retries left {}.'
                               .format(parameters[parameter], meter['id'], retries))
                        log.error(ve)
                        if retries == 0:
                            raise RuntimeError
                    except TypeError as te:
                        log.warning('Type Error while reading register {} from meter {}. Retries left {}.'
                               .format(parameters[parameter], meter['id'], retries))
                        log.error(te)
                        if retries == 0:
                            raise RuntimeError
                    except IOError as ie:
                        log.warning('IO Error while reading register {} from meter {}. Retries left {}.'
                               .format(parameters[parameter], meter['id'], retries))
                        log.error(ie)
                        if retries == 0:
                            raise RuntimeError
                    except:
                        log.error("Unexpected error:", sys.exc_info()[0])
                        raise

            datas[meter['id']]['Read time'] =  time.time() - start_time

        json_body = [
            {
                'measurement': 'energy',
                'tags': {
                    'id': meter_id,
                    'meter': meter_id_name[meter_id],
                },
                'time': t_str,
                'fields': datas[meter_id]
            }
            for meter_id in datas
        ]
        if len(json_body) > 0:
            try:
                self.influx_client.write_points(json_body)
                log.info(t_str + ' Data written for %d meters.' % len(json_body))
            except Exception as e:
                log.error('Data not written!')
                log.error(e)
                raise
        else:
            log.warning(t_str, 'No data sent.')


def repeat(interval_sec, max_iter, func, *args, **kwargs):
    from itertools import count
    import time
    starttime = time.time()
    for i in count():
        if interval_sec > 0:
            time.sleep(interval_sec - ((time.time() - starttime) % interval_sec))
        if i % 1000 == 0:
            log.info('Collected %d readouts' % i)
        try:
            func(*args, **kwargs)
        except Exception as ex:
            log.error(ex)
        if max_iter and i >= max_iter:
            return


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', default=60,
                        help='Meter readout interval (seconds), default 60')
    parser.add_argument('--meters', default='meters.yml',
                        help='YAML file containing Meter ID, name, type etc. Default "meters.yml"')
    parser.add_argument('--log', default='CRITICAL',
                        help='Log levels, DEBUG, INFO, WARNING, ERROR or CRITICAL')
    parser.add_argument('--logfile', default='',
                        help='Specify log file, if not specified the log is streamed to console')
    args = parser.parse_args()
    interval = int(args.interval)
    loglevel = args.log.upper()
    logfile = args.logfile

    # Setup logging
    log = logging.getLogger('energy-logger')
    log.setLevel(getattr(logging, loglevel))

    if logfile:
        loghandle = logging.FileHandler(logfile, 'w')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        loghandle.setFormatter(formatter)
    else:
        loghandle = logging.StreamHandler()

    log.addHandler(loghandle)

    log.info('Started app')

    # Create the InfluxDB object
    influx_config = yaml.load(open('influx_config.yml'))
    client = InfluxDBClient(influx_config['host'],
                            influx_config['port'],
                            influx_config['user'],
                            influx_config['password'],
                            influx_config['dbname'])

    collector = DataCollector(influx_client=client,
                              meter_yaml=args.meters)

    repeat(interval,
           max_iter=collector.max_iterations,
           func=lambda: collector.collect_and_store())
