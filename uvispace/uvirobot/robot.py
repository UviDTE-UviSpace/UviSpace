#!/usr/bin/env python
"""This module communicates with user and sensors for finding paths.

It contains a class, *RobotController*, that represents a real UGV, and
contains functionality for publishing new speed values, UGVs
attributes, such as the *robot_id*, its speed values, or an instance
of the *PathTracker*, for calculating and storing the robot navigation
values.
"""
# Standard libraries
import ast
import ConfigParser
import glob
import logging
import os
import sys
# Third party libraries
import zmq
# Local libraries
import path_tracker
from speedtransform import Speed

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger("controller")


class RobotController(object):
    """This class contains methods needed to control a robot's behavior.

    :param int robot_id: Identifier of the robot
    """

    def __init__(self, robot_id=1):
        """Class constructor method"""
        self.robot_id = robot_id
        self.init = False
        self.speed_status = {
            # Kalman filter iterator counter.
            'step': 0,
            'linear': 0.0,
            'angular': 0.0,
            'sp_left': 127,
            'sp_right': 127,
        }
        self.QCTracker = path_tracker.QuadCurveTracker()
        # Load the config file and read the polynomial coeficients
        self.conf = ConfigParser.ConfigParser()
        self.conf_file = glob.glob(
                        "./resources/config/robot{}.cfg".format(self.robot_id))
        self.conf.read(self.conf_file)
        self._coefs_left = ast.literal_eval(self.conf.get('Coefficients',
                                                          'coefs_left'))
        self._coefs_right = ast.literal_eval(self.conf.get('Coefficients',
                                                           'coefs_right'))
        # Send the coeficients to the polynomial solver objects
        self.robot_speed = Speed()
        self.robot_speed.poly_solver_left.update_coefs(self._coefs_left)
        self.robot_speed.poly_solver_right.update_coefs(self._coefs_right)
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
            self.QCTracker.append_point((pose['x'], pose['y']))
            self.init = True
        linear, angular = self.QCTracker.run(
                pose['x'], pose['y'], pose['theta'])
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
        """
        # Get the right and left speeds in case of direct movement
        sp_left = self.robot_speed.poly_solver_left.solve(linear, angular)
        sp_right = self.robot_speed.poly_solver_right.solve(linear, angular)
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
        """Receives a new goal and calculates the path to reach it.

        :param goal: contains a 2-D position, with 2 cartesian values
        (x,y) and an angle value (theta).
        :type goal: dict
        """
        if self.init:
            goal_point = (goal['x'], goal['y'])
            # Adds the new goal to the current path, calculating all the
            # intermediate points and stacking them to the path array
            self.QCTracker.append_point(goal_point)
            logger.info('New goal--> X: {}, Y: {}'
                        .format(goal['x'], goal['y']))
        else:
            logger.info('The system is not yet initialized, '
                        'waiting for a pose to be published.')

    def on_shutdown(self):
        """Shutdown method. Is called when execution is aborted."""
        logger.info('Shutting down')
        sp_left, sp_right = self.get_setpoints(0, 0)
        self.publish_message(self.speed_status['step']+1, 0, 0, sp_left,
                             sp_right)
        # Cleanup resources
        self.speed_publisher.close()
        return
