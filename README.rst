========
UviSpace
========

:Author:
    Department of Electronic Technology,

    University of Vigo

:Version: 1.0.0

The project contains two main packages:

* uvirobot

* uvisensor

=====================
Project documentation
=====================

.. image:: https://readthedocs.org/projects/uvispace/badge/?version=latest
   :target: http://uvispace.readthedocs.io/en/latest/?badge=latest
   :alt: Documentation Status

The oficial documentation about the UviSpace project is hosted at
.. _this website: http://uvispace.readthedocs.io/en/latest/

========
uvirobot
========

The uvirobot package contains all the modules required to control an UGV i.e.: Connect to it via an XBee module, receive position and goal parameters, calculate the path to the goal, establish speed set points, transform the speed value to a valid input to the Arduino board on the UGV and send the values to it.


messenger
---------

The *messenger* module establish a connection with the board. It has been tested with XBee modules, connected to the PC through a serial port. Once the connection is established, the program will wait for speed set points and will send them to the UGV.
   
* To run it, open a new Terminal, set up the environment, and execute the script using the Python interpreter. The execution will listen for speed set points until it is killed:

.. code-block:: bash

   $ cd /<path_to_UviSpace>/uvispace/
   $ source set_environment.sh
   $ python -m uvirobot/messenger.py -r <robot_id>

* Alternatively, execute the *messenger.py* module on an *IPython* session:

.. code-block:: python

   In [1]: cd /<path_to_UviSpace>/uvispace/
          /<path_to_UviSpace>/uvispace
   In [2]: run -m uvirobot.messenger -- -r <robot_id>


controller
----------

The *controller* module listens for new positions of the robot, as well as for destination goals typed by the user.

* To run it, open a new Terminal, set up the environment, and execute the script using the Python interpreter. The execution will keep running until it is killed.

.. code-block:: bash

   $ cd /<path_to_UviSpace>/uvispace/
   $ source set_environment.sh
   $ python -m uvirobot/move_robot.py -r <robot_id>

* Alternatively, execute the *controller.py* module on an *IPython* session:

.. code-block:: python

   In [1]: cd /<path_to_UviSpace>/uvispace/
          /<path_to_UviSpace>/uvispace
   In [2]: run -m uvirobot.move_robot -- -r <robot_id>


=========
uvisensor
=========

The uvisensor package connects via ethernet to external cameras, configures them and acquires images of the iSpace scene so it can calculate the position of the UGVs.

multiplecamera
--------------

* To run it, open a new Terminal, set up the environment, and execute the script using the Python interpreter.

.. code-block:: bash

   $ cd /<path_to_UviSpace>/uvispace/
   $ source set_environment.sh
   $ python -m uvirobot/multiplecamera.py

* Alternatively, execute the *multiplecamera.py* module on an *IPython* session:

.. code-block:: python

   In [1]: cd /<path_to_UviSpace>/uvispace/
          /<path_to_UviSpace>/uvispace
   In [2]: run -m uvisensor.multiplecamera
