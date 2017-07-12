#!/usr/bin/env python
"""Auxiliary program to set a new goal for the UGV."""
# Standard libraries
import os
import sys
import time
# Third party libraries
import zmq

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
             "set. Run the environment .sh script at the project root folder.")

def main():
    goal = {
        'x': float(sys.argv[1]),
        'y': float(sys.argv[2])
    }
    socket = zmq.Context.instance().socket(zmq.PUB)
    # Send goals for robot 1
    socket.bind("tcp://*:{}".format(
            int(os.environ.get("UVISPACE_BASE_PORT_GOAL"))+1))
    time.sleep(2)
    socket.send_json(goal)
    return

if __name__ == '__main__':
    main()
