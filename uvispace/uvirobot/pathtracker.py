#!/usr/bin/env python
"""Module with functions to allow the UGV to reach the goal points.

It contains functions to selecction correct speed depending on the
position of the UGV and its goal.
"""
# Third party libraries
import numpy as np


def get_turn_spd(differential_angle):
    """Calculate the speeds to get the correct orientation of the UGV.

    Choose the linear and angular speeds to provide a turn that equals
    the angle of the UGV and the segment between the position of the UGV
    and the goal of this.

    :param float differential_angle: contains a angle in radians.
    :return: linear and angular speed values.
    :rtype: (float, float)
    """
    if differential_angle > 0:
        angular = 0.7
    else:
        angular = -0.7
    linear = 20
    return (linear, angular)


def get_fwd_spd(distance):
    """Calculate the speeds depending on the distance to the goal.

    :param float distance: contains the distance to the goal.
    :return: linear and angular speed values.
    :rtype: (float, float)
    """
    if distance > 500:
        linear = 400
    elif distance > 300:
        linear = 200
    elif distance > 70:
        linear = 140
    else:
        linear = 0
    angular = 0
    return (linear, angular)
