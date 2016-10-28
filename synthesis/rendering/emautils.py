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

from threading import Thread

from shutil import copyfile # For copying files


CHANNELS =  ["T3", "T2", "T1", "ref", "jaw", "upperlip", "lowerlip"]


class EMAToJSON(Thread):
    def __init__(self, conf, out_path, base, logger):
        Thread.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.base = base

    def run(self):
        for cur_stream in self.conf.STREAMS:
            if cur_stream["kind"] == "ema":
                input_data = np.fromfile("%s/%s.ema" % (self.out_path, self.base),
                                         dtype=np.float32)
                nb_frames = int(input_data.size / (len(CHANNELS)*3))

                input_data = np.reshape(input_data, (nb_frames, len(CHANNELS)*3))

                with open("%s/%s.json" % (self.out_path, self.base), "w") as output_file:
                    output_file.write("{\n")
                    output_file.write("\t\"channels\": {\n")
                    for idx_c in range(0, len(CHANNELS)):
                        c = idx_c*3
                        output_file.write("\t\t\"%s\": {\n" % CHANNELS[idx_c])
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
                # os.remove("%s/%s.ema" % (self.out_path, self.base))


class JSONtoPLY(Thread):
    def __init__(self, conf, out_path, base, logger):
        Thread.__init__(self)
        self.logger = logger
        self.conf = conf
        self.out_path = out_path
        self.base = base

    def run(self):
        for c in CHANNELS:
            cmd = ["ema-json-to-mesh",
                   "--input", "%s/%s.json" % (self.out_path, self.base),
                   "--channel", c,
                   "--output", "%s/%s_%s.ply" % (self.out_path, self.base, c)]
            subprocess.call(cmd)
