#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION
    Package which provides the classes needed to achieve the default HMM generation using HTS

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
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

from generation.utils.composition import *
from generation.utils.configuration import *

class DEFAULTGenerator:
    """Generator which is achieving the default HMGenS parameter generation

    """
    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
        """Constructor

        :param conf: the configuration object
        :param out_handle: the handle to dump the standard output of the command
        :param logger: the logger
        :param nb_proc: the number of processes spawn in parallel
        :param preserve: keep the intermediate files switch
        :returns: None
        :rtype:

        """
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve
        self.configuration_generator = ConfigurationGenerator(conf, logger)

    def composition(self, use_gv):
        """Generate composed files (model files containing the predicted
        node for the labels also not present in the training corpus)

        :param use_gv: switch to activate the composition of the global variance models
        :returns:None
        :rtype:

        """
        # CMP
        thread_cmp = CMPComposition(self.conf,
                                        self.conf.hts_file_pathes["cmp_tree"],
                                        self.conf.hts_file_pathes["cmp_model"],
                                        self.conf.hts_file_pathes["full_list"],
                                        self.logger, self.out_handle)
        thread_cmp.start()
        if self.nb_proc == 1:
            thread_cmp.join()

        # DUR
        thread_dur = DURComposition(self.conf,
                                        self.conf.hts_file_pathes["dur_tree"],
                                        self.conf.hts_file_pathes["dur_model"],
                                        self.conf.hts_file_pathes["full_list"],
                                        self.logger, self.out_handle)
        thread_dur.start()
        if self.nb_proc == 1:
            thread_dur.join()


        # GV
        if use_gv:
            thread_gv = GVComposition(self.conf,
                                          self.conf.hts_file_pathes["gv"],
                                          self.logger, self.out_handle)
            thread_gv.start()
            thread_gv.join()


        if self.nb_proc != 1:
            thread_cmp.join()
            thread_dur.join()



    def generate(self, out_path, gen_labfile_list_fname, use_gv):
        """Parameter generation method.

        :param out_path: the path where to store the parameters.
        :param gen_labfile_list_fname: the name of the file containing the list of utt. to generate
        :param use_gv: switch to use the variance global
        :returns: None
        :rtype:

        """

        # Configuration part
        self.configuration_generator.generateTrainingConfiguration()
        self.configuration_generator.generateSynthesisConfiguration(use_gv)

        # Model part
        self.composition(use_gv)

        # Parameter generation
        self.logger.info("Parameter generation")
        cmd = "%s " % self.conf.HMGenS
        if self.conf.imposed_duration:
            cmd += "-m "

        cmd += '-A -B -C %s -D -T 1 -S %s -t %s -c %d -H %s -N %s -M %s %s %s' % \
          (self.conf.SYNTH_CONFIG, gen_labfile_list_fname,
               self.conf.MODELLING["beam"], int(self.conf.pg_type), self.conf.TMP_CMP_MMF, self.conf.TMP_DUR_MMF,
               out_path, self.conf.TYPE_TIED_LIST_BASE+'_cmp', self.conf.TYPE_TIED_LIST_BASE+'_dur')

        subprocess.call(cmd.split(), stdout=self.out_handle)
