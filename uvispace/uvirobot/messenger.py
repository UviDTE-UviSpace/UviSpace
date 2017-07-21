#!/usr/bin/env python 
"""This module 'listens' to speed SPs and sends them through serial port.

**Usage: messenger.py [-r <robot_id>], [--robotid=<robot_id>]**

To communicate with the external slaves, the data has to be packed using 
a prearranged protocol, in order to be unpacked and understood 
correctly by the slave.

If it is run as main script, it creates an instance of the class 
*SerMesProtocol* for managing the serial port. T

When a new speed SP is received, it is sent to the target UGV using the 
instanced object.

**Speed formatting:**


The *move_robot* function has the default speed limit set to [89-165]. 
These limits are needed when the robot is connected to a DC source with 
a small intensity limit.
If the program is run when the UGV is powered through a USB-B cable, it 
will move slowly, as the limit is too small to be able to move properly.

When the execution ends, the *plotter* module is called and the time 
delays values are plotted on a graph.
"""
# Standard libraries
import getopt
import glob
import logging
import os
import struct
import sys
import time
# Third party libraries
import zmq
# Local libraries
import plotter
from serialcomm import SerMesProtocol
from speedtransform import Speed

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger('messenger')


def connect_and_check(robot_id, port=None, baudrate=57600):
    """Return an instance of SerMesProtocol and check it is ready.
    
    If no port is specified, take the first one available.
    """
    logger.debug("Checking connection")
    # This exception prevents a crash when no device is connected to CPU.   
    if not port:
        try:
            port = glob.glob('/dev/ttyUSB*')[0]
        except IndexError:
            logger.info("It was not detected any serial port connected to PC")
            sys.exit()
    # Convert the Python id number to the C format 'unsigned byte'
    serialcomm = SerMesProtocol(port=port, baudrate=baudrate)
    serialcomm.SLAVE_ID = struct.pack('>B', robot_id)
    # Check connection to board. If broken, program exits
    if serialcomm.ready():
        logger.info("The board is ready")
    else:
        logger.info("The board is not ready")
        sys.exit()
    return serialcomm


def listen_speed_set_points(my_serial, robot_id, robot_speed, speed_calc_times,
                            wait_times, xbee_times, soc_read_interval=5):
    """Listens for new speed set point messages on a subscriber socket."""
    logger.debug("Initializing subscriber socket")
    # Open a subscribe socket to listen speed directives
    listener = zmq.Context.instance().socket(zmq.SUB)
    # Set subscribe option to empty so it receives all messages
    listener.setsockopt_string(zmq.SUBSCRIBE, u"")
    # Set the conflate option to true so it only keeps the last message received
    listener.setsockopt(zmq.CONFLATE, True)
    listener.connect("tcp://localhost:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_SPEED"))+robot_id))

    logger.debug("Listening for speed set points")
    # Initialize the time for checking if the soc has to be read.
    soc_time = time.time()
    # listen for speed directives until interrupted
    try:
        while True:
            data = listener.recv_json()
            logger.debug("Received new speed set point: {}".format(data))
            move_robot(data, my_serial, wait_times, speed_calc_times,
                       xbee_times, robot_speed)
            # Read the battery state-of-charge after regular seconds intervals.
            if (time.time()-soc_time) > soc_read_interval:
                read_battery_soc(my_serial)
                soc_time = time.time()
    except KeyboardInterrupt:
        pass
    return


