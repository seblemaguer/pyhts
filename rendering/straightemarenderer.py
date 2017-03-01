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

from rendering.emarenderer import *
from rendering.straightrenderer import *

###############################################################################
# Functions
###############################################################################
class STRAIGHTEMARenderer(STRAIGHTRenderer, EMARenderer):

    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve
        self.MATLAB="matlab"

    def render(self, out_path, gen_labfile_base_lst):
        STRAIGHTRenderer.render(self, out_path, gen_labfile_base_lst)
        EMARenderer.render(self, out_path, gen_labfile_base_lst)
