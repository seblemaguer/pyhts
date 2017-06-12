#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION
    Package for acoustic parameter rendering helpers

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


from multiprocessing import Process, Queue, JoinableQueue


class ParameterConversion(Process):
    """Helper to convert acoustic parameters to STRAIGHT compatible parameters
    """

    def __init__(self, conf, out_path, logger, preserve, queue):
        """Constructor

        :param conf: the configuration object
        :param out_path: the output directory
        :param logger: the logger
        :param preserve: switch to preserve or not intermediate files
        :param queue: the queue of utterance to deal with
        :returns: None
        :rtype:

        """
        Process.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.preserve = preserve

        self.SOPR = "sopr"
        self.MGC2SP = "mgc2sp"

        self.queue = queue

    def run(self):
        """Achieve the conversion

        :returns: None
        :rtype:

        """

        while True:
            base = self.queue.get()
            if base is None:
                break

            # bap => aperiodicity
            for cur_stream in self.conf.STREAMS:
                if cur_stream["kind"] == "lf0":
                    # lf0 => f0
                    cmd = '%s -magic -1.0E+10 -EXP -MAGIC 0.0 %s/%s.lf0' % \
                      (self.SOPR, self.out_path, base)
                    with open('%s/%s.f0' % (self.out_path, base), 'w') as f:
                        subprocess.call(cmd.split(), stdout=f)
                elif cur_stream["kind"] == "bap":
                    cmd = '%s -a %f -g 0 -m %d -l 2048 -o 0 %s/%s.bap' % \
                      (self.MGC2SP, self.conf.FREQWARPING, cur_stream["order"], self.out_path, base)
                    with open('%s/%s.ap' % (self.out_path, base), 'w') as f:
                        subprocess.call(cmd.split(), stdout=f)
                elif cur_stream["kind"] == "mgc":
                    cmd = '%s -a %f -g %f -m %d -l 2048 -o 2 %s/%s.mgc' % \
                      (self.MGC2SP, self.conf.FREQWARPING, cur_stream['parameters']['gamma'], cur_stream["order"], self.out_path, base)
                    with open('%s/%s.sp' % (self.out_path, base), 'w') as f:
                        subprocess.call(cmd.split(), stdout=f)

            if not self.preserve:
                for cur_stream in self.conf.STREAMS:
                    os.remove('%s/%s.%s' % (self.out_path, base, cur_stream["kind"]))
                os.remove('%s/%s.dur' % (self.out_path, base))


            self.queue.task_done()
# parameterconversion.py ends here
