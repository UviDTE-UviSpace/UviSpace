#!/usr/bin/env python
"""
Auxiliar module for streaming images from a Localization Node.

The localization node can be accessed through TCP/IP.
"""
import cv2
import logging
import numpy as np
import socket
import time

try:
    # Logging setup.
    import settings
except ImportError:
    # Exit program if the settings module can't be found.
    sys.exit("Can't find settings module. Maybe environment variables are not"
"set. Run the environment .sh script at the project root folder.")
logger = logging.getLogger('sensor')


def main():
    address = ("172.19.5.213", 36000)
    client = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    client.connect(address)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    videowriter = cv2.VideoWriter('output.avi', fourcc, 6.0, (640, 480))

    for frame in range(10000):
        try:
            logger.info("Requesting frame {}".format(frame))
            client.send("capture_frame\n")
            message = recv_data(client, 480*640*4)
        except socket.timeout:
            break
        except KeyboardInterrupt:
            break
        else:
            shape = (480, 640, 4)
            raw_array = np.fromstring(message, dtype=np.uint8).reshape(shape)
            image = raw_array[:, :, 0:3]
            cv2.imshow('stream', image)
            cv2.waitKey(1)
            videowriter.write(image)

    client.send("quit\n")


def recv_data(sck, size):
    """Read the specified number of packages from the input socket."""
    recv_bytes = 0
    packages = []
    count = 0
    # Do not stop reading new packages until target 'size' is reached
    while recv_bytes < size:
        try:
            received_package = sck.recv(size)
        except socket.timeout:
            break
        recv_bytes += len(received_package)
        packages.append(received_package)
        count += 1
    # Concatenate all the packages in a unique variable
    logger.debug("recv_data: {}".format(count))
    data = ''.join(packages)
    return data

if __name__ == '__main__':
    main()
