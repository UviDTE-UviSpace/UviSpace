#!/usr/bin/env python
"""This module contains the Client class, which inherits from socket.socket

* socket.socket class source code can be found in the following link:
  https://hg.python.org/cpython/file/2.7/Lib/socket.py
* Previous class is a child of the _socket.socket class. 
  Its source code can be found in the following link:
  https://github.com/biosbits/bits/blob/master/python/_socket.py

"""
# Standard libraries
import ast
import errno
import logging
import socket
from socket import socket as Socket
import sys

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger("sensor")


class Client(Socket):
    """Child class of socket.socket which includes register operations.
    
    It is intended to work with registers of an external FPGA. The 
    register identifiers must correspond with the ones of the
    HDL circuit implemented in the FPGA.
    
    Used methods from parent class:
    
    * connect((host, port)): connects to specified remote address
    * close(): close the socket opened with the client
    * send(data): send data to the client
    * recv(buflen): read the specified number of bytes
    * settimeout(timeout): time to wait for the client to respond

    :param int buffer_size: number of bytes of the incoming data.
    :param timeout: value, in seconds, of the time that will be waited 
     for reading incoming data. This will set the object to timeout mode
     (By default, it is set to blocking mode).
    :type timeout: int or float

    The class has 2 dictionaries, _REGISTERS and _COMMANDS, that contain
    all the valid commands that can be sent to the FPGA and the declared
    registers inside it. When interacting with the FPGA, can only be 
    accessed the commands and registers in these dictionaries.

    **Registers**
    
    * *RED/GREEN/BLUE_THRESHOLD*: The pixel intensity thresholds for 
      each of the 3 colors are stored in these registers, in the form of
      (low_threshold, high_threshold).
    * *IMAGE_SHAPE*:
    * ...
    """
    # Allowed register values
    _REGISTERS = {'RED_THRESHOLD': 'rt',
                  'GREEN_THRESHOLD': 'gt',
                  'BLUE_THRESHOLD': 'bt',
                  'IMAGE_SHAPE': 'is',
                  'IMAGE_EXPOSURE': 'ie',
                  'START_INDEXES': 'si',
                  'SYSTEM_SHAPE': 'ss',
                  'SYSTEM_MODES': 'sm',
                  'SYSTEM_OUTPUT': 'so',
                  'TRACKER_RESOURCES': 'tr',
                  'ACTIVATE_TRACKER': 'at',
                  'DEACTIVATE_TRACKER': 'dt',
                  'FREE_TRACKER': 'ft',
                  'FREE_ALL': 'fa',
                  'ACTUAL_LOCATION': 'al',
                  'ACTIVE_WINDOWS': 'aw',
                  'SET_WINDOW': 'sw'}
    # Allowed command values
    _COMMANDS = {'CLOSE_CONNECTION': 'Q',
                 'CONFIGURE_CAMERA': 'C',
                 'SET_VGA_OUTPUT': 'V',
                 'GET_GRAY_IMAGE': 'G',
                 'GET_COLOR_IMAGE': 'D',
                 'GET_NEW_FRAME': 'S'}

    def __init__(self, buffer_size=2048, timeout=2.0):
        """Class constructor. Set attributes, inheritance and logger."""
        # Initializes parent class
        Socket.__init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM)
        # Connection parameters for the client device
        self.ip = ''
        self.port = None
        self.buffer_size = buffer_size
        # Call parent method for setting the timeout
        self.settimeout(timeout)

    def close_connection(self):
        """Send 'CLOSE_CONNECTION' command to FPGA and close TCP/IP socket."""
        # Check parent class _sock variable,
        # as it changes its class when it is closed.
        # WARNING: not valid method for Python3.
        if not isinstance(self._sock, socket._closedsocket):
            self.write_command('CLOSE_CONNECTION')
            self.close()
            logger.info('Closed the TCP client {}'.format(75 * '-'))
        else:
            logger.debug('Unable to close TCP client. Already closed')

    def open_connection(self, ip, port):
        """Create a TCP/IP socket connection.

        After connecting, the input buffer is read in order to remove 
        its contents, as a 'Welcome message' is automatically generated.

        :param str ip: IP address of the device.

        :param int port: socket port.
        """
        self.ip = ip
        self.port = port
        self.connect((self.ip, self.port))
        logger.info('Started TCP client with IP: {} and PORT:{}.'.format(
                self.ip, self.port))
        # Empty the data buffer, as it contains the 'welcome message'.
        self.recv(self.buffer_size)

    def read_data(self, size):
        """Perform the input buffer read operation several times.

        :param int size: indicates number of bytes to be read.

        :return: A data concatenation of all packages read from the 
         input buffer.
        """
        bytes = 0
        packages = []
        # Do not stop reading new packages until target 'size' is reached.
        while bytes < size:
            try:
                received_package = self.recv(self.buffer_size)
            except socket.timeout:
                amount = 100 * float(bytes) / size
                logger.warn('Stopped data acquisition with {:.2f}% '
                            'of the data acquired'.format(amount))
                break
            bytes += len(received_package)
            packages.append(received_package)
        logger.debug('Received {} bytes of {} ({:.2f}%)'.format(
                bytes, size, (100 * float(bytes) / size)))
        # Concatenate all the packages in a unique variable
        data = ''.join(packages)
        return data

    def write_command(self, command, clean_buffer=False):
        """Send a command to the TCP/IP client.
        
        :param str command: FPGA command to be executed.
        :param bool clean_buffer: if True, a clean-up reading of the 
         input buffer is done after writing.
        :return: message returned from the FPGA after writing the 
         command. If *clean_buffer* is False or there was no message, 
         'EMPTY_BUFFER' is returned.
        """
        data = self._COMMANDS[command]
        self.send('{}\n'.format(data))
        message = "EMPTY BUFFER"
        if clean_buffer:
            try:
                message = self.recv(self.buffer_size)
            except socket.timeout:
                pass
        return message

    def read_register(self, regkey):
        """Read the value of a register and return it formatted.

        :param str regkey: register identifier
        :return: the content of the register
        :rtype: int or list
        """
        reg = self._REGISTERS[regkey]
        self.send('r,{}\n'.format(reg))
        try:
            result = self.recv(self.buffer_size)
        except socket.error as (code, msg):
            # Ignore system (user) interrupts and finish the buffer reading.
            if code != errno.EINTR:
                raise
        # Convert the string input into a valid value e.g. list or int
        formatted_result = ast.literal_eval(result)
        return formatted_result

    def write_register(self, regkey, value):
        """Write a value into a register and clean the input buffer.

        :param str regkey: register identifier that will be written.
        :param value: data that will be written to the register. It will
         be converted to a string before sending.
        :return: message given back by the FPGA after writing the 
         register
        """
        reg = self._REGISTERS[regkey]
        self.send('w,{},{}\n'.format(reg, value))
        # Sometimes an ACK message is returned. It has to be checked for
        # cleaning the buffer.
        try:
            message = self.recv(self.buffer_size)
        except socket.timeout:
            message = "EMPTY BUFFER"
        return message
