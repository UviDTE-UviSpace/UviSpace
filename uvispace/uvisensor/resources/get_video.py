import socket
import pylab
import cv2
import time
import logging

# Logging setup
import settings
logger = logging.getLogger('sensor')


def main():
    address = ("172.19.5.213", 36000)
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    s.connect(address)

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, 6.0, (640, 480))

    for i in range(10000):
        try:
            logger.info("Requesting frame {}".format(i))
            s.send("capture_frame\n")
            message = recv_data(s, 480 * 640 * 4)
        except socket.timeout:
            break
        except KeyboardInterrupt:
            break
        else:
            shape = (480, 640, 4)
            mat = pylab.fromstring(message, dtype=pylab.uint8).reshape(shape)
            image = mat[:, :, 0:3]
            cv2.imshow('stream', image)
            cv2.waitKey(1)
            out.write(image)

    s.send("quit\n")


def recv_data(sck, size):
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
