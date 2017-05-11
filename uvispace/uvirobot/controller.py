#!/usr/bin/env python
"""
Routine for getting UGV poses and publishing to speed topic

The module instantiates a RobotController object and uses its methods
for publishing new speed set points in the topic '/robot_{}/cmd_vel'.

When calling the module, one argument must be passed, representing the
id of the desired robot. It must be the same as the one passed to the
messenger.py module.
"""
# Standard libraries
import sys
import os
import getopt
import numpy as np
import time

# ROS libraries
import rospy
from geometry_msgs.msg import Pose2D

# Local libraries
from robot import RobotController
import plotter


def new_node(my_robot, robot_id):
    """Subscribe to topics and spins until aborted."""
    rospy.init_node('move_robot_{}'.format(robot_id), anonymous=True)
    # The pose is published by the uvispace package
    rospy.Subscriber('/robot_{}/pose2d'.format(robot_id), Pose2D,
                     my_robot.set_speed, queue_size=1)
    # The new goals are published by the user
    rospy.Subscriber('/robot_{}/goal'.format(robot_id), Pose2D,
                     my_robot.new_goal, queue_size=1)
    rospy.on_shutdown(my_robot.on_shutdown)


def make_a_rectangle(my_robot):
    """Set the robot path to a rectangle of fixed vertices."""
    point_a = Pose2D(x=1.0, y=1.0)
    point_b = Pose2D(x=-1.0, y=1.0)
    point_c = Pose2D(x=-1.0, y=-1.0)
    point_d = Pose2D(x=1.0, y=-1.0)
    point_e = Pose2D(x=1.0, y=0.0)
    my_robot.new_goal(point_a)
    my_robot.new_goal(point_b)
    my_robot.new_goal(point_c)
    my_robot.new_goal(point_d)
    my_robot.new_goal(point_e)


def main():
    # This exception forces to give the robot_id argument within run command.
    rectangle_path = False
    help_msg = ('Usage: controller.py [-r <robot_id>], [--robotid=<robot_id>], '
                '[--rectangle]')
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:", ["robotid=",
                                                         "rectangle"])
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
        else:
            if opt in ("-r", "--robotid"):
                robot_id = int(arg)
            else:
                print help_msg
                sys.exit()
            if opt == "--rectangle":
                rectangle_path = True
    # Calls the main function
    my_robot = RobotController(robot_id)
    new_node(my_robot, robot_id)
    # Until the first pose is not published, the robot instance
    # is not initialized.
    while not my_robot.init:
        pass
    # This function sends 4 rectangle points to the robot path.
    if rectangle_path:
        make_a_rectangle(my_robot)
    rospy.spin()

    # Print the log output to files and plot it
    script_path = os.path.dirname(os.path.realpath(__file__))
    # A file identifier is generated from the current time value
    file_id = int(time.time())
    with open('{}/tmp/path{}.log'.format(script_path, file_id), 'a') as f:
        np.savetxt(f, my_robot.QCTracker.route, fmt='%.2f')
    # Plots the robot ideal path.
    plotter.path_plot(my_robot.QCTracker.path, my_robot.QCTracker.route)


if __name__ == '__main__':
    main()
