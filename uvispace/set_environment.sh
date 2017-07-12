#!/bin/bash
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

# This statement will raise an error if the file was run, instead of sourced.
# It also redirects the STDOUT and STDERR to /dev/null.
# The null device is a device file that discards all data written to it but
# reports that the write operation succeeded.
$(return >/dev/null 2>&1)
# Print error message.
if ! [ "$?" -eq "0" ];
then
	echo "-------------------------WARNING-------------------------"
    echo "This script has not been sourced."
    echo "Please type on your terminal: 'source set_environment.sh'"
    exit 1
fi

export OLDPYTHONPATH=$PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$parent_path

export UVISPACE_BASE_PORT_POSITION=35000
export UVISPACE_BASE_PORT_SPEED=35010
export UVISPACE_BASE_PORT_GOAL=35020

echo "Exported the environment variables for the uvispace project."
