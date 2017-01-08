#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 10 October 2016
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

from rendering.parameterconversion import ParameterConversion
from rendering.emautils import *

CHANNELS =  ["T3", "T2", "T1", "ref", "jaw", "upperlip", "lowerlip"]

###############################################################################
# Functions
###############################################################################
class STRAIGHTEMARenderer(STRAIGHTRenderer, EMARenderer):

    def __init__(self, conf, out_handle, logger, is_parallel, preserve):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.is_parallel = is_parallel
        self.preserve = preserve
        self.MATLAB="matlab"

    def debug_part(self, out_path, gen_labfile_base_lst):
        """
        Generate PLY debug information
        """
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = JSONtoPLY(self.conf, out_path, base, self.logger)
            thread.start()

            if not self.is_parallel:
                thread.join()
            else:
                list_threads.append(thread)

        if self.is_parallel:
            for thread in list_threads:
                thread.join()

    def render(self, out_path, gen_labfile_base_lst):
        STRAIGHTRenderer.render(self, out_path, gen_labfile_base_lst)
        EMARenderer.render(self, out_path, gen_labfile_base_lst)
