#!/usr/bin/env python
"""
Auxiliary program to move the car at speeds between 0 and 255 (binary).
"""
# Standard libraries
import sys
import getopt
import time
# Local libraries
from messenger import connect_and_check
from robot import RobotController

def main():
    # Main routine
    help_msg = 'Usage: speedstudy.py [-r <robot_id>], [--robotid=<robot_id>]'
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

    # Create an instance of SerMesProtocol and check connection to port.
    my_serial = connect_and_check(robot_id)
    my_robot = RobotController(robot_id)
    # Request of speeds and time to the user
    sRight = input("Enter the speed value for the right wheels, between 0 and "
                    "255 \n")
    sLeft = input("Enter the speed value for the left wheels, between 0 and "
                    "255 \n")
    operatingtime = input("Enter the time to evaluate in seconds \n")
    init_time = time.time()
    print "I am sending (%d, %d)" % (sRight, sLeft)
    while (time.time() - init_time) < operatingtime:
        my_serial.move([sRight, sLeft])
    # When the desired time passes, the speed is zero
    sRight = 127
    sLeft = 127
    my_serial.move([sRight, sLeft])
    print "I am sending (%d, %d)" % (sRight, sLeft)

if __name__ == '__main__':
    main()
