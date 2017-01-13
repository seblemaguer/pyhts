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

from rendering.utils.parameterconversion import ParameterConversion


class WORLDThread(Thread):
    def __init__(self, conf, out_path, out_handle, logger, preserve, queue):
        Thread.__init__(self)
        self.logger = logger
        self.out_handle = out_handle
        self.conf = conf
        self.out_path = out_path
        self.preserve = preserve
        self.queue = queue

    def run(self):
        while True:
            base = self.queue.get()
            if base is None:
                break

            samplerate = str(self.conf.SIGNAL['samplerate'])
            frameshift = str(self.conf.SIGNAL['frameshift'])
            wav_fname = os.path.join(self.out_path, base + ".wav")

            # First convert float to double
            f0_fname = os.path.join(self.out_path, base + ".f0")
            sp_fname = os.path.join(self.out_path, base + ".sp")
            ap_fname = os.path.join(self.out_path, base + ".ap")

            df0_fname = os.path.join(self.out_path, base + ".df0")
            dsp_fname = os.path.join(self.out_path, base + ".dsp")
            dap_fname = os.path.join(self.out_path, base + ".dap")

            with open(df0_fname, "w") as f:
                cmd = ["x2x", "+fd", f0_fname]
                subprocess.call(cmd, stdout=f)

            with open(dsp_fname, "w") as f:
                cmd = ["bash" , "-c", "cat " + sp_fname + " | sopr -d 32768.0 -P  | x2x +fd" ]
                subprocess.call(cmd, stdout=f)

            with open(dap_fname, "w") as f:
                cmd = ["bash" , "-c", "cat " + ap_fname + " | sopr -d 32768.0 -P  | sopr -d 1500 | sopr -m 1200 | x2x +fd" ]
                subprocess.call(cmd, stdout=f)

            cmd = ["world_synthesis", "-s", samplerate, "-f", frameshift, df0_fname, dsp_fname, dap_fname, wav_fname]
            subprocess.call(cmd, stdout=self.out_handle)

            if not self.preserve:
                os.remove(f0_fname)
                os.remove(ap_fname)
                os.remove(sp_fname)
                os.remove(df0_fname)
                os.remove(dap_fname)
                os.remove(dsp_fname)

            self.queue.task_done()

###############################################################################
# Functions
###############################################################################
class WORLDRenderer:

    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve

    def world_part(self, out_path, gen_labfile_base_lst):
        # Convert duration to labels
        q = queue.Queue()
        threads = []
        for base in range(self.nb_proc):
            t = WORLDThread(self.conf, out_path, self.out_handle, self.logger, self.preserve, queue)
            t.start()
            threads.append(t)

        for base in gen_labfile_base_lst:
            base = base.strip()
            base = os.path.splitext(os.path.basename(base))[0]
            q.put(base)


        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(threads)):
            q.put(None)

        for t in threads:
            t.join()



    def parameter_conversion(self, out_path, gen_labfile_base_lst):
        """
        Convert parameter to WORLD params
        """
        # Convert duration to labels
        q = queue.Queue()
        threads = []
        for base in range(self.nb_proc):
            t = ParameterConversion(self.conf, out_path, self.logger, self.preserve, q)
            t.start()
            threads.append(t)

        for base in gen_labfile_base_lst:
            base = base.strip()
            base = os.path.splitext(os.path.basename(base))[0]
            q.put(base)


        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(threads)):
            q.put(None)

        for t in threads:
            t.join()


    def render(self, out_path, gen_labfile_base_lst):
        self.logger.info("Parameter conversion (could be quite long)")
        self.parameter_conversion(out_path, gen_labfile_base_lst)

        self.logger.info("Audio rendering (could be quite long)")
        self.world_part(out_path, gen_labfile_base_lst)
