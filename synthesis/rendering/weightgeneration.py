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

import numpy as np

from rendering.weightutils import *

###############################################################################
# Functions
###############################################################################
class WEIGHTGeneration:
    def __init__(self, conf, out_handle, logger, is_parallel, preserve):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.is_parallel = is_parallel
        self.preserve = preserve

    def generateWeightJSON(self, out_path, gen_labfile_base_lst):
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = WeightsToJSON(self.conf, out_path, base, self.logger)
            thread.start()

            if not self.is_parallel:
                thread.join()
            else:
                list_threads.append(thread)

        if self.is_parallel:
            for thread in list_threads:
                thread.join()



    def generateEMAFromWeights(self, out_path, gen_labfile_base_lst):
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = WeightsToEMA(self.conf, out_path, base, self.logger)
            thread.start()

            if not self.is_parallel:
                thread.join()
            else:
                list_threads.append(thread)

        if self.is_parallel:
            for thread in list_threads:
                thread.join()

    # def ema2json(self, out_path, gen_labfile_base_lst):
    #     """
    #     Convert parameter to EMA to JSON
    #     """
    #     list_threads = []
    #     for base in gen_labfile_base_lst:
    #         thread = EMAToJSON(self.conf, out_path, base, self.logger)
    #         thread.start()

    #         if not self.is_parallel:
    #             thread.join()
    #         else:
    #             list_threads.append(thread)

    #     if self.is_parallel:
    #         for thread in list_threads:
    #             thread.join()

    def render(self, out_path, gen_labfile_base_lst):
        self.logger.info("Generate Weights json file")
        self.generateWeightJSON(out_path, gen_labfile_base_lst)

        self.logger.info("Generate EMA from Weights")
        self.generateEMAFromWeights(out_path, gen_labfile_base_lst)

        # self.logger.info("EMA binary to JSON")
        # self.ema2json(out_path, gen_labfile_base_lst)
