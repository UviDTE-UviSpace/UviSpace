#!/usr/bin/env python
"""This module provides utilities for easily drawing plots.

It has 3 functions: 

* *format_plotting*: sets the configuration parameters of the plots, in 
  order to use a common format for all the plots.
* *path_plot*: draws 2 plots in the same graph, representing the ideal 
  path of an UGV and the real route it follows. The X and Y axes 
  represent the 2-D coordinates of the working real space.
* *times_plot*: Draws the time delays during execution. It is intended 
  to draw 2 plots, one representing the communication delays with the 
  slave, and the other representing the waiting times for other modules 
  of the project to give required updates of the speed values.
"""
# Standard libraries
import os
# Third party libraries
import matplotlib.pyplot as plt
import numpy as np


def format_plotting():
    plt.rcParams['figure.figsize'] = (10, 8)
    plt.rcParams['font.size'] = 22
    #    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['axes.labelsize'] = plt.rcParams['font.size']
    plt.rcParams['axes.titlesize'] = 1.2 * plt.rcParams['font.size']
    plt.rcParams['legend.fontsize'] = 0.9 * plt.rcParams['font.size']
    plt.rcParams['xtick.labelsize'] = 0.6 * plt.rcParams['font.size']
    plt.rcParams['ytick.labelsize'] = 0.6 * plt.rcParams['font.size']
    plt.rcParams['savefig.dpi'] = 1000
    plt.rcParams['savefig.format'] = 'eps'
    plt.rcParams['xtick.major.size'] = 3
    plt.rcParams['xtick.minor.size'] = 3
    plt.rcParams['xtick.major.width'] = 1
    plt.rcParams['xtick.minor.width'] = 1
    plt.rcParams['ytick.major.size'] = 3
    plt.rcParams['ytick.minor.size'] = 3
    plt.rcParams['ytick.major.width'] = 1
    plt.rcParams['ytick.minor.width'] = 1
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.loc'] = 'upper right'
    plt.rcParams['axes.linewidth'] = 1
    plt.rcParams['lines.linewidth'] = 1
    plt.rcParams['lines.markersize'] = 3

    plt.gca().spines['right'].set_color('none')
    plt.gca().spines['top'].set_color('none')
    plt.gca().xaxis.set_ticks_position('bottom')
    plt.gca().yaxis.set_ticks_position('left')


def path_plot(input_path, real_route):
    """Draw on a figure the desired and real paths."""
    x1, y1 = input_path[:,0], input_path[:,1]
    # If there is only one point in the array, an IndexError will be raised.
    try:
        x2, y2 = real_route[:,0], real_route[:,1]
    except IndexError:
        x2, y2 = real_route[0], real_route[1]
    # Draws the figure
    format_plotting()
    ax = plt.subplot(111)
    # Plotting of the 2 lines, with 'point' markers and blue and red colours
    line1, = ax.plot(x1, y1, 'b.-')
    line2, = ax.plot(x2, y2, 'r.-')
    ax.grid()
    ax.axis('equal')
    ax.set_xlim([-2, 2])
    ax.set_ylim([-2, 2])
    ax.set_xlabel('X Axis')
    ax.set_ylabel('Y Axis')
    script_path = os.path.dirname(os.path.realpath(__file__))
    plt.savefig('{}/tmp/path_plot.eps'.format(script_path), bbox_inches='tight')
    plt.show()


def times_plot(commtimes, waittimes):
    """Draw the history of communication times with the XBee modules.
    
    The input are 2 lists with the process times history.
    The plot data is a 2xN array, where N is the number of requests sent 
    to the XBee module through serial port. 
    The first element of each pair is the sending number and the second
    element is the time it took to receive back the acknowledge message.
    """
    comm_numbers = np.arange(len(commtimes))
    commdata = np.array([comm_numbers, commtimes]).transpose()
    x1, y1 = commdata[:,0], commdata[:,1]
    # The first value of waittimes is ignored as it is the time for setting up.
    wait_numbers = np.arange(len(waittimes[1:]))
    waitdata = np.array([wait_numbers, waittimes[1:]]).transpose()
    # If there is only one point in the array, an IndexError will be raised.
    try:
        x2, y2 = waitdata[:,0], waitdata[:,1]
    except IndexError:
        x2, y2 = waitdata[0], waitdata[1]
    format_plotting()
    #    fig = plt.figure()
    ax = plt.subplot(111)
    line1, = ax.plot(x1, y1, 'bo-', label='Communication times')
    line2, = ax.plot(x2, y2, 'ro-', label='Waiting times')
    ax.grid()
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.set_xlabel('Communication number')
    ax.set_ylabel('Time (s)')
    legend = plt.legend(shadow=True)
    script_path = os.path.dirname(os.path.realpath(__file__))

    plt.savefig('{}/tmp/times_plot.eps'.format(script_path),
                bbox_inches='tight')
    plt.show()


def main():
    test_path = np.array(
            [[0.0, 0.0],
             [0.1, 0.1],
             [0.1, 0.2],
             [0.1, 0.3],
             [0.2, 0.5],
             [0.4, 0.6]])
    test_route = np.array(
            [[0.0, 0.0],
             [0.0, -0.1],
             [0.1, 0.0],
             [0.4, 0.5],
             [0.5, 0.6],
             [0.8, 0.7],
             [1.0, 0.0],
             [0.7, -0.6],
             [2.0, -1.6]])
    path_plot(test_path, test_route)


# ellipse with center in (0,0), width


if __name__ == '__main__':
    main()
