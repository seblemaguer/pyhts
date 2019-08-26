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
import subprocess       # Shell command calling
import logging
from multiprocessing import Process

import utils

class ParameterConversion(Process):
    """Helper to convert acoustic parameters to STRAIGHT compatible parameters
    """

    def __init__(self, conf, out_path, preserve, queue, keep_bap=False):
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
        self.logger = logging.getLogger("ParameterConversion")
        self.conf = conf
        self.out_path = out_path
        self.preserve = preserve

        self.SOPR = "sopr"
        self.MGC2SP = "mgc2sp"

        self.queue = queue
        self.keep_bap = keep_bap

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
                    f0_fn = '%s/%s.f0' % (self.out_path, base)
                    cmd = '%s -magic -1.0E+10 -EXP -MAGIC 0.0 %s/%s.lf0 > %s' % \
                      (self.SOPR, self.out_path, base, f0_fn)

                    utils.run_shell_command(cmd, self.logger)
                elif cur_stream["kind"] == "bap":
                    ap_fn = '%s/%s.ap' % (self.out_path, base)

                    if not self.keep_bap:
                        cmd = '%s -a %f -g 0 -m %d -l 2048 -o 2 %s/%s.bap | %s -d 32768.0 -P > %s' % \
                              (self.MGC2SP, self.conf.FREQWARPING, cur_stream["order"],
                               self.out_path, base, self.SOPR, ap_fn)
                    else:
                        cmd = 'cat %s/%s.bap > %s' % (self.out_path, base, ap_fn)

                    utils.run_shell_command(cmd, self.logger)
                elif cur_stream["kind"] == "mgc":
                    sp_fn = '%s/%s.sp' % (self.out_path, base)

                    cmd = '%s -a %f -g %f -m %d -l 2048 -o 2 %s/%s.mgc | %s -d 32768.0 -P > %s' % \
                      (self.MGC2SP, self.conf.FREQWARPING, cur_stream['parameters']['gamma'], cur_stream["order"],
                       self.out_path, base, self.SOPR, sp_fn)

                    utils.run_shell_command(cmd, self.logger)

            if not self.preserve:
                try:
                    for cur_stream in self.conf.STREAMS:
                        os.remove('%s/%s.%s' % (self.out_path, base, cur_stream["kind"]))
                    os.remove('%s/%s.dur' % (self.out_path, base))
                except FileNotFoundError:
                    pass

            self.queue.task_done()
# parameterconversion.py ends here
