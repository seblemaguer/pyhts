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

from shutil import copyfile # For copying files

LEVEL = [logging.WARNING, logging.INFO, logging.DEBUG]

###############################################################################
# Functions
###############################################################################
class STRAIGHTGeneration:

    def __init__(self, conf, out_handle, is_parallel):
        self.conf = conf
        self.out_handle = out_handle
        self.is_parallel = is_parallel


    def generate(self, _out_path, gen_labfile_base_lst):
        """
        """
        # Generate STRAIGHT script
        with open(self.conf.STRAIGHT_SCRIPT, 'w') as f:
            # Header
            f.write("path(path, '%s');\n" % self.conf.STRAIGHT_PATH)
            f.write("prm.spectralUpdateInterval = %f;\n" % self.conf.SIGNAL['frameshift'])
            f.write("prm.levelNormalizationIndicator = 0;\n\n")

            # Now some parameters
            f.write("out_path = '%s';\n" % _out_path)
            f.write("fft_len = %d;\n" % 1025) # FIXME: hardcoded
            f.write("samplerate = %d;\n" % self.conf.SIGNAL["samplerate"])
            f.write("basenames = {};")
            for i in range(1, len(gen_labfile_base_lst)+1):
                f.write("basenames{%d} = '%s';\n" % (i, gen_labfile_base_lst[i-1]))
            f.write("\n")

            f.write("nb_frames = [];\n")
            for i in range(1, len(gen_labfile_base_lst)+1):
                base = gen_labfile_base_lst[i-1]
                nb_frames = os.path.getsize('%s/%s.f0' % (_out_path, base)) / 4
                f.write("nb_frames(%d) = %d;\n" % (i, nb_frames))
            f.write("\n")

            # Read STRAIGHT params
            nb_elts = len(gen_labfile_base_lst)
            if (self.is_parallel):
                f.write("parfor i=1:%d\n" % nb_elts)
            else:
                f.write("for i=1:%d\n" % nb_elts)

            f.write("\tfid_sp = fopen(sprintf('%s/%s.sp', out_path, basenames{i}), 'r', 'ieee-le');\n")
            f.write("\tfid_ap = fopen(sprintf('%s/%s.ap', out_path, basenames{i}), 'r', 'ieee-le');\n")
            f.write("\tfid_f0 = fopen(sprintf('%s/%s.f0', out_path, basenames{i}), 'r', 'ieee-le');\n")

            f.write("\tsp = fread(fid_sp, [fft_len nb_frames(i)], 'float');\n")
            f.write("\tap = fread(fid_ap, [fft_len nb_frames(i)], 'float');\n")
            f.write("\tf0 = fread(fid_f0, [1 nb_frames(i)], 'float');\n")

            f.write("\tfclose(fid_sp);\n")
            f.write("\tfclose(fid_ap);\n")
            f.write("\tfclose(fid_f0);\n")

            # Spectrum normalization    # FIXME (why ?) => not compatible with our corpus podalydes
            f.write("\tsp = sp * %f;\n" % (1024.0 / (2200.0 * 32768.0)))

            # Synthesis process part 2
            f.write("\t[sy] = exstraightsynth(f0, sp, ap, samplerate, prm);\n")
            f.write("\taudiowrite(sprintf('%s/%s.wav', out_path, basenames{i}), sy, samplerate);\n")
            f.write("end;\n")

            # Ending
            f.write("quit;\n")

        # Synthesis!
        cmd = '%s -nojvm -nosplash -nodisplay < %s' % (self.conf.MATLAB, self.conf.STRAIGHT_SCRIPT)
        subprocess.call(cmd.split(), stdout=self.out_handle)

        # Clean  [TODO: do with options]
        # os.remove(self.conf.STRAIGHT_SCRIPT)
        for base in gen_labfile_base_lst:
            os.remove('%s/%s.sp' % (_out_path, base))
            os.remove('%s/%s.ap' % (_out_path, base))
            os.remove('%s/%s.f0' % (_out_path, base))