def move_robot(data, my_serial, wait_times, speed_calc_times, xbee_times,
               robot_speed, min_speed=70, max_speed=190):
    """Convert speed msg into 2WD value and send it through port."""
    global t0
    global t1
    global t2
    t1 = time.time()
    wait_times.append(t1 - t0)
    linear = data['linear']
    angular = data['angular']
    t2 = time.time()
    speed_calc_times.append(t2 - t1)
    robot_speed.set_speed([linear, angular], 'linear_angular')
    # Get the right and left speeds in case of direct movement
    # The coefficients were found empirically
    if robot_speed.get_speed()[0] > 0:
        robot_speed.get_2WD_speeds(wheels_modifiers=[0.53, 1])
    # Get the right and left speeds in case of reverse movement
    else:
        robot_speed.get_2WD_speeds(wheels_modifiers=[1, 1])
    sp_right, sp_left = robot_speed.nonlinear_transform(min_A=min_speed,
                                                        max_B=max_speed)
    logger.info('I am sending R: {} L: {}'.format(sp_right, sp_left))
    my_serial.move([sp_right, sp_left])
    t0 = time.time()
    xbee_times.append(t0 - t2)
    logger.debug('Transmission ended successfully')


def read_battery_soc(my_serial):
    """Send a petition to the slave for returning the battery SOC"""
    raw_soc = my_serial.get_soc()
    if raw_soc is None:
        soc = 0
        logger.warn("Unable to get the battery state of charge")
    elif raw_soc == -1:
        soc = 0
        logger.warn("Fuel gauge PCB not detected")
    else:
        # The soc variable are 4 bytes, but the data is stored on the last 2.
        soc = struct.unpack('>H', raw_soc[1]+raw_soc[3])[0]
        logger.info("The current battery soc is {}%".format(soc))
    return soc


def stop_vehicle(my_serial, wait_times, speed_calc_times, xbee_times,
                 robot_speed):
    """Send a null speed to the UGV."""
    stop_speed = {
        'linear': 0.0,
        'angular': 0.0
    }
    move_robot(stop_speed, my_serial, wait_times, speed_calc_times, xbee_times,
               robot_speed)


def print_times(wait_times, speed_calc_times, xbee_times):
    """Calculate the average time of each part of the process."""
    wait_mean_time = sum(wait_times) / len(wait_times)
    speed_calc_mean_time = sum(speed_calc_times) / len(speed_calc_times)
    xbee_mean_time = sum(xbee_times) / len(xbee_times)
    logger.info('Wait mean time: {wait} - '
                'Speed calculation mean time: {speed} - '
                'XBee message sending mean time: {xbee}'
                .format(wait=wait_mean_time, speed=speed_calc_mean_time,
                        xbee=xbee_mean_time))


def main():
    logger.info("BEGINNING EXECUTION")
    global t0
    # Main routine
    help_msg = 'Usage: messenger.py [-r <robot_id>], [--robotid=<robot_id>]'
    # This try/except clause forces to give the robot_id argument.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:", ["robotid="])
    except getopt.GetoptError:
        print help_msg
        sys.exit()
    if not opts:
        print help_msg
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print help_msg
            sys.exit()
        elif opt in ("-r", "--robotid"):
            robot_id = int(arg)
    wait_times = []
    speed_calc_times = []
    xbee_times = []
    # Create an instance of SerMesProtocol and check connection to port.
    my_serial = connect_and_check(robot_id)
    robot_speed = Speed()
    t0 = time.time()

    listen_speed_set_points(my_serial, robot_id, robot_speed, speed_calc_times,
                            wait_times, xbee_times)

    stop_vehicle(my_serial, wait_times, speed_calc_times,
                 xbee_times, robot_speed)
    print_times(wait_times, speed_calc_times, xbee_times)

    # Print the log output to files and plot it
    script_path = os.path.dirname(os.path.realpath(__file__))
    # A file identifier is generated from the current time value
    file_id = int(time.time())
    with open('{}/tmp/comm{}.log'.format(script_path, file_id), 'a') as f:
        for item in xbee_times:
            print>> f, '{0:.5f}'.format(item)
    with open('{}/tmp/waittimes{}.log'.format(script_path, file_id), 'a') as f:
        for item in wait_times:
            print>> f, '{0:.5f}'.format(item)
    # Plots the robot ideal path.
    plotter.times_plot(xbee_times, wait_times)


if __name__ == '__main__':
    main()
