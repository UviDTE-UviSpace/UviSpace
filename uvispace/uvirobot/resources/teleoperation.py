#!/usr/bin/env python
"""
Auxiliary program for controlling the UGV movements through keyboard.

The module makes a reading of the keyboard, and sends the movement
chosen by the user.

For the correct operation of the module, it is necessary that the
keyboard delay in the operating system is less than 250 ms.
"""
# Standard libraries
import ast
import ConfigParser
import getopt
import glob
import logging
import os
import select
import signal
import sys
import termios
import tty
# Third party libraries
import zmq
# Local libraries
try:
    from uvirobot.speedtransform import Speed
except ImportError:
    # Exit program if the uvirobot package can't be found.
    sys.exit("Can't find uvirobot module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")

# Logging setup.
import settings


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
    # SIGINT handling:
    # -Create a global flag to check if the execution should keep running.
    # -Whenever SIGINT is received, set the global flag to False.
    global run_program
    run_program = True

    def sigint_handler(signal, frame):
        global run_program
        run_program = False
        return
    signal.signal(signal.SIGINT, sigint_handler)
    # This exception forces to give the robot_id argument within run command.
    help_msg = ('Usage: teleoperation.py [-r <robot_id>],'
                '[--robotid=<robot_id>]')
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hr:", ["robotid="])
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
    # Init publisher
    speed_publisher = zmq.Context.instance().socket(zmq.PUB)
    speed_publisher.bind("tcp://*:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_SPEED"))+1))
    speed_message = {
        'step': 0,
        'linear': 0.0,
        'angular': 0.0,
        'sp_left': 127,
        'sp_right': 127,
    }
    speed = Speed()
    # Read configuration file coefficients.
    conf = ConfigParser.ConfigParser()
    conf_file = glob.glob("./config/robot{}.cfg".format(robot_id))
    conf.read(conf_file)
    coefs_left = ast.literal_eval(conf.get('Coefficients', 'coefs_left'))
    coefs_right = ast.literal_eval(conf.get('Coefficients', 'coefs_right'))
    # Send the coeficients to the polynomial solver objects.
    speed.poly_solver_left.update_coefs(coefs_left)
    speed.poly_solver_right.update_coefs(coefs_right)
    # import pdb; pdb.set_trace()
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
    while True:
        # variables key pressed now and key previously pressed
        prev_key = key
        key = get_key()
        # Move forward.
        if key in ('w', 'W'):
            screen_message = 'moving forward'
            speed_message['sp_left'] = speed.poly_solver_left.solve(400, 0)
            speed_message['sp_right'] = speed.poly_solver_right.solve(400, 0)
            speed_publisher.send_json(speed_message)
        # Move backwards.
        elif key in ('s', 'S'):
            screen_message = 'moving backwards'
            speed_message['sp_left'] = speed.poly_solver_left.solve(-200, 0)
            speed_message['sp_right'] = speed.poly_solver_right.solve(-200, 0)
            speed_publisher.send_json(speed_message)
        # Move left.
        elif key in ('a', 'A'):
            screen_message = 'moving left'
            speed_message['sp_left'] = speed.poly_solver_left.solve(200, 1)
            speed_message['sp_right'] = speed.poly_solver_right.solve(200, 1)
            speed_publisher.send_json(speed_message)
        # Move right.
        elif key in ('d', 'D'):
            screen_message = 'moving right'
            speed_message['sp_left'] = speed.poly_solver_left.solve(200, -1)
            speed_message['sp_right'] = speed.poly_solver_right.solve(200, -1)
            speed_publisher.send_json(speed_message)
        # Stop moving and exit.
        elif key in ('q', 'Q'):
            print ('Stop and exiting program. Have a good day! =)')
            speed_message['sp_left'] = speed.poly_solver_left.solve(0, 0)
            speed_message['sp_right'] = speed.poly_solver_right.solve(0, 0)
            speed_publisher.send_json(speed_message)
            break
        # Stop moving.
        else:
            screen_message = 'stop moving'
            speed_message['sp_left'] = speed.poly_solver_left.solve(0, 0)
            speed_message['sp_right'] = speed.poly_solver_right.solve(0, 0)
            speed_publisher.send_json(speed_message)
        # if key pressed now and key pressed previously are different,
        # update message
        if prev_key != key:
            print('Currently %s. \n\r' % screen_message)

    # Cleanup resources before end
    speed_publisher.close()
    return


if __name__ == '__main__':
    main()
