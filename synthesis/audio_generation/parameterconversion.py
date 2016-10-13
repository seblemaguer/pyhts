#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 13 October 2016
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


class ParameterConversion(Thread):
    def __init__(self, conf, out_path, base, logger):
        Thread.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.base = base

        self.SOPR = "sopr"
        self.MGC2SP = "mgc2sp"

    def run(self):
        # bap => aperiodicity
        for cur_stream in self.conf.STREAMS:
            if cur_stream["kind"] == "lf0":
                # lf0 => f0
                cmd = '%s -magic -1.0E+10 -EXP -MAGIC 0.0 %s/%s.lf0' % \
                  (self.SOPR, self.out_path, self.base)
                with open('%s/%s.f0' % (self.out_path, self.base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)
            elif cur_stream["kind"] == "bap":
                cmd = '%s -a %f -g 0 -m %d -l 2048 -o 0 %s/%s.bap' % \
                  (self.MGC2SP, self.conf.FREQWARPING, cur_stream["order"], self.out_path, self.base)
                with open('%s/%s.ap' % (self.out_path, self.base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)
            elif cur_stream["kind"] == "mgc":
                # mgc => spectrum TODO
                cmd = '%s -a %f -g %f -m %d -l 2048 -o 2 %s/%s.mgc' % \
                  (self.MGC2SP, self.conf.FREQWARPING, cur_stream['parameters']['gamma'], cur_stream["order"], self.out_path, self.base)
                with open('%s/%s.sp' % (self.out_path, self.base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)

        # Clean [TODO: do with options]
        os.remove('%s/%s.lf0' % (self.out_path, self.base))
        os.remove('%s/%s.mgc' % (self.out_path, self.base))
        os.remove('%s/%s.bap' % (self.out_path, self.base))
        os.remove('%s/%s.dur' % (self.out_path, self.base))

# parameterconversion.py ends here
