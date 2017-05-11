#!/usr/bin/env python
"""
Multithreading routine for controlling external FPGAs with cameras.

The module creates several parallel threads, in order to optimize the
execution time, as it contains several instructions which require
waiting for external resources before continuing execution e.g. waiting
for the TCP/IP client to deliver FPGA registers information. Namely, 6
different threads are managed and indexed in a list called *threads*:

* 4 threads that run the 4 FGPAs initialization routines. Afterwards,
  endless loops continually request the UGVs' positions to each FPGA.
* Another thread that interacts with the user through keyboard. It reads
  input commands and performs corresponding actions.
* A final thread is in charge of merging the information obtained at
  each FPGA thread and obtain global UGVs' positions.

NOTE: The proper way to end the program is to press 'Q', as the terminal
prompt indicates during execution. If the Keyboard Interrupt is used
instead, it will probably corrupt the TCP/IP socket and the FPGAs will
have to be reset.
"""
# Standard libraries
import glob
import copy
import numpy as np
import threading
import time


# ROS libraries
from geometry_msgs.msg import Pose2D
import rospy

# Local libraries
from resources import saveposes
import videosensor


class CameraThread(threading.Thread):
    """
    Child class of threading.Thread for capturing frames from a camera.

    The *run* method, where is specified the behavior when the *start*
    method is called, is overridden. At first, it loads the FPGA
    configuration. Then it enters an endless loop until *end_event*
    flag is raised. At each iteration, when possible, reads the FPGA
    register containing triangles location, processes the data and
    writes it to the global shared variable *triangles*.

    :param triangles: Dictionary where each element is an instance
     of *geometry.Triangle*. It is a global variable for sharing the
     information of different triangles detected in the camera space.
     Each triangle has a UNIQUE key identifier. It is used for
     writing and sending to other threads the triangle elements.

    :param ntriangles: READ ONLY dictionary of the same type and shape
     as *triangles*. It contains the triangles detected by other cameras
     that are inside the borders region of the current camera's space.

    :param begin_event: *threading.Event* object that is set to True
     when the FPGA is configured and the thread begins the main loop.

    :param end_event: *threading.Event* object that is set to True
     when the execution has to end.

    :param condition: *threading.Condition* object for synchronizing
     R/W operations on shared variables i.e. *triangles, inborders*.

    :param inborders: READ ONLY dictionary whose elements indicate if
     the corresponding triangle is located within the borders region
     of current camera's space. Its keys have an univocal correspondence
     with the key identifiers of the *triangles* dictionary.

    :param reset_flag: READ ONLY dictionary of boolean elements. They
     are set to True when its corresponding triangle exits the current
     camera's space.

    :param name: String that provides the name of the thread.

    :param conf_file: String containing the relative path to the
     configuration file of the camera.
    """

    def __init__(self, triangles, ntriangles, begin_event, end_event,
                 condition, inborders, reset_flag, name=None, conf_file=''):
        """Class constructor method."""
        threading.Thread.__init__(self, name=name)
        self.image = []
        self.cycletime = 0.02
        # Initialize TCP/IP connection and start FPGA operation.
        self.camera = videosensor.camera_startup(conf_file)
        # Synchronization variables
        self.begin_event = begin_event
        self.end_event = end_event
        self.condition = condition
        # Global and local dictionaries for writing the detected triangles.
        self.triangles = triangles
        self._triangles = copy.copy(self.triangles)
        # Global and local dictionaries for reading the new triangles.
        self.ntriangles = ntriangles
        self._ntriangles = copy.copy(self.ntriangles)
        # Global and local flags indicating if the UGVs are in borders region.
        self.inborders = inborders
        self._inborders = copy.copy(self.inborders)
        # Global flag indicating if ROI tracker has to be reset.
        self.reset_flag = reset_flag
        self._reset_flag = copy.copy(self.reset_flag)

    def run(self):
        """Main routine of the CameraThread."""
        # Look for shapes in whole image and configure trackers.
        self.image, _ = videosensor.set_tracker(self.camera)
        self.begin_event.set()
        while not self.end_event.isSet():
            # Start the cycle timer
            cycle_start_time = time.time()
            # Sync operations. Read global variables and update local ones.
            self.condition.acquire()
            self._inborders.update(self.inborders)
            self._ntriangles.update(self.ntriangles)
            self._reset_flag.update(self.reset_flag)
            self.condition.release()
            #
            # Get CARTESIAN coordinates of the 8 contour points in tracker.
            # The code ONLY tracks the UGV with id=1.
            #
            try:
                locations = self.camera.get_register('ACTUAL_LOCATION')['1']
            except KeyError:
                #
                # Set a new tracker if the inborders flag is raised and
                # The corresponding tracker is empty (if KeyError).
                #
                if self._inborders['1']:
                    # Apply inverse homography and transform global to local.
                    self._ntriangles['1'].inverse_homography(self.camera._H)
                    self._ntriangles['1'].global2local(self.camera.offsets, K=4)
                    # get window and set tracker
                    self.image.triangles = [self._ntriangles['1']]
                    videosensor.set_tracker(self.camera, self.image)
                continue
            # Scale the contours obtained according to the FPGA to image ratio.
            contours = np.array(locations) / self.camera._scale
            # Convert from Cartesian to Image coordinates
            tmp = np.copy(contours[:,0])
            contours[:,0] = contours[:,1]
            contours[:,1] = tmp
            self.image.contours = [contours]
            # Correct barrel distortion.
            self.image.correct_distortion()
            # Obtain 3 vertices from the contours
            shapes = self.image.get_shapes(get_contours=False)
            # If triangles are detected, calculate coordinates.
            if len(shapes):
                self._triangles['1'] = shapes[0]
                # Obtain global cartesian coordinates with a scale ratio 4:1.
                self._triangles['1'].local2global(self.camera.offsets, K=4)
                self._triangles['1'].homography(self.camera._H)
            # If any triangle is detected, indicate it writing a None variable.
            else:
                self._triangles['1'] = None
            # Free the ROI tracker if corresponding flag was raised
            if self._reset_flag['1']:
                self.camera.set_register('FREE_TRACKER', '1')
                rospy.loginfo('{} TRACKER FREED'.format(self.name))
                self._reset_flag = {'1': False}
                self._triangles.pop('1', None)
            # Sync operations. Write to global variables.
            self.condition.acquire()
            if self._triangles.has_key('1'):
                self.triangles.update(self._triangles)
            else:
                self.triangles.clear()
            self.condition.release()
            # Sleep the rest of the cycle
            while (time.time() - cycle_start_time < self.cycletime):
                pass
        rospy.logdebug('shutting down {}'.format(self.name))
        self.camera.disconnect_client()


