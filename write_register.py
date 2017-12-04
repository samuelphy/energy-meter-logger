#!/usr/bin/env python
import minimalmodbus

instrument = minimalmodbus.Instrument('/dev/ttyAMA0', 1) # port name, slave address (in decimal)
#instrument = minimalmodbus.Instrument('/dev/serial0', 1) # port name, slave address (in decimal)
instrument.debug = True

#instrument.serial.port          # this is the serial port name
instrument.serial.baudrate = 2400   # Baud
instrument.serial.bytesize = 8
instrument.serial.parity = minimalmodbus.serial.PARITY_EVEN
instrument.serial.stopbits = 1
instrument.serial.timeout  = 0.5   # seconds
#instrument.address     # this is the slave address number
instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode


# It needs to long press the button on meter last for 3 seconds to enter the set-up interface firstly,
# then the set-up can be realized via RS485 communication. After the set-up is finished,
# long press last for 3 seconds to exit the set-up interface
instrument.write_float(28, 2, 2) #Write Address=28, baudrate 2=9600, 2 registers)
