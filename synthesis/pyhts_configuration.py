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

        # Create TMP_PATH if it doesn't exist
        try:
            os.mkdir(self.TMP_PATH)
        except FileExistsError:
            pass

        ## TMP PATHs
        # Configs
        self.TRAIN_CONFIG = os.path.join(self.TMP_PATH, "train_%d.cfg" % os.getpid())
        self.SYNTH_CONFIG = os.path.join(self.TMP_PATH, "synth_%d.cfg" % os.getpid())

        # Lists
        self.GV_TIED_LIST_TMP = os.path.join(self.TMP_PATH, "tiedlist_%d_gv" % os.getpid())
        self.TYPE_TIED_LIST_BASE = os.path.join(self.TMP_PATH, "tiedlist_%d" % os.getpid())
        self.LABEL_LIST_FNAME = os.path.join(self.TMP_PATH, "list_all_%d" % os.getpid())
        self.TMP_GEN_LABFILE_LIST_FNAME = os.path.join(self.TMP_PATH, "list_input_labels_%d" % os.getpid())

        # Tmp Scripts
        self.GV_HED_UNSEEN_BASE = os.path.join(self.TMP_PATH, "mku_%d_gv" % os.getpid())
        self.TYPE_HED_UNSEEN_BASE = os.path.join(self.TMP_PATH, "mku_%d" % os.getpid())
        self.STRAIGHT_SCRIPT = os.path.join(self.TMP_PATH, "straight_%d.m" % os.getpid())

        # Models
        self.TMP_GV_MMF = os.path.join(self.TMP_PATH, "gv_%d.mmf" % os.getpid())
        self.TMP_CMP_MMF = os.path.join(self.TMP_PATH, "cmp_%d.mmf" % os.getpid())
        self.TMP_DUR_MMF = os.path.join(self.TMP_PATH, "dur_%d.mmf" % os.getpid())

        self.MATLAB="matlab"
        self.HHEd = "HHEd"
        self.HMGenS = "HMGenS"
        self.SOPR = "sopr"
        self.MGC2SP = "mgc2sp"

        if (config_fname is not None):
            self.parseConfig(config_fname)
        
    def parseConfig(self, config_fname):
        """
        """
        
        conf = None
        with open(config_fname) as cfg_f:
            conf = json.load(cfg_f)

        # TODO: add check streams kind + be robust !
        self.STREAMS = conf["models"]["cmp"]["streams"];
        self.GEN = conf["settings"]["synthesis"]
        self.MODELLING = conf["settings"]["modelling"]
        self.DUR = conf["models"]["dur"]

        ## SIGNAL
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

        self.GV = conf["settings"]["synthesis"]["gv"]
        self.GV["slnt"] = conf["gv"]["silences"]
        self.GV["use"] = conf["gv"]["use"]
        self.GV["cdgv"] = conf["gv"]["cdgv"]

        # Add path
        self.STRAIGHT_PATH = conf["path"]["straight"]

        try:
            self.MATLAB=conf["path"]["matlab"]
        except KeyError:
            pass

        
        try:
            self.HMGenS=conf["path"]["hts"] + "/HMGenS"
            self.HHEd=conf["path"]["hts"] + "/HHEd"
        except KeyError:
            pass
        
        
        try:
            self.HMGenS=conf["path"]["hmgens"]
        except KeyError:
            pass
        
        try:
            self.HHEd=conf["path"]["hhed"]
        except KeyError:
            pass
        
        try:
            self.SOPR=conf["path"]["sopr"]
        except KeyError:
            pass
        
        try:
            self.MGC2SP=conf["path"]["mgc2sp"]
        except KeyError:
            pass
        
