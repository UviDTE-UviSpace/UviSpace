#!/usr/bin/env python
"""This module communicates with user and sensors for finding paths.

It contains a class, *RobotController*, that represents a real UGV, and
contains ROS functionality for publishing new speed values, UGV's
attributes, such as the *robot_id*, its speed values, or an instance
of the *PathTracker*, for calculating and storing the robot navigation
values.
"""
# ROS libraries
import rospy
from geometry_msgs.msg import Twist
# Local libraries
import path_tracker


class RobotController(object):
    """
    This class contains methods needed to control a robot's behavior.

    :param int robot_id: Identifier of the robot
    """

    def __init__(self, robot_id=1):
        """Class constructor method"""
        self.robot_id = robot_id
        self.init = False
        self.speeds = Twist()
        self.QCTracker = path_tracker.QuadCurveTracker()
        self.terminated = False
        self.pub_vel = rospy.Publisher('/robot_{}/cmd_vel'.format(robot_id),
                                       Twist, queue_size=1)

    def set_speed(self, pose):
        """
        Receives a new pose and calculates the UGV speeds.

        After calculating the new speed value, it is published on the
        rostopic *'/robot_X/cmd_vel'* using the *pub_vel* object.
        Only the values X, Y and theta of the *Pose2D* type are used, as
        the designed Space consists in a 2-D flat space.

        :param pose: contains a 2-D position, with 2 cartesian values
         (x,y) and an angle value (theta).
        :type pose: gemoetry_msgs.Pose2D
        """
        if self.init == False:
            self.QCTracker.append_point((pose.x, pose.y))
            self.init = True
        linear, angular = self.QCTracker.run(pose.x, pose.y, pose.theta)
        rospy.loginfo('\nLocation--> '
                      'X: {pose.x}, Y: {pose.y}, theta: {pose.theta} \n'
                      'Speeds--> Linear: {linear}, Angular {angular}'.format(
                            pose=pose, linear=linear, angular=angular))
        self.speeds.linear.x = linear
        self.speeds.angular.z = angular
        self.pub_vel.publish(self.speeds)

    def new_goal(self, goal):
        """
        Receives a new goal and calculates the path to reach it.

        :param goal: contains a 2-D position, with 2 cartesian
         values (x,y) and an angle value (theta).
        :type goal: geometry_msgs.Pose2D
        """
        if self.init:
            goal_point = (goal.x, goal.y)
            # Adds the new goal to the current path, calculating all the
            # intermediate points and stacking them to the path array
            self.QCTracker.append_point(goal_point)
            rospy.loginfo('New goal--> X: {}, Y: {}'.format(goal.x, goal.y))
        else:
            rospy.loginfo(' The system is not yet initialized. \
            Waiting for a pose to be published ')

    def on_shutdown(self):
        """ Shutdown method. Is called when execution is aborted."""
        self.speeds.linear.x = 0.0
        self.speeds.angular.z = 0.0
        self.pub_vel.publish(self.speeds)
        self.terminated = True
