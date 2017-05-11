#!/usr/bin/env python
"""
Auxiliary program for controlling the UGV movements through keyboard.

The module makes a reading of the keyboard, and from the movement
chosen by the user, publish new speed in the topic '/robot_{}/cmd_vel'.

For the correct operation of the module, it is necessary that the
keyboard delay in the operating system is less than 250 ms.
"""
# Standard libraries
import termios
import select
import sys
import time
import tty

# ROS libraries
from geometry_msgs.msg import Twist
import rospy


def get_key():
    """Return key pressed."""
    # file descriptor (integer that represents an open file).
    fd = sys.stdin.fileno()
    # get stdin settings
    settings = termios.tcgetattr(fd)
    # Put terminal in raw mode
    tty.setraw(fd)
    # Wait until stdin is ready to be read. There is a timeout of 0.25s.
    # This time depends on the keyboard delay in the operating system.
    rlist, _, _ = select.select([sys.stdin], [], [], 0.25)
    # Read the stdin input.
    if rlist:
        key = sys.stdin.read(1)
    else:
        key = ''
    # Set the attributes stored in settings after transmitting queued output.
    termios.tcsetattr(fd, termios.TCSADRAIN, settings)
    return key


def main():
    # Init node and publisher handler.
    rospy.init_node('teleop_keyboard')
    pub_vel = rospy.Publisher('/robot_1/cmd_vel', Twist, queue_size=1)
    speeds = Twist()
    init_time = time.time()
    # instructions for moving the UGV.
    print ('\n\r'
           'Teleoperation program initialized. Available commands:\n\r'
           '* S : Move backwards.\n\r'
           '* W : Move forward.\n\r'
           '* A : Move left. \n\r'
           '* D : Move right. \n\r'
           '* Q : Stop and quit.\n\r'
           '* Nothing or another key : Stop moving.\n\r'
           '\n\r'
           'Currently stop moving \n\r'
           )
    # this initialization is necessary to update the previous state variable
    # key (prev_key) the first time.
    key = ''
    # print ('\n\r'.join(message))
    while True:
        # variables key pressed now and key previously pressed
        prev_key = key
        key = get_key()
        # Move forward.
        if key in ('w', 'W'):
            message = 'moving forward'
            speeds.linear.x = 190
            speeds.angular.z = 0
            pub_vel.publish(speeds)
        # Move backwards.
        elif key in ('s', 'S'):
            message = 'moving backwards'
            speeds.linear.x = -300
            speeds.angular.z = 0
            pub_vel.publish(speeds)
        # Move left.
        elif key in ('a', 'A'):
            message = 'moving left'
            speeds.angular.x = 0
            speeds.angular.z = 10
            pub_vel.publish(speeds)
        # Move right.
        elif key in ('d', 'D'):
            message = 'moving right'
            speeds.angular.x = 0
            speeds.angular.z = -10
            pub_vel.publish(speeds)
        # Stop moving and exit.
        elif key in ('q', 'Q'):
            print ('Stop and exiting program. Have a good day! =)')
            speeds.linear.x = 0
            speeds.angular.z = 0
            pub_vel.publish(speeds)
            break
        # Stop moving.
        else:
            message = 'stop moving'
            speeds.linear.x = 0
            speeds.angular.z = 0
            pub_vel.publish(speeds)
        # if key pressed now and key pressed previously are different, update
        # message
        if prev_key != key:
            print 'Currently %s. \n\r' % message


if __name__ == '__main__':
    main()
