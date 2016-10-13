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


###############################################################################
# Utils
###############################################################################
class ParameterConversion(Thread):
    def __init__(self, conf, _out_path, base):
        Thread.__init__(self)
        self.conf = conf
        self._out_path = _out_path
        self.base = base

    def run(self):
        # bap => aperiodicity
        for cur_stream in self.conf.STREAMS:
            if cur_stream["kind"] == "lf0":
                # lf0 => f0
                cmd = '%s -magic -1.0E+10 -EXP -MAGIC 0.0 %s/%s.lf0' % \
                  (self.conf.SOPR, self._out_path, self.base)
                with open('%s/%s.f0' % (self._out_path, self.base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)
            elif cur_stream["kind"] == "bap":
                cmd = '%s -a %f -g 0 -m %d -l 2048 -o 0 %s/%s.bap' % \
                  (self.conf.MGC2SP, self.conf.FREQWARPING, cur_stream["order"], self._out_path, self.base)
                with open('%s/%s.ap' % (self._out_path, self.base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)
            elif cur_stream["kind"] == "mgc":
                # mgc => spectrum TODO
                cmd = '%s -a %f -g %f -m %d -l 2048 -o 2 %s/%s.mgc' % \
                  (self.conf.MGC2SP, self.conf.FREQWARPING, cur_stream['parameters']['gamma'], cur_stream["order"], self._out_path, self.base)
                with open('%s/%s.sp' % (self._out_path, self.base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)

        # Clean [TODO: do with options]
        os.remove('%s/%s.lf0' % (self._out_path, self.base))
        os.remove('%s/%s.mgc' % (self._out_path, self.base))
        os.remove('%s/%s.bap' % (self._out_path, self.base))
        os.remove('%s/%s.dur' % (self._out_path, self.base))

###############################################################################
# Functions
###############################################################################
class STRAIGHTGeneration:

    def __init__(self, conf, out_handle, is_parallel):
        self.conf = conf
        self.out_handle = out_handle
        self.is_parallel = is_parallel

    def straight_part(self, _out_path, gen_labfile_lst):
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
        cmd = '%s -nojvm -nosplash -nodisplay < %s' % (self.conf.MATLAB, self.conf.STRAIGHT_SCRIPT)
        subprocess.call(cmd.split(), stdout=self.out_handle)

        # Clean  [TODO: do with options]
        # os.remove(self.conf.STRAIGHT_SCRIPT)
        for base in gen_labfile_base_lst:
            os.remove('%s/%s.sp' % (_out_path, base))
            os.remove('%s/%s.ap' % (_out_path, base))
            os.remove('%s/%s.f0' % (_out_path, base))



    def parameter_conversion(self, _out_path, gen_labfile_base_lst, parallel=False):
        """
        Convert parameter to STRAIGHT params
        """
        list_threads = []
        for base in gen_labfile_base_lst:
            thread = ParameterConversion(self.conf, _out_path, base)
            thread.start()

            if not parallel:
                thread.join()
            else:
                list_threads.append(thread)

        if parallel:
            for thread in list_threads:
                thread.join()

    def generate(self, _out_path, gen_labfile_base_lst):
        self.parameter_conversion(out_path, gen_labfile_base_lst, self.is_parallel)

        self.straight_part(_out_path, gen_labfile_lst)
