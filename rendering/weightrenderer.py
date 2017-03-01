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

import queue

from threading import Thread

from shutil import copyfile # For copying files
import shutil

import numpy as np

from rendering.utils.weights import *
from rendering.utils.ema import *

###############################################################################
# Functions
###############################################################################
class WEIGHTRenderer:
    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve

    def generateWeightJSON(self, out_path, gen_labfile_base_lst):

        # Convert duration to labels
        q = queue.Queue()
        threads = []
        for base in range(self.nb_proc):
            t = WeightsToJSON(self.conf, out_path, self.logger, q)
            t.start()
            threads.append(t)

        for base in gen_labfile_base_lst:
            q.put(base)


        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(threads)):
            q.put(None)

        for t in threads:
            t.join()


    def generateEMAFromWeights(self, out_path, gen_labfile_base_lst):

        # Convert duration to labels
        q = queue.Queue()
        threads = []
        for base in range(self.nb_proc):
            t = WeightsToEMA(self.conf, out_path, self.logger, q)
            t.start()
            threads.append(t)

        for base in gen_labfile_base_lst:
            q.put(base)

        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(threads)):
            q.put(None)

        for t in threads:
            t.join()



    def convertEMAJSONToBinary(self, out_path, gen_labfile_base_lst):

        # Convert duration to labels
        q = queue.Queue()
        threads = []
        for base in range(self.nb_proc):
            t = JSONToEMA(self.conf, out_path, self.logger, q)
            t.start()
            threads.append(t)


        for base in gen_labfile_base_lst:
            q.put(base)

        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(threads)):
            q.put(None)

        for t in threads:
            t.join()

    # FIXME: not quite sure I can parallelize this one
    def videoRendering(self, gen_labfile_base_lst, model, out_path):
        framerate = 25
        for base in gen_labfile_base_lst:
            self.logger.info("\trendering video for %s" % base)
            tmp_output_dir = "%s/%s-%s" % (self.conf.TMP_PATH, base, os.getpid())
            os.mkdir(tmp_output_dir)

            # set environment variables
            os.putenv('input_file', "%s/%s_weight.json" % (out_path, base))
            os.putenv('model_file', model)
            os.putenv('output_file', tmp_output_dir + "/output")

            # start blender, open empty scene, and process core script (FIXME: path for the blender script)
            os.system('blender rendering/utils/empty.blend --python rendering/utils/blender-rendering.py -b >/dev/null 2> /dev/null')

            # Render the video (FIXME: downsample or something like that)
            self.logger.debug("ffmpeg -f %d -i %s/output_%%07d.png -c:v libx264 -r %d -pix_fmt yuv420p %s/%s.mp4" % (framerate, tmp_output_dir, framerate, out_path, base))
            os.system("ffmpeg -framerate %d -i %s/output_%%07d.png -c:v libx264 -r %d -pix_fmt yuv420p %s/%s.mp4 >/dev/null 2>/dev/null" % (framerate, tmp_output_dir, framerate, out_path, base))

            shutil.rmtree(tmp_output_dir)

    def render(self, out_path, gen_labfile_base_lst):
        self.logger.info("Generate Weights json file")
        self.generateWeightJSON(out_path, gen_labfile_base_lst)

        self.logger.info("Generate EMA from weights")
        self.generateEMAFromWeights(out_path, gen_labfile_base_lst)

        self.logger.info("Convert JSON EMA to Binary EMA")
        self.convertEMAJSONToBinary(out_path, gen_labfile_base_lst)

        # self.logger.info("Generate Video")
        # self.videoRendering(gen_labfile_base_lst, "/home/slemaguer/work/expes/current/mngu0_weights_hts2.3/synthesis/build/resources/tongue_model.json", out_path)

        # self.logger.info("EMA binary to JSON")
        # self.ema2json(out_path, gen_labfile_base_lst)
