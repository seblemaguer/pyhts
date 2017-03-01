#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 28 November 2016
"""

import sys
import os
import traceback
import argparse
import time
import logging
import subprocess
import numpy as np


from multiprocessing import Process, Queue, JoinableQueue

from shutil import copyfile # For copying files


class WeightsToJSON(Process):
    def __init__(self, conf, out_path, logger, queue):
        Process.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.queue = queue

    def run(self):
        while True:
            base = self.queue.get()

            if base is None:
                break

            for cur_stream in self.conf.STREAMS:
                if cur_stream["kind"] == "weight":
                    speakerWeights = cur_stream["parameters"]["speakerWeights"]

                    dim = cur_stream["order"]+1
                    input_data = np.fromfile("%s/%s.weight" % (self.out_path, base),
                                             dtype=np.float32)
                    nb_frames = int(input_data.size / dim)

                    input_data = np.reshape(input_data, (nb_frames,dim))

                    with open("%s/%s_weight.json" % (self.out_path, base), "w") as output_file:
                        output_file.write("[\n")

                        for f in range(0, nb_frames-1):
                            output_file.write("\t{\n")

                            # Dump phoneme weights
                            output_file.write("\t\t\"phonemeWeights\": [\n")
                            for d in range(0, dim-1):
                                output_file.write("\t\t\t%f,\n" % input_data[f, d])
                            output_file.write("\t\t\t%f\n" % input_data[f, dim-1])
                            output_file.write("\t\t],\n")

                            # Dump speaker weights
                            output_file.write("\t\t\"speakerWeights\": [\n")
                            for d in range(0, len(speakerWeights)-1):
                                output_file.write("\t\t\t%f,\n" % speakerWeights[d])
                            output_file.write("\t\t\t%f\n" % speakerWeights[len(speakerWeights)-1])
                            output_file.write("\t\t],\n")

                            # Dump timestamp
                            output_file.write("\t\t\"timeStamp\" :%f\n" % (f*0.005)) # FIXME: hardcoded frameshift
                            output_file.write("\t},\n")


                        output_file.write("\t{\n")

                        # Dump phoneme weights
                        output_file.write("\t\t\"phonemeWeights\": [")
                        for d in range(0, dim-1):
                            output_file.write("\t\t\t%f,\n" % input_data[(nb_frames-1), d])
                        output_file.write("\t\t\t%f\n" % input_data[(nb_frames-1), dim-1])
                        output_file.write("\t\t],\n")

                        # Dump speaker weights
                        output_file.write("\t\t\"speakerWeights\": [\n")
                        for d in range(0, len(speakerWeights)-1):
                            output_file.write("\t\t\t%f,\n" % speakerWeights[d])
                        output_file.write("\t\t\t%f\n" % speakerWeights[len(speakerWeights)-1])
                        output_file.write("\t\t],\n")

                        # Dump timestamp
                        output_file.write("\t\t\"timeStamp\" :%f\n" % ((nb_frames-1)*0.005)) # FIXME: hardcoded frameshift
                        output_file.write("\t}\n")

                        output_file.write("]\n")

            self.queue.task_done()


class WeightsToEMA(Process):
    def __init__(self, conf, out_path, logger, queue):
        Process.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.queue = queue

    def run(self):

        while True:
            base = self.queue.get()

            if base is None:
                break

            for cur_stream in self.conf.STREAMS:
                if cur_stream["kind"] == "weight":
                    param =  cur_stream["parameters"]
                    cmd = [
                        "weights-to-ema-json",
                        "--input", "%s/%s_weight.json" % (self.out_path, base),
                        "--model", param["tongue_model"].replace(".json", ".yaml"),
                        "--output", "%s/%s_ema.json" % (self.out_path, base),
                        "--reference", param["ref"], "--unit", "cm"
                    ]

                    cmd += ["--sourceIds"] + [str(i) for i in param["sourceIds"]]
                    cmd += ["--channels"] + param["channel_labels"]

                    subprocess.call(cmd)

            self.queue.task_done()
