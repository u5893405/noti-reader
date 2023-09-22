#!/bin/bash

# Get the directory of the currently executing script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate the virtual environment
source "$DIR/noti_reader_env/bin/activate"

# Log output and errors to files and also display them
exec > >(tee -a "$DIR/logs/output.log")
exec 2> >(tee -a "$DIR/logs/error.log" >&2)

# Dump environment variables to a file for debugging
env > "$DIR/logs/env.log"

# Run your Python script with a relative path to the Python binary
"$DIR/noti_reader_env/bin/python3" "$DIR/noti_reader_GUI.py"
