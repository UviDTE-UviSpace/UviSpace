#!/usr/bin/env python
"""Module with functions to allow the UGV to reach the goal points.

It contains functions to perform geometric calculations and speed
selections depending on the position of the UGV and its goal.
"""
# Third party libraries
import numpy as np


def get_segment_angle(final_point, initial_point):
    """Calculate the angle of a segment in a plane.

    The calculated angle is in radians.

    :param final_point: contains a 2-D segment final point, with 2
     cartesian values (x,y).
    :type final_point: (float, float)
    :param initial_point: contains a 2-D segment initial point, with 2
     cartesian values (x,y).
    :type initial_point: (float, float)
    :return: segment angle in a plane. The value is in radians.
    :rtype: float.
    """
    # Calculate the segment between two points.
    segment = final_point - initial_point
    angle = np.arctan(segment[1]/segment[0])
    # Particularities of the calculation angle according to quadrants.
    # Eliminate division by zero when angle is 90 or -90 degrees.
    if segment[0] == 0:
        if segment [1] > 0:
            angle = np.pi / 2
        else:
            angle = -np.pi / 2
    else:
        angle = np.arctan(segment[1]/segment[0])
    # Range of angle (0, 2*pi).
    if segment[0] < 0:
        angle += np.pi
    if angle < 0:
        angle += (2 * np.pi)
    return angle

def get_diff_angle(angle1, angle2):
    """Calculate the difference between two angles.

    NOTE: Calculate the minimun difference of the angle2 with regard to
    angle1 (range of angles (0, 2*pi). For example, if angle1 is 30
    degrees, and angle2 is 330 degrees, there is two possible results:
    -300 degrees, or 60 degrees. This function returns the minimum
    result. The sign indicates if angle 2 is clockwise (positive sign)
    or anticlockwise (negative sign) with respect to angle 1.

    :param float angle1: contains an angle in radians.
    :param float angle2: contains an angle in radians.
    :return: diff_angle: differential angle between two angles.
    :rtype: float.
    """
    if (angle1 > angle2) and ((angle1-angle2) > np.pi):
        differential_angle = angle1 - angle2 - 2*np.pi
    elif (angle1 < angle2) and ((angle2-angle1) > np.pi):
        differential_angle = angle1 - angle2 + 2*np.pi
    else:
        differential_angle = angle1 - angle2
    return differential_angle

def match_orientation(differential_angle):
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
