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
class STRAIGHTGeneration: #(GenerationInterface):

    def __init__(self, conf, out_handle):
        self.conf = conf
        self.out_handle = out_handle


    def generate(self, _out_path, gen_labfile_base_lst):
        """
        """
        # Generate STRAIGHT script
        with open(self.conf.STRAIGHT_SCRIPT, 'w') as f:
            # Header
            f.write("path(path, '%s');\n" % self.conf.STRAIGHT_PATH)
            f.write("prm.spectralUpdateInterval = %f;\n" % self.conf.SIGNAL['frameshift'])
            f.write("prm.levelNormalizationIndicator = 0;\n\n")

            # Read STRAIGHT params
            for base in gen_labfile_base_lst:
                f.write("fid_sp = fopen('%s/%s.sp', 'r', 'ieee-le');\n" % (_out_path, base))
                f.write("fid_ap = fopen('%s/%s.ap', 'r', 'ieee-le');\n" % (_out_path, base))
                f.write("fid_f0 = fopen('%s/%s.f0', 'r', 'ieee-le');\n" % (_out_path, base))

                nb_frames = os.path.getsize('%s/%s.f0' % (_out_path, base)) / 4
                f.write("sp = fread(fid_sp, [%d %d], 'float');\n" % (1025, nb_frames))
                f.write("ap = fread(fid_ap, [%d %d], 'float');\n" % (1025, nb_frames))
                f.write("f0 = fread(fid_f0, [%d %d], 'float');\n" % (1, nb_frames))

                f.write("fclose(fid_sp);\n")
                f.write("fclose(fid_ap);\n")
                f.write("fclose(fid_f0);\n")

                # Spectrum normalization    # FIXME (why ?) => not compatible with our corpus podalydes
                f.write("sp = sp * %f;\n" % (1024.0 / (2200.0 * 32768.0)))

                # Synthesis process part 2
                f.write("[sy] = exstraightsynth(f0, sp, ap, %d, prm);\n" % self.conf.SIGNAL["samplerate"])
                f.write("audiowrite('%s/%s.wav', sy, %d);\n" % (_out_path, base, self.conf.SIGNAL["samplerate"]))

            # Ending
            f.write("quit;\n")

        # Synthesis!
        cmd = '%s -nojvm -nosplash -nodisplay < %s' % (self.conf.MATLAB, self.conf.STRAIGHT_SCRIPT)
        subprocess.call(cmd.split(), stdout=self.out_handle)

        # Clean  [TODO: do with options]
        os.remove(self.conf.STRAIGHT_SCRIPT)
        for base in gen_labfile_base_lst:
            os.remove('%s/%s.sp' % (_out_path, base))
            os.remove('%s/%s.ap' % (_out_path, base))
            os.remove('%s/%s.f0' % (_out_path, base))
