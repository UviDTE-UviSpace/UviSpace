#!/usr/bin/env python
"""This module simulates the uvisensor package for testing uvirobot.

A robot is simulated to be placed at the pose introduced by the user.
The pose is published every 25 milliseconds.
"""
# Standard libraries
import getopt
import logging
import os
import signal
import sys
import time
# Third party libraries
import zmq

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger('sensor')


def main():
    logger.info("BEGINNING EXECUTION")

    # SIGINT handling:
    # -Create a global flag to check if the execution should keep running.
    # -Whenever SIGINT is received, set the global flag to False.
    global run_program
    run_program = True

    def sigint_handler(signal, frame):
        global run_program
        logger.info("Shutting down")
        run_program = False
        return
    signal.signal(signal.SIGINT, sigint_handler)

    # Main routine
    help_msg = ("Usage: sim_sensors.py [-x <pose_x>], [--pose_x=<pose_x>],"
                "[-y <pose_y>], [--pose_y=<pose_y>], [-t <pose_theta>],"
                "[--pose_theta=<pose_theta>]")
    # This try/except clause forces to give the robot_id argument.
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hx:y:t:", ["pose_x=",
                                   "pose_y", "pose_theta="])
    except getopt.GetoptError:
        print(help_msg)
    if not opts:
        print help_msg
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print help_msg
            sys.exit()
        elif opt in ("-x", "--pose_x"):
            pose_x = float(arg)
        elif opt in ("-y", "--pose_y"):
            pose_y = float(arg)
        elif opt in ("-t", "--pose_theta"):
            pose_theta = float(arg)
    logger.info("Start")
    pose_publisher = zmq.Context.instance().socket(zmq.PUB)
    # Send positions for robot 1
    pose_publisher.bind("tcp://*:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_POSITION"))+1))
    step = 0
    logger.info("Publisher socket bound")
    position = {
        'x': pose_x,
        'y': pose_y,
        'theta': pose_theta,
        'step': step,
    }
    # The loop is exited after the sigint_handler function is called.
    while run_program:
        step += 1
        position['step'] = step
        pose_publisher.send_json(position)
        logger.info("Sent {}".format(position))
        time.sleep(0.025)
    # Cleanup resources
    pose_publisher.close()

    return


if __name__ == '__main__':
    main()
