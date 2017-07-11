#!/usr/bin/env python
"""Auxiliary program for manipulate data of poses and time.

This module allows:
-Read data of poses with their respective time, from a spreadsheet.
-Analyze data by calculating differential values of position, time and
 lenght displaced and average speed of UGV
-Save data in spreadsheet and textfile.
-Save final data in master sheet.
"""
# Standard libraries
import glob
import numpy as np
import os
import re
from scipy import stats
import sys
import time
# Excel read/write library
import openpyxl
# Local libraries
import workbookfunctions

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
    :param float64 avg_speed: average linear speed of UGV.
    :param float64 avg_ang_speed: average angular speed of UGV.
    """
    def __init__(self):

        self.process_data = {
            'raw_data' : np.zeros((1,4))
            'analyzed_data' : np.zeros((1,11))
            'avg_speed' : 0
            'avg_ang_speed' : 0
            'filename' : None
            'sp_left' : 0
            'sp_right' 0
            'exp_conditions' : ""
            'data_to_save' : 0
            'header' : ""
            'save_analyzed' : False
        }

    def upload_data(self, data):
        """Update data matrix with time and poses.

        :param data: Matrix of floats64 with M data.
        :type data: numpy.array float64 (shape=Mx4).
        :return: updated data.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        self.process_data['raw_data'] = np.copy(data)
        return data

    def upload_setpoints_save(self, sp_left, sp_right):

        self.process_data['sp_left'] = sp_left
        self.process_data['sp_right'] = sp_right

        return sp_left, sp_right

    def upload_filename_save(self, filename):

        self.process_data['filename'] = filename

        return filename

    def remove_repeated_poses(self):
        """Remove repeated pose values.

        When the camera does not detect a triangle, the pose value is
        not updated, remaining the current pose as the previous pose.
        With this method, these values are eliminated.

        :return: data without repeated values.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        # New data is correct when at least one value of pose are different.
        work_data = np.copy(self.process_data['raw_data'])
        rows = work_data.shape[0]
        # Initialization data arrays.
        last_data = np.array([0, 0, 0, 0]).astype(np.float64)
        filtered_data = np.array([0, 0, 0, 0]).astype(np.float64)
        for row in range(rows):
            # New dara read array.
            new_data = np.copy(work_data[row, :])
            different_values = np.any(new_data[1:4] != last_data[1:4])
            if different_values:
                last_data = np.copy(new_data)
                if row == 0:
                    # Initialization filtered_data array.
                    filtered_data = np.copy(new_data)
                else:
                    filtered_data = np.vstack([filtered_data, new_data])
        self.process_data['raw_data'] = np.copy(filtered_data)
        return filtered_data

    def remove_stop_poses(self):
        """Remove stop pose values.

        This method eliminates the initial and final values in which the
        UGV is stopped.

        :return: data without stop values.
        :rtype: numpy.array float64 (shape=Mx4).
        """
        work_data = np.copy(self.process_data['raw_data'])
        rows = work_data.shape[0]
        # Initialization first and last rows witout poses with stopped UGV.
        row_upper = 0
        row_lower = rows
        # Initial repeated data calculation.
        mode_upper = stats.mode(work_data[0:20, 1:3])[0]
        mode_rows = np.all(work_data[:, 1:3]==mode_upper, axis=1)
        indexes = np.where(mode_rows)[0]
        # If there are not initial values of stopped UGV is not updated.
        if indexes.shape[0] > 0:
            row_upper = indexes.max()
        # Final repeated data calculation.
        mode_lower = stats.mode(work_data[(rows-20):rows, 1:3])[0]
        mode_rows = np.all(work_data[:, 1:3]==mode_lower, axis=1)
        indexes = np.where(mode_rows)[0]
        # If there are not final values of stopped UGV is not updated.
        if indexes.shape[0] > 0:
            row_lower = indexes.min() + 1
        # UGV data in motion.
        clipped_data = work_data[row_upper:row_lower, :]
        self.process_data['raw_data'] = np.copy(clipped_data)
        return clipped_data

    def get_diff_data(self):
        """Get differential data and relative linear and angular speed.

        Difference data are obtained between two consecutive samples,
        and linear and angular speeds are calculated from them.

        It also obtain the absolute linear and angular velocity of the
        experiment.

        :returns: [formatted_data, avg_speed, avg_ang_speed]
          * *formatted_data* data with differential values and angular
            and linear speeds.
          * *avg_speed* average linear speed of UGV.
          * *avg_ang_speed* average angular speed of UGV.
        :rtype: [numpy.array float64 (shape=Mx11), float64, float64]
        """
        # Calculate differential values.
        work_data = np.copy(self._raw_data)
        rows = self._raw_data.shape[0]
        # First sample, time zero.
        work_data[:, 0] -= work_data[0, 0]
        # Differential data matrix: current data minus previous data.
        diff_data = np.zeros_like(work_data)
        diff_data[1:rows, :] = work_data[1:rows, :] - work_data[0:(rows-1), :]
        # first_row = np.zeros((1,4))
        # diff_data = np.vstack([first_row, diff_data])
        # Vector differential length displaced.
        diff_length = np.sqrt(diff_data[:, 1]**2 + diff_data[:, 2]**2)
        # The direction is negative when the angular speed and vehicle angle
        # difference is bigger than pi/2 (90 degrees).
        speed_angles = np.arctan2(diff_data[:, 2], diff_data[:, 1])
        #import pdb; pdb.set_trace()
        sign_spd = np.ones([(rows), 1])
        sign_spd[np.abs(work_data[:, 3] - speed_angles) > (np.pi/2)] *= -1
        diff_speed = sign_spd[1:, 0] * 1000 * diff_length[1:]/diff_data[1:, 0]
        diff_speed = np.hstack([0, diff_speed])
        # Vector differential angular speed.
        diff_angl_speed = np.zeros(rows)
        diff_angl_speed[1:rows] = 1000 * diff_data[1:rows, 3] / diff_data[1:rows, 0]
        # Complete differential data matrix with new data.
        # diff_data = np.hstack([np.zeros(rows, 1), diff_data])
        diff_data = np.insert(diff_data, 4, diff_length, axis=1)
        diff_data = np.insert(diff_data, 5, diff_speed, axis=1)
        diff_data = np.insert(diff_data, 6, diff_angl_speed, axis=1)
        # Complete data matrix with differential_data.
        work_data = np.hstack([work_data, diff_data])
        # Average speed and average angular speed.
        sum_data = diff_data.sum(axis=0)
        length = np.sqrt(((work_data[rows-1,1] - work_data [0, 1])**2)
                           + ((work_data[rows-1,2] - work_data [0, 2])**2))
        sum_data = diff_data.sum(axis=0)
        avg_speed = np.round((1000*length/sum_data[0]), 2)
        avg_ang_speed = np.round(((1000*(work_data[rows-1, 3]
                                   - work_data [0, 3]))/sum_data[0]), 2)
        formatted_data = np.round(work_data, 2)
        self.process_data['analyzed_data'] = np.copy(formatted_data)
        self.process_data['avg_speed'] = avg_speed
        self.process_data['avg_ang_speed'] = avg_ang_speed
        return (formatted_data, avg_speed, avg_ang_speed)

    def save2data(self, save_analyzed=False):
        self._save_analyzed = save_analyzed
        if self._save_analyzed:
            work_data = np.copy(self._analyzed_data)
            # Header construction.
            self._header = np.array(['Time', 'Pos x', 'Pos y', 'Angle',
                                    'Diff Time', 'Diff Posx', 'Diff Posy',
                                    'Diff Angl', 'Diff Leng', 'Rel Speed',
                                    'Rel AnSpd'])
        else:
            work_data = np.copy(work_data)
            # Header construction.
            self._header = np.array(['Time', 'Pos x', 'Pos y', 'Angle'])
        #First sample, time zero.
        rows, cols = work_data.shape
        work_data[:, 0] = work_data[:, 0] - work_data[0, 0]
        self._data_to_save = np.copy(work_data)
        # Name of the output file for the poses historic values.
        if not self._filename:
            exist_file = glob.glob("datatemp/*.xlsx")
            exist_file.sort()
            index = len (exist_file)
            datestamp_file = "{}".format(time.strftime("%d_%m_%Y"))
            self._filename = "{}_{}-L{}-R{}".format(datestamp_file, (index+1),
                            self._sp_left, self._sp_right)
            datestamp_text = '{}_{}'.format(datestamp_file, (index+1))
        name_txt = "datatemp/{}.txt".format(self._filename)
        #Header for numpy savetxt.
        header_numpy = ''
        cols = self._header.shape[0]
        for col in range (0, cols):
            element = self._header[col]
            element = '%9s' % (element)
            header_numpy = '{}{}\t'.format(header_numpy, element)
        #Call to save data in textfile.
        np.savetxt(name_txt, work_data, delimiter='\t', fmt='%9.2f',
                   header=header_numpy, comments='')
        #Experiment conditions.
        self._exp_conditions = (" -Use camera 3\n -Position initial experiment forward: "
                          "right rear wheel profile (-1400, -600), rear axis UGV in "
                          "axis y, in -1800 x\n -Time: 3 seconds")
        self.write_spreadsheet()
        return work_data

    def save2master_txt(data_master):
        """
        Average speed, setpoint left and right wheels are saved in the same textfile.

        :param data_master: array that contains the average lineal speed, the
        average angular speed, the set point left, the set point right, and the
        name of datafile.
        """
        #TODO improve format
        cols = data_master.shape[0]
        for y in range (0, cols):
            value = data_master[y]
            if y == 0:
                #TODO use '.format' string construction style
                text = '%9s' % (value)
            else:
                value = float(value)
                value = '%9.2f' % (value)
                text = '{}\t\t{}'.format(text, value)
        text = '{}\n'.format(text)
        with open("datatemp/masterfile4.txt", 'a') as outfile:
            outfile.write(text)


def main():
    # o_exist_file = glob.glob("./datatemp/*.xlsx")
    # o_exist_file.sort()
    # o_index = len (o_exist_file)
    # names = [os.path.basename(x) for x in o_exist_file]
    # import pdb; pdb.set_trace()
    # for y in range (0, o_index-1):
    #     #import pdb; pdb.set_trace()
    #     print names[y]
    #     data_matrix = read_data(name_spreadsheet='datatemp/' + names[y])
    #
    # #numbers_filename = re.findall(r'\d+', name_spreadsheet)
    # #sp_left = int(numbers_filename[4])
    # #sp_right = int(numbers_filename[5])
    #
    #
    # #TODO Try, except correct value.
    # sp_left = input("Introduce value of sp_left between 0 and 255\n")
    # sp_right = input("Introduce value of sp_right between 0 and 255\n")
    new_wb = workbookfunctions.SensorDataWorkbook()
    data1 = new_wb.read_data()
    # treatment = DataSaver()
    # treatment.upload_data(data1)
    # treatment.get_diff_data()
    # treatment.save2data(True)

if __name__ == '__main__':
    main()
