#!/bin/bash

export PATH=$PATH:/vrac/work/phd/hts-sorted/tutorial_hts/tools/bin/bin/

# python prepare_data/extract_straight.py $PWD/config/example_config.cfg -v
python prepare_data/prepare_data.py $PWD/config/example_config.cfg -v
