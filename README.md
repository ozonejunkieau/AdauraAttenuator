# Adaura Technologies 

This is a basic Python 3 library for the Adaura Technologies Programmable RF Attenuators. https://adauratech.com/attenuators/

At this time it has only been tested against a AD-USB4AR36G95 running Firmware version 1.21.

Some of the codebase is based upon example code provided at https://adauratech.com/attenuators/python-example/, but it has generally been rewritten as a Python module. It also has support for connecting via Serial, Telnet or using the HTTP interface. I'm unsure on how the firmware changes are likely to break functionality, but at this time I'd suggest that the HTTP interface is more robust than the Telnet interface.

## Installation
I've not put this on `pip`, but it should be compatible with an SCM pip installation:

```
pip install git+https://github.com/ozonejunkieau/AdauraAttenuator.git
```

The `requirements.txt` file is generated based upon the version of packages I have installed, it is highly likely that older versions will work.

## Usage
```
import AdauraAttenuator
```
### Using the Serial Interface
Get a list of all attenuators found on the local USB bus, returned as a (serial, device) tuple.
```
found_attenuators = AdauraAttenuator.find_attenuators()
```
Automatically open a serial attenuator if found.
```
if len(found_attenuators) is 1:
    found_attenuator = found_attenuators[0]
    attenuator = ADAURAAttenuator(serial_number=found_attenuator[0],
                                    comport = found_attenuator[1],
                                    )
```
### Using the Telnet Interface
```
attenuator = AdauraAttenuator(ip_address='111.111.111.111', 
                              connection=AdauraAttenuator.CONN_TELNET)
```

### Using the HTTP Interface
```
attenuator = AdauraAttenuator(ip_address='111.111.111.111', 
                              connection=AdauraAttenuator.CONN_HTTP)
```

### Get the attenuator information
```
info = attenuator.get_info()
```
`info` returns a dictionary as follows:
```
{'model': 'AD-USB4AR36G95',
 'sn': 'Rxxxxxxxx',
 'fw_ver': '1.21',
 'fw_date': '21/02/2019',
 'bl_ver': '3.00',
 'mfg_date': 'DEC2018',
 'default_attenuations': ['95.0', '95.0', '95.0', '95.0'],
 'ip_address': 'xxx.xxx.xxx.xxx',
 'ip_subnet': '255.255.255.0',
 'ip_gateway': 'xxx.xxx.xxx.xxx',
 'ip_dhcp': 'Enabled'}
```
### Get the status of the attenuator
```
status = attenuator.get_status()
```
`status` returns a list of channel attenuations as follows:
```
[3.0, 95.0, 95.0, 95.0]
```
### Set the attenuation on a channel
```
attenuator.set_attenuator(1,20)
```
If no error is raised, the process was succesful. Trying to set either an invalid channel or an invalid attenuation will result in:
```
OSError: Invalid attenuation specified.
```

## Known Limitations
At the moment, there appears to be no way to dynamically discover the number of channels in the attenuator, so it is assumed to be 4. 

Error trapping, logging, etc is minimalist.