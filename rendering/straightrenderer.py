#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

    Package which contains the STRAIGHT audio rendering

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 10 October 2016
"""

import os
import logging

from multiprocessing import JoinableQueue

from rendering.utils.parameterconversion import ParameterConversion

from utils import run_shell_command

###############################################################################
# Functions
###############################################################################
class STRAIGHTRenderer:
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
        self.logger = logging.getLogger("STRAIGHTRenderer")
        self.nb_proc = nb_proc
        self.preserve = preserve
        self.MATLAB="matlab"

    def straight_part(self, in_path, out_path, gen_labfile_base_lst):
        """Achieving the straight generation

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

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
                base = gen_labfile_base_lst[i-1]
                f.write("basenames{%d} = '%s';\n" % (i, base))
            f.write("\n")

            f.write("nb_frames = [];\n")
            for i in range(1, len(gen_labfile_base_lst)+1):
                base = gen_labfile_base_lst[i-1]
                nb_frames = os.path.getsize('%s/%s.f0' % (out_path, base)) / 4
                f.write("nb_frames(%d) = %d;\n" % (i, nb_frames))
            f.write("\n")

            # Read STRAIGHT params
            nb_elts = len(gen_labfile_base_lst)
            if self.nb_proc != 1:
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
        run_shell_command(cmd, self.logger)

        if not self.preserve:
            os.remove(self.conf.STRAIGHT_SCRIPT)
            # for base in gen_labfile_base_lst:
                # os.remove('%s/%s.sp' % (out_path, base))
                # os.remove('%s/%s.ap' % (out_path, base))
                # os.remove('%s/%s.f0' % (out_path, base))



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
        self.straight_part(in_path, out_path, gen_labfile_base_lst)
