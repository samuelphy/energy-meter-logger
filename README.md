# Energy Meter Logger
Log your Energy Meter data on a Raspberry Pi and plot graphs of your energy consumption.
Its been verified to work with a Raspberry Pi with a Linksprite RS485 shield and reading values from a WEBIQ131D / SDM120. By changing the meters.yml file and making a corresponding [model].yml file it should be possible to use other models.

### Requirements

#### Hardware

* Raspberry Pi 3
* RS485 Shield V3 for RPi:
http://linksprite.com/wiki/index.php5?title=RS485/GPIO_Shield_for_Raspberry_Pi_V3.0
* Modbus based Energy Meter, e.g WEBIQ 131D / Eastron SDM120 or WEBIQ 343L / Eastron SMD630

#### Software

* Rasbian
* Python 2.7 and PIP
* Minimalmodbus
* InfluxDB
* Grafana

### Prerequisite

* Download Raspbian Stretch Lite and Flash on SD-card, e.g. by using Etcher
https://www.raspberrypi.org/downloads/raspbian/
* Mount the RS485 shield on the Raspberry Pi’s GPIO header.
* Power up Rasberry Pi and setup password (passwd) and SSH, localization, network etc using sudo raspi-config
* With raspi-config open, go to “5 Interfacing Options” -> “P6 Serial” and disable serial login shell and Enable serial port hardware (NO and then YES)
* Add the following lines to /boot/config.txt'
```sh
# Disable built in Bluetooth
dtoverlay=pi3-miniuart-bt
```
source: http://www.briandorey.com/post/Raspberry-Pi-3-UART-Boot-Overlay-Part-Two

* To disable the serial console, you need to edit the /boot/cmdline.txt file to look like the following row
```sh
dwc_otg.lpm_enable=0 console=tty1 root=/dev/mmcblk0p2 rootfstype=ext4  elevator=deadline fsck.repair=yes rootwait
```
source: http://www.briandorey.com/post/Raspberry-Pi-3-UART-Boot-Overlay-Part-Two

* Install Python Package Manager PIP if not already installed (not installed on Rasbian Lite):
```sh
$ sudo apt-get install python-pip
```

### Installation
#### Install InfluxDB
source: https://docs.influxdata.com/influxdb/v1.3/introduction/installation/

#### Step-by-step instructions
* Add the InfluxData repository
```sh
$ curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add -
$ source /etc/os-release
$ test $VERSION_ID = "9" && echo "deb https://repos.influxdata.com/debian stretch stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
```

* Download and install
```sh
$ sudo apt-get update && sudo apt-get install influxdb
```
* Start the influxdb service
```sh
$ sudo service influxdb start
  $ sudo service influxdb restart
```

* Create the database
```sh
 $ sudo influx
 CREATE DATABASE db_meters
exit 
```

#### Install Grafana
source: http://docs.grafana.org/installation/debian/

##### Step-by-step instructions
* Add APT Repository
```sh
$ echo "deb https://dl.bintray.com/fg2it/deb-rpi-1b jessie main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
```

* Add Bintray key
```sh
$ curl https://bintray.com/user/downloadSubjectPublicKey?username=bintray | sudo apt-key add -
```

* Now install
```sh
$ sudo apt-get update
 $ sudo apt-get install grafana 
```

* Start the service using systemd:
```sh
$ sudo systemctl daemon-reload
$ systemctl start grafana-server
$ systemctl status grafana-server
```

* Enable the systemd service so that Grafana starts at boot.
```sh
$ sudo systemctl enable grafana-server.service
```
* Go to http://localhost:3000 and login using admin / admin (remember to change password)

#### Install Energy Meter Logger:
* Download and install from github
```sh
$ pip install git+https://github.com/samuelphy/energy-meter-logger
```
* Make script file executable
```sh
$ chmod 777 read_energy_meter.py
```

* Edit meters.yml to match your configuration
* Test the configuration by running:
```sh
./read_energy_meter.py
```
* Run the python script at startup
Add to following lines to the end of /etc/rc.local but before exit:
```sh
# Start Elphy Energy Meter Logger
/home/pi/read_energy_meter.py --interval 60 > /var/log/meter.log &
```
