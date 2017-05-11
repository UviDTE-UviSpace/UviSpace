#!/usr/bin/env python
"""uvirobot package from UviSpace project

This python package has 2 main modules:

* robot: hears to published poses and goals and calculates new paths.
* messenger: receives speed set points and send them to the UGV through
serial ports.
"""

from __future__ import absolute_import, division, print_function

__all__ = ['sim_sensors','saveposes']
