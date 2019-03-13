# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 21:57:23 2019

@author: Tristan Steele, tristan.steele@adfa.edu.au
"""

import serial.tools.list_ports
import serial

import time

from telnetlib import Telnet
import requests


class AdauraAttenuator(object):
    """A class representing an Attenuator"""
    
    CONN_USB = "USB"
    CONN_TELNET = "TELNET"
    CONN_HTTP = "HTTP"
    
    @staticmethod
    def find_attenuators():
        ADAURA_TECH_VID = 0x04D8
        ADAURA_TECH_PID = 0xEEF5
        
        found_serial_numbers = []
        
        for pinfo in serial.tools.list_ports.comports():
            if pinfo.vid == ADAURA_TECH_VID and pinfo.pid == ADAURA_TECH_PID:
                found_serial_numbers.append((pinfo.serial_number, pinfo.device))

        return found_serial_numbers        
    
    @staticmethod    
    def find_attenuator(requested_serial):
        found_attenuators = ADAURAAttenuator.find_attenuators()
        
        for _serial_number, device in found_attenuators:
            if _serial_number == requested_serial.upper():
                return (_serial_number, device)
        
        #Not found
        raise IOError('Could not find device with provided serial number.')
        
    
    
    def __init__(self, serial_number=None, baudrate=115200, 
                 connection=CONN_USB, ip_address=None, comport=None):
        """
                
        Parameters
        ----------
        serial_number: string, The requested device's serial number. Used to find a serial port or confirm the connection on a remote device.
        baudrate: int, Baud rate such as 9600 or 115200 etc. Default is 115200
        connection: An identifier to determine what type of connection is required.
        ip_address: string, representing the IP of the remote device.
        """
        
        self.serial_number = serial_number
        
        self._connection_type = connection
        
        self.status = None
        
        
        #### SET UP IF WE ARE CONNECTED OVER USB
        if self._connection_type is self.CONN_USB:
            if comport is None and serial_number is not None:
                # Find a comport given the serial number
                self.comport = ADAURAAttenuator.find_attenuator(serial_number)
            
            elif comport is not None:
                # Open a serial  
                self.comport = comport
                
            else:
                raise Exception("USB Connection requested but no serial number or comport provided.")
        
            self.location = comport
            
            # Set up a serial port object
            try:
                self._serial = serial.Serial(self.comport, baudrate, timeout=5)
                self._serial.rts = False
            except Exception as ex:
                self.handle_serial_error(ex)

        #### SET UP IF WE ARE CONNECTED OVER ETHERNET            
        if self._connection_type is self.CONN_TELNET:
            assert ip_address is not None
            
            # Connect to a remote IP address to control the attenuator.
            self._telnet = Telnet(host = ip_address, port = 23)
            
            # Authenticate
            self._telnet.read_until(b"Login: ")
            self._telnet.write('admin'.encode('ascii') + b"\n")
    
            self._telnet.read_until(b"Password: ")
            self._telnet.write('adaura'.encode('ascii') + b"\n")
            
            time.sleep(1)
            
            # Read the data in the buffer to flush it.
            self.device_flush_buffer()
            
            self.location = ip_address
            
        if self._connection_type is self.CONN_HTTP:
            # Use HTTP Requests to interact with the Attenuator
            assert ip_address is not None
            
            self.location = 'http://{}'.format(ip_address)
            self._base_url = self.location
            
    
    def __del__(self):
        """Destructor"""
        try:
            self.close()
        except:
            pass # errors on shutdown
    
    def __str__(self):
        return "ADAURA Attenuator SRN: {}@:{}".format(self.serial_number, self.location)
    
    
    def _extract_from_info_string(self, query_string):
        """
        A helper function to 
        """
        assert self._info_raw_response is not None
        
        return [n.split(': ')[1].strip() for n in self._info_raw_response if query_string in n][0]

       
    def get_info(self):
        """
        Get the current device information
        """
        
        self.send_command('info')
        
        # read 16 lines from the device
        responses = self.receive_response(16)
        
        # Store raw response against object
        self._info_raw_response = responses
        
        #print(responses)
        
        response_dict = {}
        
        response_dict['model'] = self._extract_from_info_string('Model: ')
        response_dict['sn'] = self._extract_from_info_string('SN: ')
        response_dict['fw_ver'] = self._extract_from_info_string('FW Ver: ')
        response_dict['fw_date'] = self._extract_from_info_string('FW Date: ')
        response_dict['bl_ver'] = self._extract_from_info_string('BL Ver: ')
        response_dict['mfg_date'] = self._extract_from_info_string('MFG Date: ')
        response_dict['default_attenuations'] = self._extract_from_info_string('Default Attenuations: ').split(" ")
        
        response_dict['ip_address'] = self._extract_from_info_string('IP Address: ')
        response_dict['ip_subnet'] = self._extract_from_info_string('Subnet: ')
        response_dict['ip_gateway'] = self._extract_from_info_string('Gateway: ')
        response_dict['ip_dhcp'] = self._extract_from_info_string('DHCP: ')
        
        if response_dict['ip_address'] == 'not connected':
            response_dict['ip_address'] = '0.0.0.0'
            
        self.serial_number = response_dict['sn']
        
        self.info = response_dict
        
        return response_dict
        

    def get_status(self):
        """
        Get the current attenuation on all channels
        """
        self.send_command('status')
        
        response = self.receive_response(4)
        
        channel_values = []
        
        for ch in range(1,5): # Loop from 1...4
            this_channel = [n.split(': ')[1].strip() for n in response if 'Channel {}: '.format(ch) in n]
            
            if len(this_channel) > 0:
                channel_values.append(this_channel[0])
        
        self.status = [float(v) for v in channel_values]
        return channel_values
        
    
    def set_attenuator(self, channel, value):
        """
        Set the attenuation on a channel, checking that the response was correct.
        """
        
        tx_string = "set {0} {1}".format(channel, value)
        
        self.send_command(tx_string)
        
        # Get a line of response to determine if it was succesful
        response_one = self.receive_response(1)
        
        # Determine if running an integer value, as the format changes.
        if value % 1 is 0:
            # An integer value
            string_val = "{0:.1f}".format(value)
        else:
            string_val = "{0:.2f}".format(value)
        
        expected_response = "Channel {0} successfully set to {1}".format(channel,string_val)
        
        if not any([expected_response in l for l in response_one]):
            # Wasn't succesful, therefore error.
            raise IOError('Invalid attenuation specified.')
        else:    
            # Was succesful, flush the remainder of the response
            self.device_flush_buffer()
            
    
    
    def send_command(self, command):
        """
        Send command to serial port
        """
        if self._connection_type is self.CONN_USB:
            
            if self._serial.is_open:
                try:
                    self._serial.flushInput()
                    # Unicode strings must be encoded
                    data = command.encode('utf-8')
                    self._serial.write(data)
                except Exception as ex:
                    self.handle_serial_error(ex)
            else:
                raise IOError('Try to send data when the connection is closed')
                
        elif self._connection_type is self.CONN_TELNET:
            
            send_command = command + '\n'
            
            self._telnet.write(send_command.encode('utf-8'))
            
        elif self._connection_type is self.CONN_HTTP:
            
            self._http_response = None
            
            cmd_resp = requests.get('{0}/execute.php?{1}'.format(self._base_url, command))
    
            self._http_response = cmd_resp.text
    
    def receive_response(self, num_lines = 16):
        """
        Read back data
        """
        
        assert num_lines <= 16, "No more than 16 lines can be requested"
        
        receive_lines = []
        
        call_time = time.time()
        
        if self._connection_type is self.CONN_USB and self._serial.is_open or self._connection_type is self.CONN_TELNET:
            while True:
                try:
                    response = self.device_read_line()
                    receive_lines.append(response.decode())
                    
                    # Sleep if no data has been received
                    if response == "":
                        time.sleep(0.1)
                
                    if len(receive_lines) >= num_lines + 1:
                        return receive_lines
                    
                    # Check how long this has been running for
                    run_time = time.time() - call_time
                    if run_time > 5:
                        return receive_lines
                    
                except:
                    # Ignore the error, just return it all
                    return receive_lines
                
        elif self._connection_type is self.CONN_HTTP:
            # the response is already stored
            return self._http_response.split('\r\n')

    def device_read_line(self):
        if self._connection_type is self.CONN_USB:
            return self._serial.readline()
        
        elif self._connection_type is self.CONN_TELNET:
            return self._telnet.read_until(b'\n', timeout = 5)
        
    def device_flush_buffer(self):
        if self._connection_type is self.CONN_USB:
            self._serial.flushInput()
        
        elif self._connection_type is self.CONN_TELNET:
            self._telnet.read_very_eager()

                
    def handle_serial_error(self, error=None):
        """
        Serial port error
        """
        # terminate connection
        try:
            self._serial.close()
        except:
            pass
        # forward exception
        if isinstance(error, Exception):
            raise error # pylint: disable-msg=E0702
    
    def close(self):
        """
        Close all resources
        """
        if self._connection_type is self.CONN_USB:
            self._serial.close()
        elif self._connection_type is self.CONN_TELNET:
            self._telnet.close()
    
        
if __name__ == "__main__":
    #Some example code if running this directly.
    
    print("Found the following attenuators:")
    found_attenuators = AdauraAttenuator.find_attenuators()
    print(found_attenuators)
    print("")
    
    # Automatically open a serial attenuator if found.
    if len(found_attenuators) is 1:
       found_attenuator = found_attenuators[0]
        attenuator = ADAURAAttenuator(serial_number=found_attenuator[0],
                                      comport = found_attenuator[1],
                                      )
    
    
    #HTTP Connection
    #attenuator = AdauraAttenuator(ip_address='111.111.111.111', 
    #                              connection=AdauraAttenuator.CONN_HTTP,
    #                                  )
    
    # Telnet Connection
    #attenuator = AdauraAttenuator(ip_address='111.111.111.111', 
    #                              connection=AdauraAttenuator.CONN_TELNET,
    #                                  )
    
    info = attenuator.get_info()
    status = attenuator.get_status()
    
    attenuator.set_attenuator(1, 3)