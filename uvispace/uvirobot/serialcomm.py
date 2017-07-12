#!/usr/bin/env python
"""This module contains the class SerMesProtocol().

The aim is to provide a set of methods for performing communication 
operations with an external device, using a pair of XBee modules
(IEEE 802.15.4 protocol). Needless to say, the modules have to be 
previously configured for being able to communicate with each other, and
that task is out of the scope of this module.

The aforementioned class' methods build up messages following a common 
structure and send them through serial port to a slave with the same
implemented protocol.

Moreover, it offers methods specific to the UGV operation, as the *move*
method, that takes a speeds setpoints inputs and sends them correctly 
formatted to the slave.
"""
# Standard libraries
import logging
from serial import Serial
import struct
import sys
import time

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger('messenger')


class SerMesProtocol(Serial):
    """This is a child of PySerial class and implements a comm. protocol.
    
    This class implements a message-based protocol over the serial port
    in Master-slave mode: The master (PC) starts communication with 
    the slave(peripheral) sending a message. The slave process the 
    message and returns an answer.

    The class uses the serial port to implement this protocol.

    :param str port: name identifier of the port path in the PC's OS.
    :param int baudrate: communications speed between the XBee modules. 
    :param int stopbits: Number of bits at the end of each message.
    :param str parity: Message parity. *None* by default
    :param float timeout: Time to wait to achieve the communication.
    """

    # ---------- CLASS CONSTANTS ---------- #

    # message fields
    STX = '\x02'
    ETX = '\x03'
    # slave-to-master answers
    ACK_MSG = '\x01'
    NACK_MSG = '\x02'
    DONE_MSG = '\x03'
    # master-to-slave orders
    READY = '\x04'
    MOVE = '\x05'

    def __init__(self, port,
                 baudrate,
                 stopbits=1,
                 parity='N',
                 timeout=0.5):
        # Initializes the parent class
        Serial.__init__(self, port=port,
                        baudrate=baudrate,
                        stopbits=stopbits,
                        parity=parity,
                        timeout=timeout)
        # IDs of the master and slave.                
        self.MASTER_ID = '\x01'
        self.SLAVE_ID = '\x02'
        if self._isOpen:
            self.flushInput()

    # -------------------MASTER-SLAVE COMMANDS------------------- #
    def ready(self, tries=10):
        """Check if the communication channel is ready.

        The parameter **tries** specifies the number of attempts before 
        exiting and raising an error message.

        :returns: returns a true or false condition which confirms that 
         the message was received.
        :rtype: bool
        """
        ready = False
        # send configuration message.
        count = 0
        while not ready:
            if count == tries:
                logger.error("Unable to connect. Exited after {} tries".format(
                        tries))
                sys.exit()
            self.send_message(self.READY)
            # wait for the response from the device
            fun_code = self.read_message()[1]
            if fun_code == self.ACK_MSG:
                ready = True
            count += 1
        return ready

    def move(self, setpoint):
        """Send a move order to the slave.

        :param setpoint: List with UGV speeds, whose elements range from
         0 to 255. The first element corresponds to right wheels, and 
         the second element to left wheels. Values are rounded if 
         decimal.
        :type setpoint: [int, int]
        :returns: true or false condition which confirms that the 
            message was received.
        :rtype: bool
        """
        # Check that the values are correct. Invalid values may crash 
        # the Arduino program.
        while any(x > 255 or x < 0 for x in setpoint):
            logger.warn('Invalid set points. Please enter 2 values between '
                        '0 and 255 (Decimal values will be rounded)')
            if any(type(x) == float for x in setpoint):
                setpoint = [int(round(x)) for x in setpoint]
        # Values casted into C 'char' variables
        char_sp = '{}{}'.format(struct.pack('>h', setpoint[0])[1],
                                struct.pack('>h', setpoint[1])[1])
        # send configuration messager
        self.send_message(SerMesProtocol.MOVE, char_sp)
        # wait for the response from the device
        result = self.read_message()
        if (result == 0):  # if an error was detected
            return 0
        else:  # no errors
            fun_code = result[1]
            if fun_code:
                return True
            else:
                return False

    # -------------MASTER-SLAVE COMMANDS AUXILIAR FUNCTIONS------------- #
    def send_message(self, fun_code, data='', send_delay=0.01):
        """Send a message to slaves formatted with the defined protocol.

        :param str fun_code: function code of the command that is going 
         to be sent.
        :param str data: DATA field of the message. 
        :param float send_delay: Delay time to wait between sent bytes.
        """
        # Prepares message.
        # The data length bytes are little endian according to the protocol. 
        # Thus, these bytes have to be reversed.
        data_length = struct.pack('>H', len(data))[::-1]
        message = '{stx}{slave}{master}{ln}{func}{sent_data}{etx}'.format(
                stx=self.STX,
                slave=self.SLAVE_ID,
                master=self.MASTER_ID,
                ln=data_length,
                func=fun_code,
                sent_data=data,
                etx=self.ETX)
        # sends message.
        logger.info('sending... {}'.format(
                " ".join(hex(ord(n)) for n in message)))
        self.write(message)

    def read_message(self):
        """Read a message using the serial message protocol. 

        When the message is read, check the auxiliary bytes for 
        assuring the consistence of the message.

        :returns: [Rx_OK, fun_code, data, length]

          * *Rx_OK* is 0 if an error ocurred.
          * *fun_code* is the non decodified hex-data corresponding to 
            the function code given by the slave.
          * *data* is the non decodified hex-data corresponding to the 
            data given by slave.
          * *length* is the size of the main data, in bytes
        :rtype: [bool, str, str, int]
        """
        Rx_OK = False
        fun_code = ""
        length = 0
        data = ""
        _STX = ""
        # Reading of the auxiliary initial bytes
        # The 1st byte of transmission corresponds to 'start transmission'.
        start_time = time.time()
        while _STX != self.STX:
            current_time = time.time()
            # Gives the slave 0.1 seconds to return an answer.
            if current_time - start_time > 0.1:
                logger.info('Error, STX was not found')
                return (Rx_OK, fun_code, length, data)
            _STX = self.read(1)
        # The 2nd and 3rd bytes of transmission correspond to the master 
        # and slave IDs
        id_dest = self.read(1)
        id_org = self.read(1)

        # Reading of the length-of-data bytes
        # With the try-except statements, it is checked that there 
        # is data available in the 2 length bytes.
        try:
            length = struct.unpack('>H', self.read(2))[0]
        except:
            logger.error('Received length bytes are not valid')
            return (Rx_OK, fun_code, length, data)
        logger.info('received data length = {}'.format(length))

        # Reading of the function code and the main data
        fun_code = self.read(1)
        for i in range(length):
            data = '{previous_data} {new_data}'.format(previous_data=data,
                                                       new_data=self.read(1))
        # Reading of the last byte, corresponding to end of transmission check.
        _ETX = self.read(1)

        # Check of message validity
        if (_STX == self.STX) and (_ETX == self.ETX) \
                and (id_dest == self.MASTER_ID):
            logger.info('Succesfull communication')
            Rx_OK = True
        elif _ETX != SerMesProtocol.ETX:
            logger.error('Error, ETX was not found')
        elif id_dest != self.MASTER_ID:
            logger.warn('Message for other device')

        return (Rx_OK, fun_code, length, data)
