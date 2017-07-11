"""Auxiliary program for manipulate data of poses and time.

"""
# Standard libraries

# Excel read/write library
import openpyxl

class SensorDataWorkbook(openpyxl.Workbook):

    """Dictionary with different formats to apply to the cells when writes
    the data in a spreadsheet.
    """
    cell_formats = {
        # Types of text alignment.
        'center_al': openpyxl.styles.Alignment(horizontal='center',
                                               vertical='center'),
        'right_al': openpyxl.styles.Alignment(horizontal='right',
                                              vertical='center'),
        # Types of font.
        'title_ft': openpyxl.styles.Font(color='FFFFFFFF', size=20, bold=True),
        'white_ft': openpyxl.styles.Font(color='FFFFFFFF', bold=True),
        # Types of border.
        'thick_bd': openpyxl.styles.Border(
                                    top=openpyxl.styles.Side(border_style='thick',
                                                             color='FF4143CA'),
                                    bottom=openpyxl.styles.Side(
                                           border_style='thick', color='FF4143CA')),
        'thin_bd': openpyxl.styles.Border(
                                       top=openpyxl.styles.Side(border_style='thin',
                                                                color='FF83C6D6'),
                                    bottom=openpyxl.styles.Side(border_style='thin',
                                                                color='FF83C6D6')),
        # Types of fill.
        'blue_fill': openpyxl.styles.PatternFill(fill_type='solid',
                                                 start_color='FF2F79E6',
                                                 end_color='FF2F79E6'),
        'skyblue_fill': openpyxl.styles.PatternFill(fill_type='solid',
                                                    start_color='FFDBF4FA',
                                                    end_color='FFDBF4FA'),
        'white_fill': openpyxl.styles.PatternFill(fill_type='solid',
                                                  start_color='FFFFFFFF',
                                                  end_color='FFFFFFFF')
    }
    def read_data(name_spreadsheet="31_05_2017_201-L255-R255b.xlsx"):
        """It allows to read poses and time of spreadsheet.

        These data are stored in the "data" matrix.

        Each group of data is composed to 4 elements about the location of
        the UGV at a given time: time, position "x", position "y" and angle
        "theta".

        :param str name_spreadsheet: name of spreadsheet that contain the
        data to be read.
        :return: matrix dimentions Mx4 with read data. M is the number of
        rows corresponding to the number of data read.
        :rtype: numpy.array(shape=Mx4)
        """
        # Open spreadsheet
        try:
            wb = load_workbook(name_spreadsheet)
        except IOError:
            wb = Workbook()
        ws = wb.active
        # Initialization of matrixes for data.
        data = np.array([0, 0, 0, 0]).astype(np.float64)
        new_data = np.array([0, 0, 0, 0]).astype(np.float64)
        # Rows 1 and 2 are for the file name, the next three rows describe the
        # experiment parameters, and the 6 is the header in any type file.
        # Start reading in row 7.
        row = 7
        # Number of columns in the matrix.
        cols = data.shape[0]
        # Loop for reading data.
        data_in_this_row = True
        while data_in_this_row:
            element = ws.cell(column=1, row=row).value
            # "Sum differerential data:" is the value of the next row to the last
            # data.
            if element == 'Sum differential data:':
                data_in_this_row = False
            else:
                # Reading data.
                for col in range (0, cols):
                    element = ws.cell(column=col+1, row=row).value
                    new_data[col] = element
                if row == 7:
                    # Substitution of row of zeros by first row of data read.
                    data = np.copy(new_data)
                else:
                    data = np.vstack([data, new_data])
                row +=1
        rounded_data = np.round(data, 2)
        return rounded_data

    def write_spreadsheet(self):
        """
        Receives poses and time, and saves them in a spreadsheet.

        :param header: contains header to save in spreadsheet.
        :param data: contains data to save in spreadsheet.
        :param filename: name of spreadsheet where the data will be saved.
        :param exp_conditions: contains string with experiment description.
        :param save_master: boolean with True for save data in masterfile.
        """
        name_spreadsheet = "datatemp/{}.xlsx".format(self._filename)
        try:
            wb = openpyxl.load_workbook(name_spreadsheet)
        except:
            wb = openpyxl.Workbook()
        ws = wb.active
        #Spreadsheet title.
        ws.merge_cells('A1:K2')
        ws.cell('A1').value = self._filename
        ws.cell('A1').alignment = cell_formats['center_al']
        ws.cell('A1').font = cell_formats['title_ft']
        ws.cell('A1').fill = cell_formats['blue_fill']
        #Experiment conditions.
        ws.merge_cells('A3:K5')
        ws.cell('A3').value = self._exp_conditions
        #Freeze header
        my_cell = ws['B7']
        ws.freeze_panes = my_cell
        #Write in spreadsheet the headboard.
        rows, cols = self._data_to_save.shape
        for col in range (0, cols):
            ws.cell(column=col+1, row=6, value=self._header[col])
            ws.cell(column=col+1, row=6).alignment = cell_formats['right_al']
            ws.cell(column=col+1, row=6).font = cell_formats['white_ft']
            ws.cell(column=col+1, row=6).fill = cell_formats['blue_fill']
            ws.cell(column=col+1, row=6).border = cell_formats['thick_bd']
        #Write in spreadsheet the data.
        for row in range(0, rows):
            for col in range(0, cols):
                element = float(self._data_to_save[row,col])
                ws.cell(column=col+1, row=row+7, value=element).number_format = '0.00'
                if row % 2 != 0:
                    ws.cell(column=col+1, row=row+7).fill = cell_formats[
                                                                 'skyblue_fill']
                else:
                    ws.cell(column=col+1, row=row+7).fill = cell_formats[
                                                                   'white_fill']
                my_cell = ws.cell(column=col+1, row=row+7)
                ws.column_dimensions[my_cell.column].width = 10
        #Write in spreadsheet the name of statistics.
        if self._save_analyzed:
            for row in range(rows+7, rows+11):
                ws.merge_cells(start_row=row,start_column=1,end_row=row,end_column=4)
                ws.cell(column=1, row=row).alignment = cell_formats['right_al']
                ws.cell(column=1, row=row).fill = cell_formats['blue_fill']
                ws.cell(column=1, row=row).font = cell_formats['white_ft']
            ws.cell(column=1, row=rows+7, value='Sum differential data:')
            ws.cell(column=1, row=rows+8, value='Mean of differential data:')
            ws.cell(column=1, row=rows+9, value='Variance differential data:')
            ws.cell(column=1, row=rows+10, value='Std deviation differential data:')
            ws.cell(column=8, row=rows+11, value='Linear Relative Speed:')
            ws.cell(column=8, row=rows+12, value='Angular Relative Speed:')
            ws.merge_cells(start_row=rows+11,start_column=8,end_row=rows+11,end_column=10)
            ws.merge_cells(start_row=rows+12,start_column=8,end_row=rows+12,end_column=10)
            ##Write and calculate in spreadsheet the statistics.
            for col in range(5, cols+1):
                letter_range = openpyxl.utils.get_column_letter(col)
                start_range = '{}{}'.format(letter_range, 7)
                end_range = '{}{}'.format(letter_range, rows+5)
                interval = '{}:{}'.format(start_range,end_range)
                ws.cell(column=col, row=rows+7, value= '=SUM({})\n'.format(interval))
                ws.cell(column=col, row=rows+8, value= '=AVERAGE({})\n'.format(interval))
                ws.cell(column=col, row=rows+9, value= '=VAR({})\n'.format(interval))
                ws.cell(column=col, row=rows+10, value= '=STDEV({})\n'.format(interval))
                for row in range(rows+7, rows+13):
                    ws.cell(column=col, row=row).number_format = '0.00'
                    ws.cell(column=col, row=row).font = cell_formats['white_ft']
                    ws.cell(column=col, row=row).fill = cell_formats['blue_fill']
                    ws.cell(column=col, row=row).alignment = cell_formats['right_al']
            ws.cell(column=11, row=rows+11, value= '=1000*SQRT(((B{rows}-B7)^2)+'
                    '(((C{rows}-C7)^2)))/E{rows2}\n'.format(rows=rows+5, rows2=rows+7))
            ws.cell(column=11, row=rows+12, value= '=1000*(D{rows}-D7)/'
                                        'E{rows2}\n'.format(rows=rows+5, rows2=rows+7))
        wb.save(name_spreadsheet)

        return name_spreadsheet

    def save2master_xlsx(data_master):
        """
        Average speed, setpoint left and right wheels are saved in the same spreadsheet.

        :param data_master: array that contains the average lineal speed, the
        average angular speed, the set point left, the set point right, and the
        name of datafile.
        """
        #Data search to save in masterspreadsheet.
        folder = '\'file:///home/jorge/UviSpace/uvispace/uvisensor/'
        name_sheet = '\'#$Sheet.'
        try:
            wb = openpyxl.load_workbook(data_master[3])
        except:
            wb = openpyxl.Workbook()
        ws = wb.active
        #Next empty row search.
        row = 7
        written_row = True
        while written_row:
            element = ws.cell(column=1, row=row).value
            if element == None:
                written_row = False
            else:
                row +=1
        avg_speed = folder + data_master[3] + name_sheet + 'K' + '{}'.format(row)
        row = row + 1
        avg_ang_speed = folder + data_master[3] + name_sheet + 'K' + '{}'.format(row)
        #Save data in masterspreadsheet.
        try:
            wb = openpyxl.load_workbook("datatemp/masterfile4.xlsx")
        except:
            wb = openpyxl.Workbook()
        ws = wb.active
        #Freeze header
        my_cell = ws['A2']
        ws.freeze_panes = my_cell
        #Next empty row search.
        row = 1
        written_row = True
        while written_row:
            element = ws.cell(column=1, row=row).value
            if element == None:
                written_row = False
            else:
                row +=1
        #Save data in empty row.
        ws.cell(column=1, row=row, value=data_master[0])
        ws.cell(column=2, row=row, value=data_master[1])
        ws.cell(column=3, row=row, value=data_master[2])
        ws.cell(column=4, row=row, value= '=INDIRECT(F{})\n'.format(row)).number_format = '0.00'
        ws.cell(column=5, row=row, value= '=INDIRECT(G{})\n'.format(row)).number_format = '0.00'
        ws.cell(column=6, row=row, value=avg_speed)
        ws.cell(column=7, row=row, value=avg_ang_speed)
        ws.cell(column=8, row=row, value="_")
        #Format data.
        for y in range (1, 8):
            my_cell = ws.cell(column=y, row=row)
            if y == 1:
                ws.column_dimensions[my_cell.column].width = 18
            else:
                ws.column_dimensions[my_cell.column].width = 10
            if row % 2 != 0:
                ws.cell(column=y, row=row).fill = cell_formats['skyblue_fill']
            else:
                ws.cell(column=y, row=row).fill = cell_formats['white_fill']
            if y < 6:
                ws.cell(column=y, row=row).alignment = cell_formats['right_al']
        wb.save("datatemp/masterfile4.xlsx")
