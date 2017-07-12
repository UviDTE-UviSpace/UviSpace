#!/usr/bin/env python
"""Routine for getting UGV poses and publishing speed set points.

The module instantiates a RobotController object and uses its methods
for publishing new speed set points.

When calling the module, one argument must be passed, representing the
id of the desired robot. It must be the same as the one passed to the
messenger.py module.
"""
# Standard libraries
import getopt
import logging
import os
import signal
import sys
import time
# Third party libraries
import numpy as np
import zmq
# Local libraries
import plotter
from robot import RobotController

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger('controller')


def make_a_rectangle(my_robot):
    """Set the robot path to a rectangle of fixed vertices."""
    logger.info("Creating rectangle path")
    point_a = {'x': 1.0, 'y': 1.0}
    point_b = {'x': -1.0, 'y': 1.0}
    point_c = {'x': -1.0, 'y': -1.0}
    point_d = {'x': 1.0, 'y': -1.0}
    point_e = {'x': 1.0, 'y': 0.0}
    my_robot.new_goal(point_a)
    my_robot.new_goal(point_b)
    my_robot.new_goal(point_c)
    my_robot.new_goal(point_d)
    my_robot.new_goal(point_e)
    return


def init_sockets(robot_id):
    """Initializes the subscriber sockets in charge of listening for data."""
    logger.debug("Initializing subscriber sockets")

    # Open a subscribe socket to listen for position data
    pose_subscriber = zmq.Context.instance().socket(zmq.SUB)
    pose_subscriber.setsockopt_string(zmq.SUBSCRIBE, u"")
    pose_subscriber.setsockopt(zmq.CONFLATE, True)
    pose_subscriber.connect("tcp://localhost:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_POSITION"))+robot_id))

    # Open a subscribe socket to listen for new goals
    goal_subscriber = zmq.Context.instance().socket(zmq.SUB)
    goal_subscriber.setsockopt_string(zmq.SUBSCRIBE, u"")
    goal_subscriber.connect("tcp://localhost:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_GOAL"))+robot_id))
    # Construct the sockets dictionary
    sockets = {
        'pose_subscriber': pose_subscriber,
        'goal_subscriber': goal_subscriber,
    }
    return sockets


def listen_sockets(sockets, my_robot):
    """Listens on subscriber sockets for messages of positions and goals."""
    global run_program
    # Initialize poll set
    poller = zmq.Poller()
    poller.register(sockets['pose_subscriber'], zmq.POLLIN)
    poller.register(sockets['goal_subscriber'], zmq.POLLIN)

    # listen for position information and new goal points
    while run_program:
        # poll the sockets every second
        events = dict(poller.poll(1000))
        if (sockets['pose_subscriber'] in events
                and events[sockets['pose_subscriber']] == zmq.POLLIN):
            position = sockets['pose_subscriber'].recv_json()
            logger.debug("Received new pose: {}".format(position))
            my_robot.set_speed(position)

        if (sockets['goal_subscriber'] in events
                and events[sockets['goal_subscriber']] == zmq.POLLIN):
            goal = sockets['goal_subscriber'].recv_json()
            logger.debug("Received new goal: {}".format(goal))
            my_robot.new_goal(goal)


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

    # This exception forces to give the robot_id argument within run command.
    rectangle_path = False
    help_msg = ('Usage: controller.py [-r <robot_id>], [--robotid=<robot_id>], '
                '[--rectangle]')
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:",
                                   ["robotid=", "rectangle"])
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
        if opt in ("-r", "--robotid"):
            robot_id = int(arg)
        if opt == "--rectangle":
            rectangle_path = True
    # Calls the main function
    my_robot = RobotController(robot_id)

    # Open listening sockets
    sockets = init_sockets(robot_id)

    # Until the first pose is not published, the robot instance is not
    # initialized. Keep trying to receive the initial position with a
    # no blocking recv until the instance is initialized or the run flag
    # has been set to False.
    logger.info("Waiting for first pose")
    while run_program and not my_robot.init:
        try:
            position = sockets['pose_subscriber'].recv_json(zmq.NOBLOCK)
        except zmq.ZMQError:
            pass
        else:
            logger.debug("Received first position: {}".format(position))
            my_robot.set_speed(position)

    # This function sends 4 rectangle points to the robot path.
    if rectangle_path:
        make_a_rectangle(my_robot)

    # Listen sockets
    listen_sockets(sockets, my_robot)
    # Once the run flag has been set to False, shutdown
    my_robot.on_shutdown()
    # Cleanup resources
    for socket in sockets:
        sockets[socket].close()
    # Plot results
    if my_robot.QCTracker.path is not None:
        # Print the log output to files and plot it
        script_path = os.path.dirname(os.path.realpath(__file__))
        # A file identifier is generated from the current time value
        file_id = time.strftime('%Y%m%d_%H%M')
        with open('{}/tmp/path_{}.log'.format(script_path, file_id), 'a') as f:
            np.savetxt(f, my_robot.QCTracker.route, fmt='%.2f')
        # Plots the robot ideal path.
        plotter.path_plot(my_robot.QCTracker.path, my_robot.QCTracker.route)

    return


if __name__ == '__main__':
    main()
