#!/usr/bin/env python

from influxdb import InfluxDBClient
from datetime import datetime, timedelta
from os import path
import sys
import os
import minimalmodbus
import time
import yaml

# Change working dir to the same dir as this script
os.chdir(sys.path[0])

class DataCollector:
    def __init__(self, influx_client, meter_yaml):
        self.influx_client = influx_client
        self.meter_yaml = meter_yaml
        self.max_iterations = None  # run indefinitely by default
        self.meter_map = None
        self.meter_map_last_change = -1
        print 'Meters:'
        for meter in sorted(self.get_meters()):
            print '\t', meter['id'], '<-->', meter['name']

    def get_meters(self):
        assert path.exists(self.meter_yaml), 'Meter map not found: %s' % self.meter_yaml
        if path.getmtime(self.meter_yaml) != self.meter_map_last_change:
            try:
                print('Reloading meter map as file changed')
                new_map = yaml.load(open(self.meter_yaml))
                self.meter_map = new_map['meters']
                self.meter_map_last_change = path.getmtime(self.meter_yaml)
            except Exception as e:
                print('Failed to re-load meter map, going on with the old one. Error:')
                print(e)
        return self.meter_map

    def collect_and_store(self):
        meters = self.get_meters()
        t_utc = datetime.utcnow()
        t_str = t_utc.isoformat() + 'Z'

        instrument = minimalmodbus.Instrument('/dev/ttyAMA0', 1) # port name, slave address (in decimal)
        instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
        #instrument.debug = True
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
                print('Error! No parity specified')
                raise
            instrument.serial.stopbits = meter['stopbits']
            instrument.serial.timeout  = meter['timeout']    # seconds
            instrument.address = meter['id']    # this is the slave address number

            #print 'Reading meter %s (%s).' % (meters[meter_id], meter_id)

            assert path.exists(meter['type']), 'Meter model yaml file not found: %s' % meter['type']
            try:
                parameters = yaml.load(open(meter['type']))
            except Exception as e:
                print('Error! Loading model yaml file')
                print(e)
                raise

            start_time = time.time()
            datas[meter['id']] = dict()

            for parameter in parameters:
                try:
                    datas[meter['id']][parameter] = instrument.read_float(parameters[parameter], 4, 2)
                    pass
                except Exception as e:
                    print('Reading register %i from meter %i. Error:' % parameters[parameter], meter['id'])
                    print(e)
                    raise

            datas[meter['id']]['Time to read'] =  time.time() - start_time

        json_body = [
            {
                'measurement': 'energy',
                'tags': {
                    'id': meter_id,
                    'meter': meter['name'],
                },
                'time': t_str,
                'fields': datas[meter_id]
            }
            for meter_id in datas
        ]
        if len(json_body) > 0:
            try:
                self.influx_client.write_points(json_body)
                print(t_str + ' Data written for %d meters.' % len(json_body))
            except Exception as e:
                print('Data not written! Error:')
                print(e)
                raise
        else:
            print(t_str, 'No data sent.')


def repeat(interval_sec, max_iter, func, *args, **kwargs):
    from itertools import count
    import time
    starttime = time.time()
    retry = False
    for i in count():
        if (retry == False) & (interval_sec > 0):
            time.sleep(interval_sec - ((time.time() - starttime) % interval_sec))
        retry = False # Reset retry flag
        if i % 1000 == 0:
            print('Collected %d readouts' % i)
        try:
            func(*args, **kwargs)
        except Exception as ex:
            print('Error!')
            print(ex)
            retry = True # Force imidiate retry, skip sleep

        if max_iter and i >= max_iter:
            return


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--interval', default=60,
                        help='Meter readout interval (seconds), default 60')
    parser.add_argument('--meters', default='meters.yml',
                        help='YAML file containing Meter ID, name, type etc. Default "meters.yml"')
    args = parser.parse_args()
    interval = int(args.interval)

    # Create the InfluxDB object
    influx_config = yaml.load(open('influx_config.yml'))
    client = InfluxDBClient(influx_config['host'],
                            influx_config['port'],
                            influx_config['user'],
                            influx_config['password'],
                            influx_config['dbname'])

    collector = DataCollector(influx_client=client,
                              meter_yaml='meters.yml')

    repeat(interval,
           max_iter=collector.max_iterations,
           func=lambda: collector.collect_and_store())
