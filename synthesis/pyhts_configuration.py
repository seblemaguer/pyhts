#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import json

class Configuration(object):
    """
    Configuration file to synthesize speech using python version of HTS
    """
    def __init__(self, config_fname):
        """
        """
        # Pathes
        self.THIS_PATH = os.path.dirname(os.path.realpath(__file__))
        self.CWD_PATH = os.getcwd()
        self.TMP_PATH = os.path.join(self.CWD_PATH, 'tmp')

        # Input pathes
        self.project_path = None
        self.hts_file_pathes = dict()

        # Create TMP_PATH if it doesn't exist
        try:
            os.mkdir(self.TMP_PATH)
        except OSError:
            pass

        ## TMP PATHs
        # Configs
        self.TRAIN_CONFIG = os.path.join(self.TMP_PATH, "train_%d.cfg" % os.getpid())
        self.SYNTH_CONFIG = os.path.join(self.TMP_PATH, "synth_%d.cfg" % os.getpid())

        # Lists
        self.GV_TIED_LIST_TMP = os.path.join(self.TMP_PATH, "tiedlist_%d_gv" % os.getpid())
        self.TYPE_TIED_LIST_BASE = os.path.join(self.TMP_PATH, "tiedlist_%d" % os.getpid())
        self.LABEL_LIST_FNAME = os.path.join(self.TMP_PATH, "list_all_%d" % os.getpid())
        self.TMP_GEN_LABFILE_LIST_FNAME = os.path.join(self.TMP_PATH,
                                                       "list_input_labels_%d" % os.getpid())

        # Tmp Scripts
        self.GV_HED_UNSEEN_BASE = os.path.join(self.TMP_PATH, "mku_%d_gv" % os.getpid())
        self.TYPE_HED_UNSEEN_BASE = os.path.join(self.TMP_PATH, "mku_%d" % os.getpid())
        self.STRAIGHT_SCRIPT = os.path.join(self.TMP_PATH, "straight_%d.m" % os.getpid())

        # Models
        self.TMP_GV_MMF = os.path.join(self.TMP_PATH, "gv_%d.mmf" % os.getpid())
        self.TMP_CMP_MMF = os.path.join(self.TMP_PATH, "cmp_%d.mmf" % os.getpid())
        self.TMP_DUR_MMF = os.path.join(self.TMP_PATH, "dur_%d.mmf" % os.getpid())

        self.HHEd = "HHEd"
        self.HMGenS = "HMGenS"

        self.pg_type = 0

        if (config_fname is not None):
            self.parseConfig(config_fname)

    def parseConfig(self, config_fname):
        """
        """
        # Load config files
        conf = None
        with open(config_fname) as cfg_f:
            conf = json.load(cfg_f)

        try:
            self.generator = conf["settings"]["synthesis"]["generator"]
        except KeyError:
            # Back compatibility
            try:
                self.generator = "default"
                self.renderer = conf["settings"]["synthesis"]["kind"]
            except KeyError:
                raise Exception("An acoustic generator needs to be defined")

        try:
            self.renderer = conf["settings"]["synthesis"]["renderer"]
        except KeyError:
            if self.renderer is None:
                raise Exception("A renderer needs to be defined")



        self.STREAMS = conf["models"]["cmp"]["streams"];

        self.GEN = conf["settings"]["synthesis"]
        self.MODELLING = conf["settings"]["training"]
        self.DUR = conf["models"]["dur"]

        # SIGNAL
        FREQWARP_DIC = {
            '8000': 0.31,
            '10000': 0.35,
            '12000': 0.37,
            '16000': 0.42,
            '22050': 0.45,
            '32000': 0.45,
            '44100': 0.53,
            '48000': 0.55,
        }
        self.SIGNAL = conf["signal"]
        self.FREQWARPING = FREQWARP_DIC[str(self.SIGNAL["samplerate"])]

        # Global Variance
        self.GV = conf["settings"]["synthesis"]["gv"]
        self.GV["slnt"] = conf["gv"]["silences"]
        self.GV["use"] = conf["gv"]["use"]
        self.GV["cdgv"] = conf["gv"]["cdgv"]

        # Add pathes
        self.PROJECT_DIR = conf["data"]["project_dir"]

        if ("path" in conf) and ("straight" in conf["path"]):
            self.STRAIGHT_PATH = conf["path"]["straight"]
