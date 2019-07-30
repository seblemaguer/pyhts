#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION
    This package provides helper classes to deal with HTS configuration.
    For now only HMGenS-like synthesis is supported

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
"""

import os
import shutil
import logging

class ConfigurationGenerator:
    """HMGenS-like synthesis configuration helper
    """
    def __init__(self, conf):
        """Constructor

        :param conf: the configuration object
        :returns: None
        :rtype:

        """
        self.conf = conf
        self.logger = logging.getLogger("ConfigurationGenerator")


    def generateTrainingConfiguration(self):
        """Generate the configuration file needed to adapt the models to be able to synthesize unseen labels.

        :returns:None
        :rtype:

        """


        """
        Generate 'training configuration' => needed for the tree search
        """
        # Training configuration
        with open(self.conf.TRAIN_CONFIG, 'w') as f:
            f.write('NATURALREADORDER = T\n')
            f.write('NATURALWRITEORDER = T\n')

            # Variance floor options
            f.write('APPLYVFLOOR = T\n')

            cur_stream_idx = 0
            tmp_vflr_val = ''
            for cur_stream in self.conf.STREAMS:
                cur_stream_idx += 1
                tmp_vflr_val += ' '
                if cur_stream["is_msd"]:
                    end_stream_idx = cur_stream_idx + len(cur_stream["winfiles"]) - 1
                    tmp_vflr_val += ' '.join(['%s' % cur_stream["vflr"]] * (end_stream_idx - cur_stream_idx + 1))
                    cur_stream_idx = end_stream_idx
                else:
                    tmp_vflr_val += '%s' % cur_stream["vflr"]

            f.write('VFLOORSCALESTR = "Vector %d %s"\n' % (cur_stream_idx, tmp_vflr_val))

            f.write('APPLYDURVARFLOOR = T\n')
            f.write('DURVARFLOORPERCENTILE = %f\n' % (100 * float(self.conf.DUR["vflr"])))

            # Duration specific
            f.write('MAXSTDDEVCOEF = %s\n' % self.conf.MODELLING['maxdev'])
            f.write('MINDUR = %s\n' % self.conf.MODELLING['mindur'])


    def generateSynthesisConfiguration(self, use_gv):
        """Generate the synthesis configuration file needed by HMGenS

        :param use_gv: switch to activate the use of the global variance
        :returns: None
        :rtype:

        """
        # config file for parameter generation
        with open(self.conf.SYNTH_CONFIG, 'w') as f:

            # Global parameters
            f.write('NATURALREADORDER = T\n')
            f.write('NATURALWRITEORDER = T\n')
            f.write('USEALIGN = T\n')
            f.write('MAXEMITER = %s\n' % self.conf.GEN['maxemiter'])

            # Counting streams
            f.write('PDFSTRSIZE = "IntVec %d' % len(self.conf.STREAMS))    # PdfStream structure
            for cur_stream in self.conf.STREAMS:
                if cur_stream["is_msd"]:
                    f.write(' %d' % len(cur_stream["winfiles"]))
                else:
                    f.write(' 1')
            f.write('"\n')

            # Order of each coefficients
            f.write('PDFSTRORDER = "IntVec %d' % len(self.conf.STREAMS))    # PdfStream structure
            for cur_stream in self.conf.STREAMS:
                f.write(' %d' % (cur_stream["order"]+1))
            f.write('"\n')

            # Extension
            f.write('PDFSTREXT = "StrVec %d' % len(self.conf.STREAMS))
            for cur_stream in self.conf.STREAMS:
                f.write(' %s' % cur_stream["kind"])
            f.write('"\n')

            # Windows
            f.write('WINFN = "')                                        # WINFN: Name of window coefficient files

            win_dir = "%s/%s" % (os.path.relpath(self.conf.TMP_PATH), "win")
            if os.path.exists(win_dir):
                shutil.rmtree(win_dir)

            if self.conf.project_path is not None:
                shutil.copytree("%s/%s" % (self.conf.project_path, "win"), win_dir)

                for cur_stream in self.conf.STREAMS:
                    win = ""
                    for w in cur_stream["winfiles"]:
                        win = win + "%s/%s " % (win_dir, os.path.basename(w))

                    f.write('StrVec %d %s' % (len(cur_stream["winfiles"]), win))

            else:
                os.mkdir(win_dir)

                for cur_stream in self.conf.STREAMS:
                    win = ""

                    for w in cur_stream["winfiles"]:
                        shutil.copy("%s/%s" % (self.conf.PROJECT_DIR, w), "%s/%s" % (win_dir, w))
                        win = win + "%s/%s " % (win_dir, os.path.basename(w))

                    f.write('StrVec %d %s' % (len(cur_stream["winfiles"]), win))
            f.write('"\n')

            # Global variance
            if use_gv:
                f.write('EMEPSILON  = %f\n' % self.conf.GV['emepsilon'])
                f.write('USEGV      = TRUE\n')
                f.write('GVMODELMMF = %s\n' % self.conf.TMP_GV_MMF)
                f.write('GVHMMLIST  = %s\n' % self.conf.GV_TIED_LIST_TMP)
                f.write('MAXGVITER  = %d\n' % self.conf.GV['maxgviter'])
                f.write('GVEPSILON  = %f\n' % self.conf.GV['gvepsilon'])
                f.write('MINEUCNORM = %f\n' % self.conf.GV['mineucnorm'])
                f.write('STEPINIT   = %f\n' % self.conf.GV['stepinit'])
                f.write('STEPINC    = %f\n' % self.conf.GV['stepinc'])
                f.write('STEPDEC    = %f\n' % self.conf.GV['stepdec'])
                f.write('HMMWEIGHT  = %f\n' % self.conf.GV['hmmweight'])
                f.write('GVWEIGHT   = %f\n' % self.conf.GV['gvweight'])
                f.write('OPTKIND    = %s\n' % self.conf.GV['optkind'])

                if self.conf.GV["slnt"] is not None:
                    f.write('GVOFFMODEL = "StrVec %d %s"\n' % (len(self.conf.GV["slnt"]), ' '.join(self.conf.GV["slnt"])))

                if self.conf.GV['cdgv']:
                    f.write('CDGV = TRUE\n')
                else:
                    f.write('CDGV = FALSE\n')
            else:
                f.write('USEGV      = FALSE\n')
