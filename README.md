# Energy Meter Logger
Log your Energy Meter data on a Raspberry Pi and plot graphs of your energy consumption.
Its been verified to work with a Raspberry Pi with a Linksprite RS485 shield or with generic cheap USB convertor and reading values from WEBIQ131D / SDM120 and WEBIQ343L / SDM630. By changing the meters.yml file and making a corresponding [model].yml file it should be possible to use other modbus enabled models.

### Requirements

#### Hardware

* Raspberry Pi 3
* [Linksprite RS485 Shield V3 for RPi](http://linksprite.com/wiki/index.php5?title=RS485/GPIO_Shield_for_Raspberry_Pi_V3.0)
* OR
* cheap generic USB convertor (like this one https://a.aliexpress.com/_ufjPgJ) 
* Modbus based Energy Meter, e.g WEBIQ 131D / Eastron SDM120 or WEBIQ 343L / Eastron SMD630

#### Software

* Rasbian
* Python 2.7 and PIP
* [Minimalmodbus](https://minimalmodbus.readthedocs.io/en/master/)
* [InfluxDB](https://docs.influxdata.com/influxdb/v1.3/)
* [Grafana](http://docs.grafana.org/)

### Prerequisite

This project has been documented at [Hackster](https://www.hackster.io/samuelphy/energy-meter-logger-6a3468). Please follow the instructions there for more detailed information.

### Installation
#### Install InfluxDB*

##### Step-by-step instructions
* Add the InfluxData repository (change the debian release accoring to one you use, below is for buster)
    ```sh
    $ curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add -
    $ source /etc/os-release
    $ sudo test $VERSION_ID = "10" && echo "deb https://repos.influxdata.com/debian buster stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
    ```
* Download and install
    ```sh
    $ sudo apt-get update && sudo apt-get install influxdb
    ```
* Unmask the influxdb service
    ```sh
    $ sudo systemctl unmask influxdb.service
    ```
* Start the influxdb service
    ```sh
    $ sudo systemctl start influxdb
    ```
* Create the database
    ```sh
    $ influx
    CREATE DATABASE db_meters
    exit
    ```
[*source](https://docs.influxdata.com/influxdb/v1.3/introduction/installation/)

#### Install Grafana*

##### Step-by-step instructions
* Add APT Repository and key
    ```sh
    sudo apt-get install -y apt-transport-https
    sudo apt-get install -y software-properties-common wget
    wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
    ```
* Add Repository to package manager for stable channel
    ```sh
    echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee -a /etc/apt/sources.list.d/grafana.list
    ```
* Now install
    ```sh
    $ sudo apt-get update && sudo apt-get install grafana
    ```
* Start the service using systemd:
    ```sh
    $ sudo systemctl daemon-reload
    $ sudo systemctl start grafana-server
    $ systemctl status grafana-server
    ```
* Enable the systemd service so that Grafana starts at boot.
    ```sh
    $ sudo systemctl enable grafana-server.service
    $ sudo service grafana-server start
    $ sudo service grafana-server status
    $ sudo update-rc.d grafana-server defaults
    ```
* Go to http://localhost:3000 and login using admin / admin (remember to change password)
[*source](http://docs.grafana.org/installation/debian/)

#### Install Energy Meter Logger:
* Download and install from Github
    ```sh
    $ git clone https://github.com/Dulus0/energy-meter-logger
    ```
* Run setup script (must be executed as root (sudo) if the application needs to be started from rc.local, see below)
    ```sh
    $ cd energy-meter-logger
    $ sudo python setup.py install
    ```    
* Make script file executable
    ```sh
    $ chmod 777 read_energy_meter.py
    ```
* Edit meters.yml to match your configuration
* Test the configuration by running:
    ```sh
    ./read_energy_meter.py
    ./read_energy_meter.py --help # Shows you all available parameters
    ```
* To run the python script at system startup. Add to following lines to the end of /etc/rc.local but before exit:
    ```sh
    # Start Energy Meter Logger
    /home/pi/energy-meter-logger/read_energy_meter.py --interval 60 > /var/log/energy_meter.log &
    ```
    Log with potential errors are found in /var/log/energy_meter.log