class DataFusionThread(threading.Thread):
    """
    Child class of threading.Thread for merging and processing data.

    The *run* method, where is specified the behavior when the *start*
    method is called, is overridden. At first, it waits until all cameras
    are initialized. Then it enters an endless loop until the
    *end_event* flag is raised. At each iteration:

    - Check the triangles found by each *CameraThread*.
    - When a camera detects a triangle, it determines if the triangle is
      in the borders region of another camera. If that is True, orders
      the creating of a new ROI tracker in the second camera.
    - Evaluate if an UGV exits a camera, deleting the ROI tracker if
      it is True.
    - Merge the information obtained in all the cameras and write it in
      a ROS topic

    :param triangles: READ ONLY List containing N dictionaries, where
     N is the number of Camera threads. Each dictionary element is the
     set of coordinates of an UGV inside the Nth camera.

    :param ntriangles: WRITE N-len list of the same type and shape as
     *triangles*, for exchanging triangles information between
     *CameraThreads*.

    :param conditions: List containing N *threading.Condition* objects.
     They are used for synchronizing the *CameraThreads* and the
     *DataFusionThread* when doing R/W operations on shared variables.

    :param inborders: List containing N dictionaries. Each dictionary
     element is a flag set to True when the UGV is within the Nth camera
     borders region.

    :param quadrant_limits: List containing N 4x2 arrays. Each array
     contains the 4 points defining the working space of the Nth camera.

    :param end_event: *threading.Event* object that is set to True when
     the *UserThread* detects an 'end' order from the user.

    :param publisher: *rospy.Publisher* object for sending pose values to
     a ROS topic, that can be read by other ROS nodes.

    :param reset_flags: List containing N dictionaries whose entries are
     flags set to True when a ROI tracker in specified FPGA to be reset.

    :param name: String containing the name of the current thread.
    """

    def __init__(self, triangles, ntriangles, conditions, inborders,
                 quadrant_limits, begin_events, end_event, reset_flags,
                 publisher, name='Fusion Thread'):
        """
        Class constructor method
        """
        threading.Thread.__init__(self, name=name)
        self.publisher = publisher
        self.cycletime = 0.02
        self.quadrant_limits = quadrant_limits
        # Synchronization variables
        self.conditions = conditions
        self.begin_events = begin_events
        self.end_event = end_event
        # Shared lists. Can be accessed by other threads.
        self.triangles = triangles
        self.ntriangles = ntriangles
        self.inborders = inborders
        self.reset_flags = reset_flags
        # Local lists. Can only be R/W by this thread.
        self._triangles = copy.copy(self.triangles)
        self._ntriangles = copy.copy(self.ntriangles)
        self._inborders = copy.copy(self.inborders)
        self._reset_flags = copy.copy(self.reset_flags)
        # Name of the output file for the poses historic values.
        self.filename = "{}".format(time.strftime("%d_%m_%Y_%H%M"))
        # Array to save poses historic values.
        self.array2save = np.array(['time','pos x','pos y','angle'])
        # Boolean to save time by detecting first triangle
        self.first_triangle = True
        self.initial_time = 0
        

    def run(self):
        """Main routine of the DataFusionThread."""
        # Wait until all cameras are initialized
        for event in self.begin_events:
            event.wait()
        triangle = []
        while not self.end_event.isSet():
            # Start the cycle timer
            cycle_start_time = time.time()
            # Loop with N iterations, being N the number of camera threads.
            for index, condition in enumerate(self.conditions):
                # Threads synchronized instructions.
                condition.acquire()
                # Read shared variables and store in local ones
                self._triangles[index].update(self.triangles[index])
                self._reset_flags[index].update(self.reset_flags[index])
                condition.release()
                #
                # Evaluate if the triangle is in the borders regions.
                #
                if self._triangles[index]:
                    # Check that the element is not of None type.
                    if self._triangles[index]['1']:
                        triangle = self._triangles[index]['1']
                        # Evaluate if triangle is in borders region.
                        self._inborders[index]['1'] = triangle.in_borders(
                                self.quadrant_limits[index])
                    # If dictionary element is None, skip to next camera.
                    else:
                        continue
                # If the element is void, skip to next camera.
                else:
                    continue
                #
                # The following instructions will only be executed if a triangle
                # is detected in the scanned CameraThread (with id 'index').
                #
                # Check in the other quadrants if the triangle is in borders.
                #
                for index2, quadrant in enumerate(self.quadrant_limits):
                    # Do not run the function for the current quadrant.
                    if index2 == index:
                        continue
                    self._inborders[index2]['1'] = triangle.in_borders(
                            self.quadrant_limits[index2])
                    # Update triangles[index2] if there is not any tracker
                    # initialized and UGV is within borders of the Camera.
                    if (self._inborders[index2]['1'] and not
                    self._triangles[index2]):
                        self._ntriangles[index2]['1'] = copy.copy(triangle)
                        self._reset_flags[index2]['1'] = False
                        rospy.loginfo("New triangle in Camera{}".format(
                                index2))
                    # If the UGV is not in borders, but a tracker is set and is
                    # returning None values, it has to be reset.
                    elif (not self._inborders[index2]['1'] and
                                  self._triangles[index2].get('1', False) is None):
                        self._reset_flags[index2]['1'] = True
                        self._ntriangles[index2].pop('1', None)
                    # If the UGV is not in borders and any tracker was detected,
                    # the reset flag has to be cleared.
                    elif (not self._inborders[index2]['1'] and
                                  self._triangles[index2].get('1', False) is False):
                        self._reset_flags[index2]['1'] = False
                        self._ntriangles[index2].pop('1', None)
                    # Sync operations. Write to global variables
                    self.conditions[index2].acquire()
                    self.ntriangles[index2].update(self._ntriangles[index2])
                    self.inborders[index2].update(self._inborders[index2])
                    self.reset_flags[index2].update(self._reset_flags[index2])
                    self.conditions[index2].release()
            # TODO merge the content of every dictionary in triangle

            # Scan for detected triangle and publish it.
            for element in self._triangles:
                if element.has_key('1'):
                    if element['1'] is not None:
                        triangle = copy.copy(element['1'])
            if triangle:            
                pose = triangle.get_pose()
                # Convert coordinates to meters.
                mpose = [pose[0] / 1000, pose[1] / 1000, pose[2]]
                # Differential time variable.
                while self.first_triangle:
                    self.initial_time = time.time()
                    self.first_triangle = False
                diff_time = time.time() - self.initial_time
                # Time formatted without decimals.
                formatted_time = "{:.{prec}}".format(diff_time, prec=3)
                # Temporary array to save time and pose in meters.
                temp_array = np.array([formatted_time, pose[0], pose[1],
                                       pose[2]])
                # Array to save data.
                self.array2save = np.vstack((self.array2save, temp_array))
                rospy.logdebug("detected triangle at {}mm and {} radians."
                               "".format(pose[0:2], pose[2]))
                self.publisher.publish(Pose2D(mpose[0], mpose[1], mpose[2]))
            rospy.loginfo("Triangles at: {}".format(self._triangles))
            #            rospy.loginfo("Borders: {}".format(self._inborders))
            # Sleep the rest of the cycle
            while (time.time() - cycle_start_time < self.cycletime):
                pass
        # Instructions to execute after end_event is raised.
        self.initial_time = time.time()
        wait = True
        # Wait time to enter test speed
        while wait:
            if (time.time() - self.initial_time) > 0.2:
                wait = False
        # Test speed to filename
        sLeft = input("Introduce sLeft of test\n")
        sRight = input("Introduce sRight of test\n")
        # Save poses in spreadsheet.
        saveposes.data2spreadsheet(self.array2save,
                "tmp/{}-L{}-R{}.xlsx".format(self.filename, sLeft, sRight))
        # Save poses in textfile.
        saveposes.data2textfile(self.array2save,
                "tmp/{}-L{}-R{}.txt".format(self.filename, sLeft, sRight))


