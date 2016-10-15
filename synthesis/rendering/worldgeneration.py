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


class WORLDThread(Thread):
    def __init__(self, conf, out_path, base, out_handle, logger):
        Thread.__init__(self)
        self.logger = logger
        self.out_handle = out_handle
        self.conf = conf
        self.out_path = out_path
        self.base = base

    def run(self):
        samplerate = str(self.conf.SIGNAL['samplerate'])
        frameshift = str(self.conf.SIGNAL['frameshift'])
        wav_fname = os.path.join(self.out_path, self.base + ".wav")

        # First convert float to double
        f0_fname = os.path.join(self.out_path, self.base + ".f0")
        sp_fname = os.path.join(self.out_path, self.base + ".sp")
        ap_fname = os.path.join(self.out_path, self.base + ".ap")

        df0_fname = os.path.join(self.out_path, self.base + ".df0")
        dsp_fname = os.path.join(self.out_path, self.base + ".dsp")
        dap_fname = os.path.join(self.out_path, self.base + ".dap")

        with open(df0_fname, "w") as f:
            cmd = ["x2x", "+fd", f0_fname]
            subprocess.call(cmd, stdout=f)

        with open(dsp_fname, "w") as f:
            cmd = ["x2x", "+fd", sp_fname]
            subprocess.call(cmd, stdout=f)

        with open(dap_fname, "w") as f:
            cmd = ["x2x", "+fd", ap_fname]
            subprocess.call(cmd, stdout=f)

        cmd = ["world_synthesis", "-s", samplerate, "-f", frameshift, df0_fname, dsp_fname, dap_fname, wav_fname]
        subprocess.call(cmd, stdout=self.out_handle)

        # os.remove(f0_fname)
        # os.remove(ap_fname)
        # os.remove(sp_fname)


###############################################################################
# Functions
###############################################################################
class WORLDGeneration:

    def __init__(self, conf, out_handle, logger, is_parallel):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.is_parallel = is_parallel
        self.MATLAB="matlab"

    def world_part(self, out_path, gen_labfile_base_lst):
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = WORLDThread(self.conf, out_path, base, self.out_handle, self.logger)
            thread.start()

            if not self.is_parallel:
                thread.join()
            else:
                list_threads.append(thread)

        if self.is_parallel:
            for thread in list_threads:
                thread.join()



    def parameter_conversion(self, out_path, gen_labfile_base_lst):
        """
        Convert parameter to WORLD params
        """
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = ParameterConversion(self.conf, out_path, base, self.logger)
            thread.start()

            if not self.is_parallel:
                thread.join()
            else:
                list_threads.append(thread)

        if self.is_parallel:
            for thread in list_threads:
                thread.join()

    def render(self, out_path, gen_labfile_base_lst):
        self.logger.info("Parameter conversion (could be quite long)")
        self.parameter_conversion(out_path, gen_labfile_base_lst)

        self.logger.info("Audio rendering (could be quite long)")
        self.world_part(out_path, gen_labfile_base_lst)
