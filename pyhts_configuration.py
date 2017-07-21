#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import json

class Configuration(object):
    """
    Configuration file to synthesize speech using python version of HTS
    """
    def __init__(self, args):
        """ Initialize the configuration object based on the arguments args, the configuration file
        specified in the arguments and  some default values
        """

        self.PYHTS_PATH = os.path.dirname(os.path.realpath(__file__))

        # Check some command imposed information
        self.generator = args["--generator"]
        self.renderer = args["--renderer"]

        # Start of everything:  the project path and the config
        self.project_path = os.path.dirname(args["--config"])
        self.conf = self.parseConfig(args["--config"])

        # HTS options
        self.pg_type = int(args["--pg_type"])
        self.imposed_duration = args["--imposed_duration"]
        self.use_gv = False
        if (os.path.isdir(os.path.join(self.project_path, "gv"))):
            self.use_gv = True

        # HTS pathes
        self.hts_file_pathes = dict()
        self.hts_file_pathes["cmp_model"] = os.path.join(self.project_path, "models/re_clustered_cmp.mmf")
        self.hts_file_pathes["dur_model"] = os.path.join(self.project_path, "models/re_clustered_dur.mmf")
        self.hts_file_pathes["full_list"] = os.path.join(self.project_path, "full.list")
        self.hts_file_pathes["cmp_tree"]  = os.path.join(self.project_path, "trees")
        self.hts_file_pathes["dur_tree"]  = os.path.join(self.project_path, "trees")

        if self.use_gv:
            self.hts_file_pathes["gv"] = os.path.join(self.project_path, "gv")


        # Pathes
        self.THIS_PATH = os.path.dirname(os.path.realpath(__file__))
        self.CWD_PATH = os.getcwd()
        self.TMP_PATH = os.path.join(self.CWD_PATH, 'tmp')

        # Create TMP_PATH if it doesn't exist
        try:
            os.mkdir(self.TMP_PATH)
        except OSError:
            pass

        ## TMP PATHs
        # Configs
        self.TRAIN_CONFIG = os.path.join(self.TMP_PATH, "train_%d.cfg" % os.getpid())
        self.SYNTH_CONFIG = os.path.join(self.TMP_PATH, "synth_%d.cfg" % os.getpid())
        self.DNN_CONFIG = os.path.join(self.TMP_PATH, "dnn_%d.cfg" % os.getpid())

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



    def parseConfig(self, config_fname):
        """Extract configuration information from the configuration file indicated by config_fname
        """
        # Load config files
        conf = None
        with open(config_fname) as cfg_f:
            conf = json.load(cfg_f)

        if self.generator is None:
            try:
                self.generator = conf["settings"]["synthesis"]["generator"]
            except KeyError:
                # Back compatibility
                try:
                    self.generator = "default"
                    self.renderer = conf["settings"]["synthesis"]["kind"]
                except KeyError:
                    raise Exception("An acoustic generator needs to be defined")

        if self.renderer is None:
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

        self.nb_emitting_states = conf["models"]["global"]["nb_emitting_states"]
        self.frameshift = conf["signal"]["frameshift"]

        # Global Variance
        self.GV = conf["settings"]["synthesis"]["gv"]
        self.GV["slnt"] = conf["gv"]["silences"]
        self.GV["use"] = conf["gv"]["use"]
        self.GV["cdgv"] = conf["gv"]["cdgv"]

        # Add pathes
        self.PROJECT_DIR = conf["data"]["project_dir"]

        if ("path" in conf) and ("straight" in conf["path"]):
            self.STRAIGHT_PATH = conf["path"]["straight"]

        return conf
