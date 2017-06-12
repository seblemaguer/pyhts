#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION
   Package which provides the classes needed to not achieve any generation.

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

class NONEGenerator:
    """Generator which is not doing anything.

    It is used to desactivate the generation part and go directly to the
    rendering part
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

    def generate(self, out_path, gen_labfile_list_fname, use_gv):
        """Parameter generation method. In this case it doesn't do anything.

        :param out_path: the path where to store the parameters.
        :param gen_labfile_list_fname: the name of the file containing the list of utt. to generate
        :param use_gv: switch to use the variance global
        :returns: None
        :rtype:

        """
        self.logger.info("use of the NONEGenerator")
