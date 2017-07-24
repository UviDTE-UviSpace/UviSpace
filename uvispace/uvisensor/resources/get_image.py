#!/usr/bin/env python
"""
Auxiliar module for obtaining an image from a Localization Node.

The localization node can be accessed through TCP/IP.
"""
import numpy as np
from scipy import misc
import socket


def main():
    client = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    address = ("172.19.5.213", 36000)
    client.connect(address)
    client.send("capture_frame\n")
    try:
        message = recv_data(client, 480*640*4)
    except socket.timeout:
        print("timeout")
    else:
        raw_array = np.fromstring(message, dtype=np.uint8)
        raw_array = raw_array.reshape((480, 640, 4))
        image_array = raw_array[:, :, 0:3]
        misc.imsave("image.png", image_array)

    client.send("quit\n")


def recv_data(sck, size):
    """Read the specified number of packages from the input socket."""
    recv_bytes = 0
    packages = []
    # Do not stop reading new packages until target 'size' is reached.
    while recv_bytes < size:
        try:
            received_package = sck.recv(size)
        except socket.timeout:
            break
        recv_bytes += len(received_package)
        packages.append(received_package)
    # Concatenate all the packages in a unique variable
    data = ''.join(packages)
    return data

if __name__ == '__main__':
    main()
