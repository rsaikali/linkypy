# LinkyPy

![PEP8](https://github.com/rsaikali/linkypy/workflows/PEP8/badge.svg)
![Docker](https://github.com/rsaikali/linkypy/workflows/Docker/badge.svg)

`LinkyPy` is intended to grab Linky (french dedicated energy meter) information through RaspberryPi USB port.

Default behaviour is to store data in an InfluxDB database, but it can be used as a standalone library as you can implement your own callback function.

Retrieved data is computed accordingly to the Enedis specifications (packets, checksums...) available [here](https://www.enedis.fr/sites/default/files/Enedis-NOI-CPT_54E.pdf).

Have a look to my other Github project for an all-in-one RaspberryPi Kubernetes installer: [rsaikali/linkypy_k3s](https://github.com/rsaikali/linkypy_k3s). (this includes an easy to install LinkyPy, InfluxDB database and Grafana stack on your RaspberryPi).

## Hardware needed

1. A RaspberryPi, of course.

2. A Linky energy meter with Teleinfo pins.

<p align="center">
    <img src="https://pbs.twimg.com/media/DhwX-daX4AIdzMv.jpg" width="300" height="300">
</p>

3. A [µTeleInfo](http://hallard.me/utinfo/) dongle. It is plugged in the RaspberryPi through USB port and connected to the Teleinfo Linky pins.
The USB dongle is available on [Tindie](https://www.tindie.com/products/hallard/micro-teleinfo-v20/).

<p align="center">
    <img src="https://cdn.tindiemedia.com/images/resize/DCGyvSQz2JMzZUvVRCTSGKsgJ-4=/p/fit-in/1032x688/filters:fill(fff)/i/5857/products/2018-06-08T13%3A23%3A25.397Z-MicroTeleinfo_Top_V2.png" width="300">
</p>


## Make your own plugin

This is a sample plugin class, here we will print Linky information:

```python
class MyPlugin(object):

    def compute(self, data, timestamp):
        print(timestamp)
        for key, value in data.items():
            print(f"{key} = {value}")
```

Then add your plugin declaration in the configuration file `/etc/linkypy/linkypy.yaml`:

```yaml
linkypy:

    (...)

    callbacks:
        - linkypy.callbacks.influxdb_plugin.InfluxDBPlugin
        - your_package.MyPlugin

    (...)
```

You can now launch `linkypy`:

```sh
linkypy run
```

```sh
(...)
2020-11-21 12:45:11,823
ADCO     = 012345678901
OPTARIF  = HC..
ISOUSC   = 45
HCHC     = 005602128
HCHP     = 007923975
PTEC     = HP..
IINST    = 001
IMAX     = 090
PAPP     = 00460
HHPHC    = A
MOTDETAT = 000000
(...)
```

Detailed description of fields is available in the [Enedis documentation](https://www.enedis.fr/sites/default/files/Enedis-NOI-CPT_54E.pdf).

## Default InfluxDB behaviour

Default callback will store data into an InfluxDB database.

Once installed, simply run the following command to launch the daemon:

```sh
linkypy run
```

Connection information is configured through environment variables:

```sh
export INFLUXDB_SERVICE_HOST=influxdb.local
export INFLUXDB_SERVICE_PORT=8086
export INFLUXDB_DATABASE=linky
export INFLUXDB_USERNAME=admin
export INFLUXDB_PASSWORD=password
````

Only valuable information is stored:

- `HCHP`: High price hours (heures pleines) values (in kWh).
- `HCHC`: Low price hours (heures creuses) values (in kWh).
- `PAPP`: Instant power delivered (in VA, but I personnaly assume it's watts, yes, even if it's not true that's enough for my understanding).

Price calculation and estimation for current month will also be stored.

Prices are now extracted from energy providers websites (PDF).

In my scenario, I use Grafana next to InfluxDB to visualize stored data.
Have a look to my other Github project for an all-in-one RaspberryPi Kubernetes installer: [rsaikali/linkypy_k3s](https://github.com/rsaikali/linkypy_k3s). This includes LinkyPy, InfluxDB database and Grafana:

<p align="center">
    <img src="https://raw.githubusercontent.com/rsaikali/linkypy/main/img/grafana-screenshot.jpg" width="100%">
</p>

## Docker build

Current project is available as a Docker image in [rsaikali/linkypy](https://hub.docker.com/repository/docker/rsaikali/linkypy)

To build your own `linux/arm/v7` docker image from another architecture, you'll need a special (experimental) Docker multi-architecture build functionality detailled here: [Building Multi-Arch Images for Arm and x86 with Docker Desktop](https://www.docker.com/blog/multi-arch-images/)

You'll basically need to activate experimental features and use `buildx`.

```sh
export DOCKER_CLI_EXPERIMENTAL=enabled
docker buildx create --use --name build --node build --driver-opt network=host
docker buildx build --platform linux/arm/v7 -t <your-repo>/linkypy --push .
```

## Credits

Thank you to Charles (https://github.com/hallard) for the µTeleInfo USB dongle and documentation.