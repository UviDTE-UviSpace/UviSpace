import socket
import pylab
from scipy import misc


def main():
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    address = ("172.19.5.213", 36000)
    s.connect(address)
    s.send("capture_frame\n")
    try:
        message = recv_data(s, 480 * 640 * 4)
    except socket.timeout:
        print("timeout")
    else:
        mat = pylab.fromstring(message, dtype=pylab.uint8)
        mat = mat.reshape((480, 640, 4))
        arr = mat[:, :, 0:3]
        misc.imsave("image.png", arr)


def recv_data(sck, size):
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
