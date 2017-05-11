#!/usr/bin/env python
"""
Auxiliary program for saving poses in spreadsheet and text file.
"""
# Standard libraries
import numpy as np
import sys

#Excel read/write library
from openpyxl import load_workbook
from openpyxl import Workbook


def data2spreadsheet(data, filename_spreadsheet):
    """
    Receives poses and time, and saves them in a spreadsheet.

    :param data: contains data to save in spreadsheet.
    :param filename_spreadsheet: name of spreadsheet where the data
     will be saved.
    """
    try:
        wb = load_workbook(filename_spreadsheet)
    except:
        wb = Workbook()
    ws = wb.active
    rows = data.shape[0]
    cols = data.shape[1]
    for x in range(0, rows):
        for y in range(0, cols):
            try:
                element = float(data[x,y])
                element = float("{0:.2f}".format(element))
            except:
                element = data[x,y]
            ws.cell(column=y+1, row=x+1, value=element)
    wb.save(filename_spreadsheet)

def data2textfile(data, filename_textfile):
    """
    Receives poses and time, and saves them in a textfile.

    :param data: contains data to save in a textfile.
    :param filename_textfile: name of textfile where the data will
     be saved.
    """
    text = ''
    with open(filename_textfile, 'a') as outfile:
        rows = data.shape[0]
        cols = data.shape[1]
        for x in range(0, rows):
            for y in range(0, cols):
                try:
                    element = float(data[x,y])
                    element = float("{0:.2f}".format(element))
                except:
                    element=data[x,y]
                text = text + "{} \t\t".format(element)
            text = text + "\n"
        outfile.write(text)