class UserThread(threading.Thread):
    """
    Child class of threading.Thread for interacting with user.

    The *run* method, where is specified the behavior when the *start*
    method is called, is overridden. Ask the user for commands through
    keyboard.

    :param begin_events: List with N *threading.Event* objects, where N
     is the number of Camera threads. Until the set up of every camera
     is finished, the user can not interact with this thread.

    :param end_event: *threading.Event* object that is set to True when
     the *UserThread* detects an 'end' order from the user.
    """

    def __init__(self, begin_events, end_event, name='User Thread'):
        """Class constructor method."""
        threading.Thread.__init__(self, name=name)
        self.begin_events = begin_events
        self.end_event = end_event
        self.cycletime = 0.5

    def run(self):
        """Main routine of the UserThread."""
        # Wait until all camera threads start.
        for event in self.begin_events:
            event.wait()
        rospy.loginfo("All cameras were initialized")
        while not self.end_event.isSet():
            # Start the cycle timer
            cycle_start_time = time.time()
            i = raw_input("Press 'Q' to stop the script... ")
            if i == 'Q':
                self.end_event.set()
            # Sleep the rest of the cycle
            while (time.time() - cycle_start_time < self.cycletime):
                pass


def main():
    """
    Main routine for multiplecamera.py

    Read configuration files, initialize variables and set up threads.
    :return:
    """
    rospy.init_node('uvisensor')
    publisher = rospy.Publisher('/robot_1/pose2d', Pose2D, queue_size=1)
    rospy.loginfo("BEGINNING MAIN EXECUTION")
    # Get the relative path to all the config files stored in /config folder.
    conf_files = glob.glob("./resources/config/*.cfg")
    conf_files.sort()
    threads = []
    # A Condition object for each camera thread execution.
    conditions = []
    # Shared variable for storing triangles. Writable only by CameraThreads.
    triangles = [{}, {}, {}, {}]
    # Shared variable for storing triangles. Writable only by DataFusionThread.
    ntriangles = [{}, {}, {}, {}]
    # Shared variable for storing the presence of UGVs in borders regions.
    inborders = [{'1': False}, {'1': False}, {'1': False}, {'1': False}]
    # Shared variable flags indicating ROI trackers reset orders.
    reset_flags = [{'1': False}, {'1': False}, {'1': False}, {'1': False}]
    # A begin event for each camera will be created
    begin_events = []
    end_event = threading.Event()
    # New thread instantiation for each configuration file.
    for index, fname in enumerate(conf_files):
        conditions.append(threading.Condition())
        begin_events.append(threading.Event())
        threads.append(CameraThread(triangles[index], ntriangles[index],
                                    begin_events[index], end_event,
                                    conditions[index], inborders[index],
                                    reset_flags[index],
                                    'Camera{}'.format(index), fname))
    # List containing the points defining the space limits of each camera.
    quadrant_limits = []
    for camera_thread in threads:
        quadrant_limits.append(camera_thread.camera._limits)
    # Thread for merging the data obtained at every CameraThread.
    threads.append(DataFusionThread(triangles, ntriangles, conditions,
                                    inborders, quadrant_limits, begin_events,
                                    end_event, reset_flags, publisher))
    # Thread for getting user input.
    threads.append(UserThread(begin_events, end_event))
    # start threads
    for thread in threads:
        thread.start()
    # wait for threads to end
    for thread in threads:
        thread.join()


if __name__ == '__main__':
    main()
