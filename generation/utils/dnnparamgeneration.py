#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 12 January 2017
"""

import os
import sys

import time
import subprocess       # Shell command calling
import re
import logging
import shutil

# # Multi process
# from multiprocessing import Process, Queue, JoinableQueue

from threading import Thread
from shutil import copyfile # For copying files

import generation.dnn.DNNDataIO as DNNDataIO
import generation.dnn.DNNDefine as DNNDefine

import tensorflow as tf

class DNNParamGeneration(Thread):
    def __init__(self, user_config, dnn_config, frameshift, out_path, logger, out_handle, preserve, queue):
        Thread.__init__(self)
        self.conf = user_config
        self.dnn_config = dnn_config
        self.frameshift = frameshift
        self.out_path = out_path
        self.out_handle = out_handle
        self.logger = logger
        self.preserve = preserve
        self.queue = queue


    def convertDUR2LAB(self, input_dur_path, output_lab_path):
        result = ""
        with open(input_dur_path) as f:

            total_state = self.conf.nb_emitting_states
            id_state = 1
            t = 0
            for line in f.readlines():
                line = line.strip()
                if id_state <= total_state:
                    if id_state == 1:
                        pass

                    # Retrieve information
                    state_infos = re.search("(.*)\\.state\\[[0-9]*\\].*duration=([0-9]*) .*",line, re.IGNORECASE)
                    label = state_infos.group(1)
                    nb_frames = int(state_infos.group(2))

                    # Compute start and end
                    start = t * self.frameshift
                    end = (t + nb_frames) * self.frameshift

                    # Update output
                    result += "%d %d %s[%d]" % (start, end, label, id_state+1)
                    if id_state == 1:
                        result += " %s" % label
                    result += "\n"

                    # Prepare next state
                    t += nb_frames
                    id_state += 1
                else:
                    id_state = 1

        with open(output_lab_path, "w") as f:
            f.write(result)



    def makeFeature(self, input_lab_path, output_ffi_path):
        config_path = self.conf.project_path + "/DNN/qconf.conf"
        cmd = "perl utils/makefeature.pl %s %d %s | x2x +af > %s" % \
          (config_path, self.frameshift, input_lab_path, output_ffi_path)

        wrapped_cmd = ["bash", "-c", cmd]
        subprocess.call(wrapped_cmd)

    def fillFeedDict(self, data_set, keep_prob, placeholders, batch_size, shuffle=True):
        inputs_pl, outputs_pl, keep_prob_pl = placeholders
        inputs_feed, outputs_feed = data_set.get_pairs(batch_size, shuffle)
        feed_dict = {
            inputs_pl: inputs_feed,
            outputs_pl: outputs_feed,
            keep_prob_pl: keep_prob
        }
        return feed_dict

    def forward(self, config, ffi_path, ffo_path):

        self.logger.debug('Start forwarding')
        self.logger.debug('  Processing %s' % ffi_path)
        forward_data, num_examples = DNNDataIO.read_data_from_file([ffi_path, None], config['num_io_units'])

        total_cost = 0.0
        sess = config["session"]
        inputs = config["inputs"]
        outputs = config["outputs"]
        keep_prob = config["keep_prob"]
        predicted_outputs = config["predicted_outputs"]
        cost_op = config["cost_op"]

        start_time = time.time()
        for j in range(num_examples):
            feed_dict = self.fillFeedDict(
                forward_data, 1.0,
                [inputs, outputs, keep_prob], 1, shuffle=False)

            predicts, value = sess.run(
                [predicted_outputs, cost_op],
                feed_dict=feed_dict)

            total_cost += value

            append = False if j == 0 else True
            DNNDataIO.write_data(ffo_path, predicts, append)

        self.logger.debug('End forwarding')


    def extractParam(self, out_path, base):

        ffo_size = 0
        for map_ffo in self.conf.conf["models"]["ffo"]["streams"]:
            ffo_size += (map_ffo["order"]+1) * len(map_ffo["winfiles"])

        ffo_path = "%s/%s.ffo" % (out_path, base)
        T = int(os.path.getsize(ffo_path) / (ffo_size * 4))
        start = 0
        for map_ffo in self.conf.conf["models"]["ffo"]["streams"]:
            kind = map_ffo["kind"]

            # Extract MEAN from DNN
            order = map_ffo["order"]
            dim = (order+1) * len(map_ffo["winfiles"])

            cmd = "bcp +f -s %d -e %d -l %d %s > %s/%s.%s.mean" % (start, start + dim - 1, ffo_size, ffo_path, out_path, base, kind)
            wrapped_cmd = ["bash", "-c", cmd]
            subprocess.call(wrapped_cmd)

            if kind != "vuv": # v/uv is just a mask => no dyn => no "generation"

                # Generate variance
                var_fname = "%s/%s.%s.var" % (out_path, base, kind)
                for t in range(0, T):
                    cmd = "cat %s/DNN/var/%s.var >> %s" % (self.conf.project_path, kind, var_fname)
                    wrapped_cmd = ["bash", "-c", cmd]
                    subprocess.call(wrapped_cmd)

                win_files = map_ffo["winfiles"]
                if len(win_files) < 3:
                    raise Exception("for DNN we need to have the delta and the acceleration window")

                # Get Windows part
                win_dir = "%s/%s" % (os.path.relpath(self.conf.TMP_PATH), "win")
                win_delta = 0
                with open("%s/%s" % (win_dir, os.path.basename(win_files[1]))) as f:
                    line = f.readline().strip()
                    elts = line.split()
                    win_delta = " ".join(elts[1:])

                win_accel = 0
                with open("%s/%s" % (win_dir, os.path.basename(win_files[2]))) as f:
                    line = f.readline().strip()
                    elts = line.split()
                    win_accel = " ".join(elts[1:])

                # Generate the parameter
                cmd = "merge -l %d -L %d %s/%s.%s.mean < %s/%s.%s.var " % \
                  (dim, dim, out_path, base, kind, out_path, base, kind)
                cmd += "| mlpg -m %d -d %s -d %s " % \
                  (order, win_delta, win_accel)
                self.logger.debug("%s stream DNN in process" % kind)

                # if lf0 we should apply the mask
                if kind == "lf0":
                    cmd += "| vopr -l 1 -m %s/%s.vuv | " % (out_path, base)
                    cmd += "sopr -magic 0 -MAGIC -1.0E+10 "

                cmd += "> %s/%s.%s" % (out_path, base, kind)
                wrapped_cmd = ["bash", "-c", cmd]
                subprocess.call(wrapped_cmd)

                # clean
                if not self.preserve:
                    os.remove("%s/%s.%s.mean" % (out_path, base, kind))
                    os.remove("%s/%s.%s.var" % (out_path, base, kind))
                    if (kind == "lf0"):
                        os.remove("%s/%s.vuv" % (out_path, base))


            else:
                # Adapt the mask for v/uv mask
                cmd = "cat %s/%s.%s.mean | sopr -s 0.5 -UNIT > %s/%s.%s" % \
                  (out_path, base, kind, out_path, base, kind)
                wrapped_cmd = ["bash", "-c", cmd]
                subprocess.call(wrapped_cmd)

                if not self.preserve:
                    os.remove("%s/%s.%s.mean" % (out_path, base, kind))

            # Next
            start += dim

    def run(self):
        while True:
            base = self.queue.get()
            if base is None:
                break

            self.logger.info("starting DNN generation for %s" % base)
            self.convertDUR2LAB("%s/%s.dur" % (self.out_path, base),
                                "%s/%s.lab" % (self.out_path, base))

            self.makeFeature("%s/%s.lab" % (self.out_path, base),
                            "%s/%s.ffi" % (self.out_path, base))


            # Prediction of the ffo
            self.forward(self.dnn_config,
                         "%s/%s.ffi" % (self.out_path, base),
                         "%s/%s.ffo" % (self.out_path, base))

            # Extract coefficients from the ffo
            self.extractParam(self.out_path, base)

            self.queue.task_done()
