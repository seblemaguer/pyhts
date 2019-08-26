#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

    Package which contains the helper to achieve rendering based on WORLD (NOT WORKING YET!)

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 10 October 2016
"""

import os

import logging

import numpy as np
from scipy.interpolate import interp1d
# from scipy.io import wavfile
import pyworld as pw
import soundfile as sf

from multiprocessing import Process, JoinableQueue

from rendering.utils.parameterconversion import ParameterConversion

class WORLDProcess(Process):
    def __init__(self, conf, out_path, preserve, queue):
        Process.__init__(self)
        self.logger = logging.getLogger("WORLDProcess")
        self.conf = conf
        self.out_path = out_path
        self.preserve = preserve
        self.queue = queue

    def run(self):
        while True:
            base = self.queue.get()
            if base is None:
                break

            # Get some information
            samplerate = int(self.conf.SIGNAL['samplerate'])
            frameshift = float(self.conf.SIGNAL['frameshift'])

            # F0
            f0_fname = os.path.join(self.out_path, base + ".f0")
            f0 = np.fromfile(f0_fname, dtype=np.float32)
            f0 = f0.astype(np.float64)
            nb_frames = f0.shape[0]

            # Spectrum
            sp_fname = os.path.join(self.out_path, base + ".sp")
            sp = np.fromfile(sp_fname, dtype=np.float32)
            sp = sp.reshape((nb_frames, int(sp.shape[0]/nb_frames)))
            sp = sp.astype(np.float64)

            # Aperiodicity
            ap_fname = os.path.join(self.out_path, base + ".ap")
            ap = np.fromfile(ap_fname, dtype=np.float32)
            ap = ap.reshape((nb_frames, int(ap.shape[0]/nb_frames)))
            ap = ap.astype(np.float64)

            y = pw.synthesize(f0, sp, ap, samplerate, frameshift);

            # Save the waveform
            wav_fname = os.path.join(self.out_path, base + ".wav")
            sf.write(wav_fname, y, samplerate)

            if not self.preserve:
                os.remove(f0_fname)
                os.remove(ap_fname)
                os.remove(sp_fname)

            self.queue.task_done()


###############################################################################
# Functions
###############################################################################

class WORLDRenderer:
    """Renderer based on STRAIGHT to generate audio signal
    """
    def __init__(self, conf, nb_proc, preserve):
        """Constructor

        :param conf: the configuration object
        :param out_handle: the handle where the standard output of subcommands is dumped
        :param logger: the logger
        :param nb_proc: the number of process to run
        :param preserve: switch to preserve intermediate files or not
        :returns: None
        :rtype:

        """
        self.conf = conf
        self.logger = logging.getLogger("WORLDRenderer")
        self.nb_proc = nb_proc
        self.preserve = preserve

    def world_part(self, in_path, out_path, gen_labfile_base_lst):
        # Convert duration to labels
        q = JoinableQueue()
        processes = []
        for base in range(self.nb_proc):
            t = WORLDProcess(self.conf, out_path, self.preserve, q)
            t.start()
            processes.append(t)

        for base in gen_labfile_base_lst:
            base = base.strip()
            base = os.path.splitext(base)[0]
            q.put(base)


        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(processes)):
            q.put(None)

        for t in processes:
            t.join()


    def parameter_conversion(self, in_path, out_path, gen_labfile_base_lst):
        """Convert acoustic parameters to STRAIGHT compatible parameters

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """

        # Convert duration to labels
        q = JoinableQueue()
        processs = []
        for base in range(self.nb_proc):
            t = ParameterConversion(self.conf, out_path, self.preserve, q)
            t.start()
            processs.append(t)

        for base in gen_labfile_base_lst:
            base = base.strip()
            base = os.path.splitext(base)[0]
            q.put(base)


        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(processs)):
            q.put(None)

        for t in processs:
            t.join()

    def render(self, in_path, out_path, gen_labfile_base_lst):
        """Rendering

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """
        self.logger.info("Parameter conversion (could be quite long)")
        self.parameter_conversion(in_path, out_path, gen_labfile_base_lst)

        self.logger.info("Audio rendering (could be quite long)")
        self.world_part(in_path, out_path, gen_labfile_base_lst)
