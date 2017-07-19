#!/usr/bin/env python
"""

"""
# Third party libraries
import numpy as np

def target_angle(current_point, goal_points):
    if not (goal_points == None):
        segment = goal_points[0, :] - current_point
        beta = np.arctan(segment[1]/segment[0])
        print segment

        if segment[0] == 0:
            if segment [1] > 0:
                beta = np.pi / 2
            else:
                beta = -np.pi / 2
        if segment[0] < 0:
            beta += np.pi
        if beta < 0:
            beta += (2 * np.pi)
    else:
        beta = 0

    return beta

def target_dist(final_point, initial_point):

    segment = final_point - initial_point
    distance = np.sqrt(segment[0]**2 + segment[1]**2)

    return distance

def match_orientation(beta, theta):

    if beta > theta:
        linear = 20
        angular = 0.6
    if beta < theta:
        linear = 20
        angular = -0.6

    return (linear, angular)

def lin_ang_values(distance):
    if distance > 200:
        linear = 200
        angular = 0
    elif distance > 70:
        linear = 140
        angular = 0
    else:
        linear = 0
        angular = 0

    return (linear, angular)

def delete_point(goal_points):
    work_goal_points = goal_points
    if work_goal_points == None:
        pass
    if work_goal_points.shape[0] == 1:
        work_goal_points = None
    else:
        work_goal_points = work_goal_points[1:, :]

    return work_goal_points



def main():
    # Test angle:
    # Inicialitation points
    read_point = {'x': 0, 'y': 0, 'theta': 0.0}
    goal_point0 = np.array([1, 1])
    goal_point1 = np.array([1, 0])
    goal_point2= np.array([0, 1])
    goal_point3 = np.array([-1, 1])
    goal_point4 = np.array([-1, -1])
    goal_point5 = np.array([1, -1])
    goal_point6 = np.array([-1, 0])
    goal_point7 = np.array([0, -1])

    current_point = (read_point['x'], read_point['y'])

    goal_point_array = goal_point0
    goal_point_array = np.vstack([goal_point_array, goal_point1])
    goal_point_array = np.vstack([goal_point_array, goal_point2])
    goal_point_array = np.vstack([goal_point_array, goal_point3])
    goal_point_array = np.vstack([goal_point_array, goal_point4])
    goal_point_array = np.vstack([goal_point_array, goal_point5])
    goal_point_array = np.vstack([goal_point_array, goal_point6])
    goal_point_array = np.vstack([goal_point_array, goal_point7])

    beta = target_angle(current_point, goal_point_array)
    print beta
    print (beta*180/np.pi)



if __name__ == '__main__':
    main()
