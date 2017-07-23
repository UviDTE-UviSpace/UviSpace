#!/usr/bin/env python
"""This module communicates with user and sensors for finding paths.

It contains a class, *RobotController*, that represents a real UGV, and
contains functionality for publishing new speed values, UGVs
attributes such as the *robot_id* or its speed values. It imports
*pathtracker*, for calculating the robot navigation values.
"""
# Standard libraries
import ast
import ConfigParser
import glob
import logging
import os
import sys
# Third party libraries
import numpy as np
import zmq
# Local libraries
import pathtracker
from speedtransform import Speed

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger("navigator")


class RobotController(object):
    """This class contains methods needed to control a robot's behavior.

    :param int robot_id: identifier of the robot.
    :param bool init: indicates if the instance has been initialized or
     not.
    :param dict speed_status: dictionary with iteration values of the
     kalman filter, linear and angular speeds, and UGV setpoints.
    :param goal_points: array that stores the following M goal points
     for the UGV.
    :type goal_points: numpy.array float64 (shape=Mx2).
    :param float beta: angle of the line between the UGV and the next
     goal point. The value is in radians.
    :param float epsilon: difference between beta angle and UGV angle
     (theta). Angle error to correct. The value is in radians.
    :param float accepted_angle: accepted value of angle error to
     consider that there is no error. The value is in grades.
    :param float distance: distance between UGV and the next goal point
     in millimeters.
    :param float accepted_distance: accepted value of distance between
     UGV and the next goal point to consider that there is no error. The
     value is in millimeters.
    """

    def __init__(self, robot_id=1):
        """Class constructor method"""
        self.robot_id = robot_id
        self.init = False
        self.speed_status = {
            'step': 0,
            'linear': 0.0,
            'angular': 0.0,
            'sp_left': 127,
            'sp_right': 127,
        }
        self.goal_points = np.array([None, None]).reshape(1,2)
        self.beta = 0
        self.epsilon = 0
        self.accepted_angle = 10
        self.distance = 0
        self.accepted_distance = 70
        # Load the config file and read the polynomial coeficients
        self.conf = ConfigParser.ConfigParser()
        self.conf_file = glob.glob("./resources/config/robot{}.cfg"
                                   .format(self.robot_id))
        self.conf.read(self.conf_file)
        self._coefs_left_fwd = ast.literal_eval(self.conf.get(
                                              'Coefficients_fwd', 'coefs_left'))
        self._coefs_right_fwd = ast.literal_eval(self.conf.get(
                                             'Coefficients_fwd', 'coefs_right'))
        self._coefs_left_turn = ast.literal_eval(self.conf.get(
                                             'Coefficients_turn', 'coefs_left'))
        self._coefs_right_turn = ast.literal_eval(self.conf.get(
                                            'Coefficients_turn', 'coefs_right'))
        # Send the coeficients to the polynomial solver objects
        self.robot_speed = Speed()
        self.robot_speed.poly_sol_left_fwd.update_coefs(self._coefs_left_fwd)
        self.robot_speed.poly_sol_right_fwd.update_coefs(self._coefs_right_fwd)
        self.robot_speed.poly_sol_left_turn.update_coefs(self._coefs_left_turn)
        self.robot_speed.poly_sol_right_turn.update_coefs(
                                                         self._coefs_right_turn)
        # Publishing socket instantiation.
        self.speed_publisher = zmq.Context.instance().socket(zmq.PUB)
        self.speed_publisher.bind("tcp://*:{}".format(
                int(os.environ.get("UVISPACE_BASE_PORT_SPEED"))+robot_id))

    def set_speed(self, pose):
        """Receive a new pose and calculate a speed value.

        After calculating the new speed value, call the get_setpoint
        function to transform the speed value into setpoints.

        :param pose: contains a 2-D position, with 2 cartesian values
        (x,y) and an angle value (theta).
        :type pose: dict
        """
        if not self.init:
            self.init = True
            linear = 0
            angular = 0
        elif not self.goal_points.all() == None:
            # There is a goal point.
            current_point = (pose['x'], pose['y'])
            next_point = self.goal_points[0, :]
            self.beta = pathtracker.get_segment_angle(next_point, current_point)
            # Change range of angle UGV: (-pi, pi) to (0, 2*pi).
            if pose['theta'] < 0:
                self.theta = pose['theta'] + 2*np.pi
            else:
                self.theta = pose['theta']
            # Correct UGV orientation.
            self.epsilon = pathtracker.get_diff_angle(self.beta, self.theta)
            linear, angular = pathtracker.match_orientation(self.epsilon)
            # Calculate distance to next goal point.
            segment = next_point - current_point
            self.distance = np.sqrt(segment[0]**2 + segment[1]**2)
            # Check distance to next goal point.
            if self.distance < self.accepted_distance:
                self.delete_goal()
            # Straight movement if the angle is correct.
            if np.abs(self.epsilon) < (self.accepted_angle* np.pi / 180):
                linear, angular = pathtracker.get_fwd_spd(self.distance)
        else:
            linear = 0
            angular = 0
            logger.info('Waiting for a goal...')
        self.robot_speed.set_speed([linear, angular], 'linear_angular')
        logger.info('Pose--> X: {:1.4f}, Y: {:1.4f}, theta: {:1.4f} - '
                    'Speeds--> Linear: {:4.2f}, Angular {:4.2f}, Step {}'
                    .format(pose['x'], pose['y'], pose['theta'], linear, 
                            angular, pose['step']))
        sp_left, sp_right = self.get_setpoints(linear, angular)
        self.publish_message(pose['step'], linear, angular, sp_left, sp_right)
        return

    def get_setpoints(self, linear, angular):
        """Receive speed value and transform it into setpoints.

        :param float linear: linear speed value.
        :param float angular: angular speed value.
        :return: setpoints values.
        :rtype: (int, int)
        """
        # Get the right and left speeds in case of direct movement
        if linear > 60:
            sp_left = self.robot_speed.poly_sol_left_fwd.solve(linear, angular)
            sp_right = self.robot_speed.poly_sol_right_fwd.solve(linear,
                                                                 angular)
        else:
            sp_left = self.robot_speed.poly_sol_left_turn.solve(linear, angular)
            sp_right = self.robot_speed.poly_sol_right_turn.solve(linear,
                                                                  angular)
        return (sp_left, sp_right)

    def publish_message(self, step, linear, angular, sp_left, sp_right):
        """Receives speeds and setpoints and publish them.

        :param int step: kalman filter iterator counter.
        :param float linear: linear speed value.
        :param float angular: angular speed value.
        :param int sp_left: setpoint left value.
        :param int sp_right: setpoint right value.
        """
        self.speed_status['step'] = step
        self.speed_status['linear'] = linear
        self.speed_status['angular'] = angular
        self.speed_status['sp_left'] = sp_left
        self.speed_status['sp_right'] = sp_right
        self.speed_publisher.send_json(self.speed_status)
        return

    def new_goal(self, goal):
        """Receives a new goal and stores it in goal points array.

        :param goal: contains a 2-D position, with 2 cartesian values
        (x,y) and an angle value (theta).
        :type goal: dict
        """
        if self.init:
            goal_point = (goal['x'], goal['y'])
            # Adds the new goal to goal points array.
            if self.goal_points.all() == None:
                self.goal_points = np.array([goal_point]).reshape(1,2)
            else:
                self.goal_points = np.vstack([self.goal_points, goal_point])
            logger.info('New goal--> X: {}, Y: {}'
                        .format(goal['x'], goal['y']))
        else:
            logger.info('The system is not yet initialized, '
                        'waiting for a pose to be published.')
        return

    def delete_goal(self):
        """Delete the next goal point of the array

        The next goal point is in the first row of the array. Deleted
        when destination is reached.
        """
        data_array = self.goal_points
        if data_array.shape[0] == 1:
            # If the data matrix only contain one data.
            data_array = np.array([None, None]).reshape(1,2)
        else:
            data_array = data_array[1:, :]
        self.goal_points = data_array
        return

    def on_shutdown(self):
        """Shutdown method. Is called when execution is aborted."""
        logger.info('Shutting down')
        sp_left, sp_right = self.get_setpoints(0, 0)
        self.publish_message(self.speed_status['step']+1, 0, 0, sp_left,
                             sp_right)
        # Cleanup resources
        self.speed_publisher.close()
        return
