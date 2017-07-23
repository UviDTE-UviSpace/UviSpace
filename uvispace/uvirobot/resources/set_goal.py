#!/usr/bin/env python
"""Auxiliary program to set a new goal for the UGV."""
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
logger = logging.getLogger('navigator')

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
    help_msg = ("Usage: set_goal.py [-x <goal_x>], [--goal_x=<goal_x>],"
                "[-y <goal_y>], [--goal_y=<goal_y>]")
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hx:y:", ["goal_x=", "goal_y"])
    except getopt.GetoptError:
        print(help_msg)
    if not opts:
        print help_msg
        sys.exit()
    for opt, arg in opts:
        if opt == '-h':
            print help_msg
            sys.exit()
        elif opt in ("-x", "--goal_x"):
            goal_x = float(arg)
        elif opt in ("-y", "--goal_y"):
            goal_y = float(arg)
    logger.info("Start")
    goal_publisher = zmq.Context.instance().socket(zmq.PUB)
    # Send goals for robot 1
    goal_publisher.bind("tcp://*:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_GOAL"))+1))
    logger.info("Publisher socket bound")
    goal = {
        'x': goal_x,
        'y': goal_y,
    }
    # The loop is exited after the sigint_handler function is called.
    while run_program:
        goal_publisher.send_json(goal)
        logger.info("Sent {}".format(goal))
        time.sleep(2)
    # Cleanup resources
    goal_publisher.close()
    return

if __name__ == '__main__':
    main()
