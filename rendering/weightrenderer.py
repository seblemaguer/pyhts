#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

    Package which contains the helper to render the EMA,video,... from the tongue weights

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 10 October 2016
"""

import os
import logging
import shutil

from multiprocessing import JoinableQueue
from rendering.utils.weights import *
from rendering.utils.ema import *


class WEIGHTRenderer:
    """Rendering based on the tongue model weights
    """
    def __init__(self, conf, nb_proc, preserve):
        """Constructor

        :param conf: the configuration object
        :param nb_proc: the number of process to run
        :param preserve: switch to preserve intermediate files or not
        :returns: None
        :rtype:

        """

        self.conf = conf
        self.logger = logging.getLogger("WEIGHTRenderer")
        self.nb_proc = nb_proc
        self.preserve = preserve

    def generateWeightJSON(self, out_path, gen_labfile_base_lst):
        """Convert the binary weights to JSON formatted weights

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """

        # Convert duration to labels
        q = JoinableQueue()
        processs = []
        for base in range(self.nb_proc):
            t = WeightsToJSON(self.conf, out_path, self.logger, q)
            t.start()
            processs.append(t)

        for base in gen_labfile_base_lst:
            q.put(base)


        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(processs)):
            q.put(None)

        for t in processs:
            t.join()


    def generateEMAFromWeights(self, out_path, gen_labfile_base_lst):
        """Rendering EMA from the weights

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """

        # Convert duration to labels
        q = JoinableQueue()
        processs = []
        for base in range(self.nb_proc):
            t = WeightsToEMA(self.conf, out_path, q)
            t.start()
            processs.append(t)

        for base in gen_labfile_base_lst:
            q.put(base)

        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(processs)):
            q.put(None)

        for t in processs:
            t.join()



    def convertEMAJSONToBinary(self, out_path, gen_labfile_base_lst):
        """Convert JSON formatted EMA to binary EMA

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """

        # Convert duration to labels
        q = JoinableQueue()
        processs = []
        for base in range(self.nb_proc):
            t = JSONToEMA(self.conf, out_path, q)
            t.start()
            processs.append(t)


        for base in gen_labfile_base_lst:
            q.put(base)

        # block until all tasks are done
        q.join()

        # stop workers
        for i in range(len(processs)):
            q.put(None)

        for t in processs:
            t.join()

    def videoRendering(self, gen_labfile_base_lst, model, out_path):
        """Rendering tongue video using the given model and the predicted weights

        FIXME: not quite sure I can parallelize this one

        :param gen_labfile_base_lst: the file containing the list of utterances
        :param model: the tongue shape model
        :param out_path: the output directory path
        :returns: None
        :rtype:

        """
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
        """Rendering

        :param out_path: the output directory path
        :param gen_labfile_base_lst: the file containing the list of utterances
        :returns: None
        :rtype:

        """

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
