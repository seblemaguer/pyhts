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

###############################################################################
# Functions
###############################################################################
class STRAIGHTRenderer:

    def __init__(self, conf, out_handle, logger, is_parallel, preserve):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.is_parallel = is_parallel
        self.preserve = preserve
        self.MATLAB="matlab"

    def straight_part(self, out_path, gen_labfile_base_lst):
        """
        """
        # Generate STRAIGHT script
        with open(self.conf.STRAIGHT_SCRIPT, 'w') as f:
            # Header
            f.write("path(path, '%s');\n" % self.conf.STRAIGHT_PATH)
            f.write("prm.spectralUpdateInterval = %f;\n" % self.conf.SIGNAL['frameshift'])
            f.write("prm.levelNormalizationIndicator = 0;\n\n")

            # Now some parameters
            f.write("out_path = '%s';\n" % out_path)
            f.write("fft_len = %d;\n" % 1025) # FIXME: hardcoded
            f.write("samplerate = %d;\n" % self.conf.SIGNAL["samplerate"])
            f.write("basenames = {};\n")
            for i in range(1, len(gen_labfile_base_lst)+1):
                f.write("basenames{%d} = '%s';\n" % (i, gen_labfile_base_lst[i-1]))
            f.write("\n")

            f.write("nb_frames = [];\n")
            for i in range(1, len(gen_labfile_base_lst)+1):
                base = gen_labfile_base_lst[i-1]
                nb_frames = os.path.getsize('%s/%s.f0' % (out_path, base)) / 4
                f.write("nb_frames(%d) = %d;\n" % (i, nb_frames))
            f.write("\n")

            # Read STRAIGHT params
            nb_elts = len(gen_labfile_base_lst)
            if (self.is_parallel):
                f.write("parfor i=1:%d\n" % nb_elts)
            else:
                f.write("for i=1:%d\n" % nb_elts)


            f.write("\ttry\n")
            f.write("\t\tfid_sp = fopen(sprintf('%s/%s.sp', out_path, basenames{i}), 'r', 'ieee-le');\n")
            f.write("\t\tfid_ap = fopen(sprintf('%s/%s.ap', out_path, basenames{i}), 'r', 'ieee-le');\n")
            f.write("\t\tfid_f0 = fopen(sprintf('%s/%s.f0', out_path, basenames{i}), 'r', 'ieee-le');\n")

            f.write("\t\tsp = fread(fid_sp, [fft_len nb_frames(i)], 'float');\n")
            f.write("\t\tap = fread(fid_ap, [fft_len nb_frames(i)], 'float');\n")
            f.write("\t\tf0 = fread(fid_f0, [1 nb_frames(i)], 'float');\n")

            f.write("\t\tfclose(fid_sp);\n")
            f.write("\t\tfclose(fid_ap);\n")
            f.write("\t\tfclose(fid_f0);\n")

            # Spectrum normalization    # FIXME (why ?) => not compatible with our corpus podalydes
            f.write("\t\tsp = sp * %f;\n" % (1024.0 / (2200.0 * 32768.0)))

            # Synthesis process part 2
            f.write("\t\t[sy] = exstraightsynth(f0, sp, ap, samplerate, prm);\n")
            f.write("\t\taudiowrite(sprintf('%s/%s.wav', out_path, basenames{i}), sy, samplerate);\n")

            f.write("\tcatch me\n")
            f.write("\t\twarning(sprintf('cannot render %s: %s', basenames{i}, me.message));\n")
            f.write("\tend;\n")
            f.write("end;\n")

            # Ending
            f.write("quit;\n")

        # Synthesis!
        cmd = '%s -nojvm -nosplash -nodisplay < %s' % (self.MATLAB, self.conf.STRAIGHT_SCRIPT)
        subprocess.call(cmd.split(), stdout=self.out_handle)

        if not self.preserve:
            os.remove(self.conf.STRAIGHT_SCRIPT)
            for base in gen_labfile_base_lst:
                os.remove('%s/%s.sp' % (out_path, base))
                os.remove('%s/%s.ap' % (out_path, base))
                os.remove('%s/%s.f0' % (out_path, base))



    def parameter_conversion(self, out_path, gen_labfile_base_lst):
        """
        Convert parameter to STRAIGHT params
        """
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = ParameterConversion(self.conf, out_path, base, self.logger, self.preserve)
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
        self.straight_part(out_path, gen_labfile_base_lst)
