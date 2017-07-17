#!/usr/bin/env python
"""Auxiliary program to move the UGV at constant speed.

This module allows the UGV to move at a constant speed for a given time.
These values ​​are required to the user.
"""
# Standard libraries
import getopt
import logging
import numpy as np
import sys
import time
# Local libraries
from messenger import connect_and_check
from robot import RobotController
from speedtransform import PolySpeedSolver

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger('speedstudy')

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
    # Equation degrees linear velocity 2 and angular velocity 2.
    left_solver = PolySpeedSolver(coefs=(117.1, 0.334, 36.02, 0.00002422,
                                         -0.4208, 22.21))
    right_solver = PolySpeedSolver(coefs=(141, 0.0902, -94.88, 0.0004565,
                                          0.6557, 22.59))
    #TODO Check correct values
    linear = float(raw_input("Enter the linear speed value\n"))
    angular = float(raw_input("Enter the angular speed value\n"))
    operatingtime = float(raw_input("Enter the time to evaluate in seconds \n"))
    init_time = time.time()
    sp_left = int(left_solver.solve(linear, angular))
    sp_right = int(right_solver.solve(linear, angular))
    print "I am sending ({}, {})".format(sp_left, sp_right)
    while (time.time() - init_time) < operatingtime:
        my_serial.move([sp_right, sp_left])
        print "I am sending ({}, {})".format(sp_left, sp_right)
    # When the desired time passes, the speed is zero
    sp_right = 127
    sp_left = 127
    my_serial.move([sp_right, sp_left])
    print "I am sending ({}, {})".format(sp_left, sp_right)

if __name__ == '__main__':
    main()
