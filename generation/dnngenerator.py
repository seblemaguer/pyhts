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
import time
import subprocess       # Shell command calling
import re


# Multi process
from multiprocessing import Process, Queue, JoinableQueue

from shutil import copyfile # For copying files

from generation.utils.composition import *
from generation.utils.configuration import *
from generation.defaultgenerator import *

import generation.dnn.DNNDataIO as DNNDataIO
import generation.dnn.DNNDefine as DNNDefine
from generation.utils.dnnparamgeneration import *
import tensorflow as tf
import numpy

###############################################################################
# Functions
###############################################################################
class DNNGenerator(DEFAULTGenerator):
    """
    TODO:
    """
    def __init__(self, conf, out_handle, logger, nb_proc, preserve):
        """
        Constructor
        """
        self.conf = conf
        self.logger = logger
        self.out_handle = out_handle
        self.nb_proc = nb_proc
        self.preserve = preserve
        self.configuration_generator = ConfigurationGenerator(conf, logger)
        self.frameshift = self.conf.frameshift * 10000 # frameshift ms * 10 000> frameshift in HTK unit (frameshift * 100ns)


    def generateConfigFile(self):
        input_dim = 691 # FIXME: hardcoded

        output_dim = 0
        for s in self.conf.conf["models"]["ffo"]["streams"]:
            output_dim += ((s["order"] + 1) * len(s["winfiles"]) )


        conf = "[Architecture]\n"
        conf += "num_input_units: %d\n" % input_dim
        conf += "num_hidden_units: %s\n"  % self.conf.conf["settings"]["dnn"]["num_hidden_units"]
        conf += "num_output_units: %d\n" % output_dim
        conf += "hidden_activation: %s\n"  % self.conf.conf["settings"]["dnn"]["hidden_activation"]
        conf += "output_activation: Linear\n"
        conf += "\n"
        conf += "[Others]\n"
        conf += "num_threads: %d\n" % self.conf.conf["settings"]["dnn"]["num_threads"]
        conf += "restore_ckpt: 183350\n" # FIXME: hardcoded value

        with open(self.conf.DNN_CONFIG, "w") as f:
            f.write(conf)

    def formatNumParameters(self, num_parameters):
        if num_parameters >= 1e+6:
            return '%.1f M' % (num_parameters / 1e+6)
        elif num_parameters >= 1e+3:
            return '%.1f k' % (num_parameters / 1e+3)
        else:
            return num_parameters

    def loadSession(self, model, config, stddev):

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

            sess = tf.Session(config=tf.ConfigProto(intra_op_parallelism_threads=config['num_threads']))

            sess.run(init_op)

            saver.restore(sess, model)

            config["session"] = sess
            config["inputs"] = inputs
            config["outputs"] = outputs
            config["keep_prob"] = keep_prob
            config["predicted_outputs"] = predicted_outputs
            config["cost_op"] = cost_op

            return config

    def generate(self, out_path, gen_labfile_list_fname, use_gv):

        # Use the default HTS to get the duration
        DEFAULTGenerator.generate(self, out_path, gen_labfile_list_fname, use_gv)

        # load the config file
        self.generateConfigFile()
        config = DNNDataIO.load_config(self.conf.DNN_CONFIG)
        model = '%s/DNN/models/model.ckpt' % self.conf.project_path
        if ("restore_ckpt" in config) and (config['restore_ckpt'] > 0):
            model += "-%s" % str(config['restore_ckpt'])

        # # See for the variance (FIXME: optional ?)
        # stddev = numpy.ones(
        #     config['num_output_units'], dtype=numpy.float32)

        variance = DNNDataIO.read_data("%s/DNN/var/global.var" % self.conf.project_path)
        stddev = numpy.sqrt(variance)

        # Restore session
        config = self.loadSession(model, config, stddev)

        # FIXME: wha
        q = JoinableQueue()
        processes = []
        for base in range(args.nb_proc):
            t = DNNParamGeneration(self.conf, config,
                                   self.frameshift, out_path,
                                   self.logger, self.out_handle, self.preserve,
                                   q)
            t.start()
            processes.append(t)


        # Fill the queue for the workers
        with open(gen_labfile_list_fname) as f:
            for base in f.readlines():
                base = base.strip()
                base = os.path.splitext(os.path.basename(base))[0]

                # First some cleaning
                for cmp in self.conf.conf["models"]["cmp"]["streams"]:
                    kind = cmp["kind"]
                    os.remove("%s/%s.%s" % (out_path, base, kind))

                q.put(base)

        # Fill the queue by adding a None to indicate the end
        for i in range(len(processes)):
            q.put(None)

        # Wait the end of the processes
        for t in processes:
            t.join()

        config["session"].close()
