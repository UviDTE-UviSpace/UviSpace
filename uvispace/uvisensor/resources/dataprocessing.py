#!/usr/bin/env python
"""Auxiliary program for manipulate and save data of poses and time.

This module allows:
-Analyze data by calculating differential values of position, time and
 lenght displaced and relative linear and angular speed of UGV.
-Save data in spreadsheet and text file.
-Save final data in master sheet and master text file.

Also contains auxiliary function to store data using a certain workflow.
"""
# Standard libraries
import glob
import numpy as np
import os
import re
from scipy import stats
import sys
import time
# Local libraries
import workbookfunctions as wf

class DataAnalyzer(object):
    """Receives time and poses of matrix to filter, analyze and save.

    Different time and position values are calculated between two data
    points. From these, the linear average speed and the angular average
    speed are calculated.

    :param data: Matrix of floats64 with M data.
    :type data: numpy.array float64 (shape=Mx4).
    :param analyzed_data: Matrix with M analyzed data after calculating.
     differential values and relative linear and angular speeds.
    :type analyzed_data: numpy.array float64 (shape=Mx11).
    :param float64 avg_lin_spd: average linear speed of UGV.
    :param float64 avg_ang_spd: average angular speed of UGV.
    :param int sp_left: left speed setpoint.
    :param int sp_right: right speed setpoint.
    """
    def __init__(self):
        self._raw_data = np.zeros((1,4))
        self._analyzed_data = np.zeros((1,11))
        self._avg_lin_spd = 0
        self._avg_ang_spd = 0
        self._sp_left = 0
        self._sp_right = 0

    def set_data(self, data):
        """Update raw_data matrix with time and poses.

        :param data: Matrix of floats64 with M data.
        :type data: numpy.array float64 (shape=Mx4).
        :return: data matrix loaded.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        self._raw_data = np.copy(data)
        return data

    def set_setpoints(self, sp_left, sp_right):
        """Update sp_left and sp_right with new setpoints values.

        :param int sp_left: left speed setpoint.
        :param int sp_right: right speed setpoint.
        :return: setpoints loaded.
        :rtype: (int, int)
        """
        self._sp_left = sp_left
        self._sp_right = sp_right
        return (sp_left, sp_right)

    def remove_repeated_poses(self):
        """Remove repeated pose values from the raw_data matrix.

        When the camera does not detect a triangle, the pose value is
        not updated. With this method, these values are eliminated.

        :return: data without repeated values.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        # Initialization data arrays.
        last_data = np.zeros((1,4)).astype(np.float64)
        filtered_data = np.zeros((1,4)).astype(np.float64)
        # TODO substitute the for loop by numpy methods.
        for row in range(self._raw_data.shape[0]):
            # New dara read array.
            if np.any(self._raw_data[row, 1:4] != last_data[:, 1:4]):
                last_data = np.copy(self._raw_data[row]).reshape(1,4)
                if row == 0:
                    # Initialization filtered_data array.
                    filtered_data = np.copy(self._raw_data[row]).reshape(1,4)
                else:
                    filtered_data = np.vstack([filtered_data,
                                               self._raw_data[row]])
        # Unnecesary update raw_data if only have one data.
        if self._raw_data.shape[0] > 1:
            self._raw_data = np.copy(filtered_data)
        return filtered_data

    def remove_stop_poses(self):
        """Remove stop pose values for the raw_data matrix.

        This method eliminates the initial and final values in which the
        UGV is stopped.

        NOTE: This method implies that on a normal execution there will
        be more than 20 captured poses.

        :return: data without stop values.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        rows = self._raw_data.shape[0]
        # Initialization first and last rows witout poses with stopped UGV,
        # before and after movement.
        row_upper_index = 0
        row_lower_index = rows
        # Initial repeated data calculation. We work with the first 20 data,
        # assuming that the array will have more than 20 data (data collected
        # for at least 4 seconds).
        upper_mode = stats.mode(self._raw_data[0:20, 1:3])[0]
        mode_rows = np.all(self._raw_data[:, 1:3]==upper_mode, axis=1)
        mode_indexes = np.where(mode_rows)[0]
        # If there are not initial values of stopped UGV is not updated.
        if mode_indexes.shape[0] > 0:
            row_upper_index = mode_indexes.max()
        # Final repeated data calculation. We work with the first 20 data
        # assuming that the array will have more than 20 data (data collected
        # for at least 4 seconds).
        lower_mode = stats.mode(self._raw_data[(rows-20):rows, 1:3])[0]
        mode_rows = np.all(self._raw_data[:, 1:3]==lower_mode, axis=1)
        mode_indexes = np.where(mode_rows)[0]
        # If there are not final values of stopped UGV is not updated.
        if mode_indexes.shape[0] > 0:
            row_lower_index = mode_indexes.min() + 1
        # UGV data in movement.
        # The next case happen if the UGV is stopped always. Small errors in the
        # data taken, imply that the lower row is above the upper row.
        if row_upper_index > row_lower_index:
            clipped_data = self._raw_data[0,:].reshape(1, 4)
        # Normal movement.
        else:
            clipped_data = self._raw_data[row_upper_index:row_lower_index, :]
        self._raw_data = np.copy(clipped_data)
        return clipped_data

    def get_processed_data(self):
        """Get differential data and relative linear and angular speed.

        Differential data is obtained between two consecutive samples,
        and relative linear and angular speeds are calculated from
        them.

        The absolute linear and angular speeds of the experiment is also
        obtained.

        :returns: [formatted_data, avg_lin_spd, avg_ang_spd]
          * *formatted_data* data with differential values and angular
            and linear speeds.
          * *avg_lin_spd* average linear speed of UGV.
          * *avg_ang_spd* average angular speed of UGV.
        :rtype: [numpy.array float64 (shape=Mx11), float64, float64]
        """
        # work_data is the data matrix to be manipulated in this function.
        work_data = np.copy(self._raw_data)
        rows = work_data.shape[0]
        # Unnecesary to manipulate raw_data if there is only one sample.
        if rows > 1:
            # First sample, time zero.
            work_data[:, 0] -= work_data[0, 0]
            # Differential data matrix: current sample minus previous sample in
            # data.
            diff_data = np.zeros_like(work_data)
            diff_data[1:] = work_data[1:] - work_data[0: -1]
            # Vector differential length displaced.
            diff_length = np.sqrt(diff_data[:, 1]**2 + diff_data[:, 2]**2)
            # The direction is negative when the angular speed and vehicle angle
            # difference is bigger than pi/2 (90 degrees).
            speed_angles = np.arctan2(diff_data[:, 2], diff_data[:, 1])
            # The sign of the UGV speed represents the direction on X axis.
            sign_spd = np.ones([(rows), 1])
            sign_spd[np.abs(work_data[:, 3] - speed_angles) > (np.pi/2)] *= -1
            # Vector differential length displaced.
            diff_speed = np.zeros(rows)
            diff_speed[1:] = (sign_spd[1:, 0] * 1000 * diff_length[1:]
                              / diff_data[1:, 0])
            # Vector differential angular speed.
            diff_angl_speed = np.zeros(rows)
            diff_angl_speed[1:] = 1000 * diff_data[1:, 3] / diff_data[1:, 0]
            # Complete differential data matrix with new data.
            diff_data = np.insert(diff_data, 4, diff_length, axis=1)
            diff_data = np.insert(diff_data, 5, diff_speed, axis=1)
            diff_data = np.insert(diff_data, 6, diff_angl_speed, axis=1)
            # Complete work_data matrix with differential data.
            work_data = np.hstack([work_data, diff_data])
            # Calculate average linear and angular speeds.
            sum_data = diff_data.sum(axis=0)
            total_length = np.sqrt((work_data[-1, 1] - work_data [0, 1])**2
                                    + (work_data[-1, 2] - work_data [0, 2])**2)
            avg_lin_spd = np.round((1000*total_length/sum_data[0]), 2)
            avg_ang_spd = np.round((1000*(work_data[-1, 3]
                                    - work_data [0, 3]))/sum_data[0], 2)
            formatted_data = np.round(work_data, 2)
            self._analyzed_data = np.copy(formatted_data)
            self._avg_lin_spd = avg_lin_spd
            self._avg_ang_spd = avg_ang_spd
        # Case that there is only one sample.
        else:
            self._analyzed_data[:, :4] = self._raw_data
            formatted_data = 0
            avg_lin_spd = 0
            avg_ang_spd = 0
        return (formatted_data, avg_lin_spd, avg_ang_spd)

    def save2data(self, save_analyzed=False, save2master=False):
        """Saves the poses data in a spreadsheet and in a text file.

        This function prepares the name of the file, the headers, and
        the conditions of the experiment performed. Once this is done,
        the data is saved in a text file, and the write function is
        called.

        Optionally, linear and angular absolute speed data can be stored
        in a master file.

        :param bool save_analyzed: this parameter determines if analyzed
         data (True) or raw data (False) is saved.
        :param bool save2master: this parameter determines if analyzed
         absolute speeds is saved or not in a master file.
        :return: data to save in spreadsheet and text file.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        if save_analyzed:
            data_to_save = np.copy(self._analyzed_data)
            # Header construction.
            header = np.array(['Time', 'Pos x', 'Pos y', 'Angle', 'Diff Time',
                               'Diff Posx', 'Diff Posy', 'Diff Angl',
                               'Diff Leng', 'Rel LnSpd', 'Rel AnSpd'])
        else:
            data_to_save = np.copy(self._raw_data)
            # Header construction.
            header = np.array(['Time', 'Pos x', 'Pos y', 'Angle'])
        # Determine the number of previously saved experiments in order to add
        # the corresponding index to the file name. It is obtained from the
        # number of spreadsheets in the 'datatemp' folder.
        xlsx_files = glob.glob("datatemp/*.xlsx")
        xlsx_files.sort()
        index = len(xlsx_files)
        datestamp = "{}".format(time.strftime("%d_%m_%Y"))
        # The experiment name is formed by the experiment date, its number and
        # the speed setpoints.
        exp_name = "{}_{}-L{}-R{}".format(datestamp, (index+1), self._sp_left,
                                          self._sp_right)
        txt_name = "datatemp/{}.txt".format(exp_name)
        # Header for save data with numpy savetxt.
        numpy_header = ""
        for element in header:
            numpy_header = "{}{:>9}\t".format(numpy_header, element)
        # Call to save data in textfile.
        np.savetxt(txt_name, data_to_save, delimiter='\t', fmt='%9.2f',
                   header=numpy_header, comments='')
        # Add (or subtract) the relative distance from the triangle base to the
        # UGV corner.
        pos_x_init = int(data_to_save[0, 1] - 52)
        pos_y_init = int(data_to_save[0, 2] + 110)
        exp_conditions = ("Initial position of the UGV in the experiment:\n"
                          "-point of contact with the ground of profile of "
                          "right rear wheel ({0}, {1})\n-rear axis UGV in {0} x"
                          "".format(pos_x_init, pos_y_init))
        # Call to function to write to spreadsheet.
        wf.write_spreadsheet(header, data_to_save, exp_name,
                             exp_conditions, save_analyzed)
        # Only data can be saved in the master file if the analyzed data has
        # been saved.
        if save_analyzed and save2master:
            wf.save2master_xlsx(exp_name, self._sp_left, self._sp_right,
                                self._avg_lin_spd, self._avg_ang_spd)
            self.save2master_txt(exp_name)
        return data_to_save

    def save2master_txt(self, exp_name):
        """Save linear and angular speeds data in master text file.

        :param str exp_name: name of performed experiment.
        """
        #TODO improve format
        data_master = np.array([exp_name, self._sp_left, self._sp_right,
                                self._avg_lin_spd, self._avg_ang_spd])
        for value in data_master:
            if value == exp_name:
                #TODO use '.format' string construction style
                text = "{:>9}".format(value)
            else:
                value = float(value)
                text = '{}\t\t{}'.format(text, value)
        text = '{}\n'.format(text)
        with open("datatemp/masterfile.txt", 'a') as outfile:
            outfile.write(text)
        return


def process_data(data, save_analyzed=False, save2master=False):
    """Auxiliary function to store data using a certain workflow.

    From the obtained data, the positions in which the robot is stopped
    are eliminated, the repeated positions are eliminated because the
    camera does not detect another triangle, and the differential data,
    and the relative and absolute speeds data are obtained.

    Later, this data is stored in a text file and in a spreadsheet as
    is indicated.
    :param bool save_analyzed: this parameter determines if analyzed
     data (True) or raw data (False) is saved.
    :param bool save2master: this parameter determines if analyzed
     absolute speeds is saved or not in a master file.
    """
    # Analysis of data.
    analysis = DataAnalyzer()
    analysis.set_data(data)
    analysis.remove_stop_poses()
    analysis.remove_repeated_poses()
    analysis.get_processed_data()
    #TODO Try, except correct value.
    # Request the setpoints to the user.
    sp_left = input("Introduce value of sp_left between 0 and 255\n")
    sp_right = input("Introduce value of sp_right between 0 and 255\n")
    analysis.set_setpoints(sp_left, sp_right)
    # Data save.
    analysis.save2data(save_analyzed=save_analyzed, save2master=save2master)
    return
