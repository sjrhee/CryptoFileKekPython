#!/bin/bash
source /opt/safenet/protecttoolkit7/cpsdk/setvars.sh
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)
python app.py
