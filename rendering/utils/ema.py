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

import sys
import os
import traceback
import argparse
import time
import logging
import subprocess
import numpy as np
import json

from threading import Thread

from shutil import copyfile # For copying files


CHANNELS =  ["T3", "T2", "T1", "ref", "jaw", "upperlip", "lowerlip"]


class EMAToJSON(Thread):
    def __init__(self, conf, out_path, logger, queue):
        Thread.__init__(self)
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
                if cur_stream["kind"] == "ema":
                    cur_channels = CHANNELS
                    if ("parameters" in cur_stream) and \
                       ("channel_labels" in cur_stream["parameters"]) :
                        cur_channels = cur_stream["parameters"]["channel_labels"]

                    input_data = np.fromfile("%s/%s.ema" % (self.out_path, base),
                                             dtype=np.float32)
                    nb_frames = int(input_data.size / (len(cur_channels)*3))

                    input_data = np.reshape(input_data, (nb_frames, len(cur_channels)*3))

                    with open("%s/%s.json" % (self.out_path, base), "w") as output_file:
                        output_file.write("{\n")
                        output_file.write("\t\"channels\": {\n")
                        for idx_c in range(0, len(cur_channels)):
                            c = idx_c*3
                            output_file.write("\t\t\"%s\": {\n" % cur_channels[idx_c])
                            output_file.write("\t\t\t\"position\": [\n")

                            # Frame values
                            for f in range(0, nb_frames-1):
                                output_file.write("\t\t\t\t%f, " % input_data[f, c])
                                output_file.write("\t\t\t\t%f, " % input_data[f, c+1])
                                output_file.write("\t\t\t\t%f,\n" % input_data[f, c+2])
                                # output_file.write("\t\t\t\t%f," % 0)

                            # Last frame
                            output_file.write("\t\t\t\t%f, " % input_data[nb_frames-1, c])
                            output_file.write("\t\t\t\t%f, " % input_data[nb_frames-1, c+1])
                            output_file.write("\t\t\t\t%f\n" % input_data[nb_frames-1, c+2])
                            # output_file.write("\t\t\t\t%f" % 0)

                            # Closing
                            output_file.write("\t\t\t]\n")
                            output_file.write("\t\t},\n")

                        output_file.write("\t\t\"ignore\": {\n")
                        output_file.write("\t\t}\n")
                        output_file.write("\t},\n")

                        output_file.write("\t\"timestamps\": [\n")
                        for f in range(0, nb_frames-1):
                            output_file.write("\t\t%f,\n" % (f*0.005))

                        output_file.write("\t\t%f\n" % ((nb_frames-1)*0.005))
                        output_file.write("\t]\n")

                        output_file.write("}\n")

                    # Cleaning
                    # os.remove("%s/%s.ema" % (self.out_path, base))


    # class JSONToEMA(Thread):
    #     def __init__(self, conf, out_path, base, logger):
    #         Thread.__init__(self)
    #         self.logger = logger
    #         self.conf = conf
    #         self.out_path = out_path
    #         base = base

    #     def run(self):
    #         def input_file = "%s/%s_ema.json" % (self.out_path, base)
    #         def output_file = "%s/%s.ema" % (self.out_path, base)

    #         with open(input_file) as f:
    #             content = json.load(f)


            self.queue.task_done()


class JSONToEMA(Thread):
    def __init__(self, conf, out_path, logger, queue):
        Thread.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.queue = queue

    def run(self):

        for cur_stream in self.conf.STREAMS:
            if (cur_stream["kind"] == "ema") or  (cur_stream["kind"] == "weight"):
                cur_channels = CHANNELS
                if ("parameters" in cur_stream) and \
                   ("channel_labels" in cur_stream["parameters"]) :
                    cur_channels = cur_stream["parameters"]["channel_labels"]

        while True:
            base = self.queue.get()
            if base is None:
                break

            input_filename = "%s/%s_ema.json" % (self.out_path, base)
            output_filename = "%s/%s.ema" % (self.out_path, base)

            with open(input_filename) as f:
                json_ema = json.load(f)

                nb_frames = int(len(json_ema["channels"][cur_channels[0]]["position"])/3)
                matrix = np.ndarray((nb_frames, len(cur_channels)*3),dtype=np.float32)

                for i in range(0, nb_frames):
                    for j, c in enumerate(cur_channels):
                        for d in range(0, 3):
                            matrix[i, j*3+d] = json_ema["channels"][c]["position"][i*3+d]

                with open(output_filename, "wb") as f_out:
                    matrix.tofile(f_out)

            self.queue.task_done()


class JSONtoPLY(Thread):
    def __init__(self, conf, out_path, logger, queue):
        Thread.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.queue = queue

    def run(self):
        while True:
            base = self.queue.get()
            if base is None:
                break

            for c in cur_channels:
                cmd = ["ema-json-to-mesh",
                       "--input", "%s/%s.json" % (self.out_path, base),
                       "--channel", c,
                       "--output", "%s/%s_%s.ply" % (self.out_path, base, c)]
                subprocess.call(cmd)

            self.queue.task_done()
