#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

    Package contains the renderer to produced STRAIGHT-based audio signal and the EMA results

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

from rendering.emarenderer import *
from rendering.straightrenderer import *

###############################################################################
# Functions
###############################################################################
class STRAIGHTEMARenderer(STRAIGHTRenderer, EMARenderer):
    """Composite renderer to produce STRAIGHT audio signal and EMA related results
    """
    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
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
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve
        self.MATLAB="matlab"

    def render(self, out_path, gen_labfile_base_lst):
        """Rendering

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """
        STRAIGHTRenderer.render(self, out_path, gen_labfile_base_lst)
        EMARenderer.render(self, out_path, gen_labfile_base_lst)
