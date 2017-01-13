#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
"""

import os
import sys
import traceback
import argparse as ap

import time
import subprocess       # Shell command calling
import re
import logging

from threading import Thread

from shutil import copyfile # For copying files

from generation.utils.composition import *
from generation.utils.configuration import *

###############################################################################
# Functions
###############################################################################
class NONEGenerator:

    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
        """
        Constructor
        """
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve
        self.configuration_generator = ConfigurationGenerator(conf, logger)

    def generate(self, out_path, gen_labfile_list_fname, use_gv):
        self.logger.info("use of the NONEGenerator")
