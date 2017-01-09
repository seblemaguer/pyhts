#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
"""

import os
# import sy
import time
import subprocess       # Shell command calling
import re

from threading import Thread

from shutil import copyfile # For copying files

from generation.utils.composition import *
from generation.utils.configuration import *
from generation.defaultgenerator import *

import generation.dnn.DNNDataIO as DNNDataIO
import generation.dnn.DNNDefine as DNNDefine

import tensorflow as tf
import numpy

###############################################################################
# Functions
###############################################################################
class DNNGenerator(DEFAULTGenerator):

    def __init__(self, conf, out_handle, logger, is_parallel, preserve):
        """
        Constructor
        """
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.is_parallel = is_parallel
        self.preserve = preserve
        self.configuration_generator = ConfigurationGenerator(conf, logger)
        self.frameshift = self.conf.frameshift * 10000 # frameshift ms * 10 000> frameshift in HTK unit (frameshift * 100ns)

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
        # perl utils/makefeature.pl ~/tmp/demo-cmu-dnn/DNN/qconf.conf
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

    def formatNumParameters(self, num_parameters):
        if num_parameters >= 1e+6:
            return '%.1f M' % (num_parameters / 1e+6)
        elif num_parameters >= 1e+3:
            return '%.1f k' % (num_parameters / 1e+3)
        else:
            return num_parameters


    def forward(self, config, model, stddev, ffi_path, ffo_path):
        with tf.Graph().as_default():
            inputs, outputs = DNNDataIO.batched_data(config['num_io_units'], 1)
            keep_prob = tf.placeholder(tf.float32)

            predicted_outputs, _ = DNNDefine.inference(
                inputs,
                config['num_io_units'],
                config['num_hidden_units'],
                config['hidden_activation'],
                'linear',
                keep_prob)

            num_parameters = DNNDefine.get_num_parameters()
            self.logger.debug('Number of parameters %s' % self.formatNumParameters(num_parameters))

            cost_op = DNNDefine.cost(predicted_outputs, outputs, stddev)

            init_op = tf.group(
                tf.global_variables_initializer(),
                tf.local_variables_initializer())

            saver = tf.train.Saver()

            sess = tf.Session(config=tf.ConfigProto(
                intra_op_parallelism_threads=config['num_threads']))

            sess.run(init_op)

            saver.restore(sess, model)

            self.logger.debug('Start forwarding')
            self.logger.debug('  Processing %s' % ffi_path)
            forward_data, num_examples = DNNDataIO.read_data_from_file([ffi_path, None], config['num_io_units'])

            total_cost = 0.0
            start_time = time.time()

            for j in range(num_examples):
                feed_dict = self.fillFeedDict(
                    forward_data, 1.0,
                    [inputs, outputs, keep_prob], 1, shuffle=False)

                predicts, value = sess.run(
                    [predicted_outputs, cost_op], feed_dict=feed_dict)

                total_cost += value

                append = False if j == 0 else True
                DNNDataIO.write_data(ffo_path, predicts, append)

            sess.close()

        self.logger.debug('End forwarding')

    def generateConfigFile(self):
        #FIXME: everything is hardcoded
        conf = "[Architecture]\n"
        conf += "num_input_units: 691\n"
        conf += "num_hidden_units: [1024, 1024, 1024]\n"
        conf += "num_output_units: 229\n"
        conf += "hidden_activation: Sigmoid\n"
        conf += "output_activation: Linear\n"
        conf += "\n"
        conf += "[Others]\n"
        conf += "num_threads: 0\n"
        conf += "restore_ckpt: 130000\n"

        with open(self.conf.DNN_CONFIG, "w") as f:
            f.write(conf)

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
                self.logger.info("%s stream DNN in process" % kind)

                # if lf0 we should apply the mask
                if kind == "lf0":
                    cmd += "| vopr -l 1 -m %s/%s.vuv | " % (out_path, base)
                    cmd += "sopr -magic 0 -MAGIC -1.0E+10 "

                cmd += "> %s/%s.%s" % (out_path, base, kind)
                print(cmd)
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
                print(cmd)
                wrapped_cmd = ["bash", "-c", cmd]
                subprocess.call(wrapped_cmd)

                if not self.preserve:
                    os.remove("%s/%s.%s.mean" % (out_path, base, kind))

            # Next
            start += dim

    def generate(self, out_path, gen_labfile_list_fname, use_gv):


        # Use the default HTS to get the duration
        DEFAULTGenerator.generate(self, out_path, gen_labfile_list_fname, use_gv)

        # load the config file
        self.generateConfigFile()
        config = DNNDataIO.load_config(self.conf.DNN_CONFIG)
        model = '-'.join(['%s/DNN/models/model.ckpt' % self.conf.project_path,
                          str(config['restore_ckpt'])])

        # See for the variance (FIXME: optional ?)
        stddev = numpy.ones(
            config['num_output_units'], dtype=numpy.float32)

        # variance = DNNDataIO.read_data("%s/DNN/var/global.var" % self.conf.project_path)
        # stddev = numpy.sqrt(variance)

        # Convert duration to labels
        with open(gen_labfile_list_fname) as f:
            for base in f.readlines():
                base = base.strip()
                base = os.path.splitext(os.path.basename(base))[0]
                self.convertDUR2LAB("%s/%s.dur" % (out_path, base),
                                    "%s/%s.lab" % (out_path, base))

                self.makeFeature("%s/%s.lab" % (out_path, base),
                                "%s/%s.ffi" % (out_path, base))


                # Prediction of the ffo
                self.forward(config, model, stddev,
                             "%s/%s.ffi" % (out_path, base),
                             "%s/%s.ffo" % (out_path, base))

                # Extract coefficients from the ffo
                self.extractParam(out_path, base)
