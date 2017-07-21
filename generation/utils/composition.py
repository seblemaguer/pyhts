#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION
    Package which provides the classes to adapt the model to be used by HMGenS to achieve the synthesis

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
"""

import os
import sys

import time
import subprocess       # Shell command calling
import re
import logging
import shutil


from multiprocessing import Process, Queue, JoinableQueue
from shutil import copyfile # For copying files


################################################################################
### Model composition Processs
################################################################################
class CMPComposition(Process):
    """ Class to generate the CMP models based on a given set of labels, the trained models and decision trees.
    This class is a process to be able to be run in parallel.
    """

    def __init__(self, conf, _cmp_tree_path, cmp_model_fpath, full_list_fpath, logger, out_handle):
        """ Constructor

        :param conf: the configuration object
        :param _cmp_tree_path: the path of the decision tree file
        :param cmp_model_fpath: the path of the model file
        :param full_list_fpath: the path of the file containing the list of needed labels
        :param logger: the logger
        :param out_handle: the handle to dump the standard output of the command
        :returns: None
        :rtype:

        """
        Process.__init__(self)
        self.conf = conf
        self._cmp_tree_path = _cmp_tree_path
        self.cmp_model_fpath = cmp_model_fpath
        self.full_list_fpath = full_list_fpath
        self.out_handle = out_handle
        self.logger = logger

    def mk_unseen_script(self):
        """Generate the HHEd script which contains the command to generate an adapted model file
        for the synthesis stage.

        :returns:None
        :rtype:

        """

        with open('%s_cmp.hed' % self.conf.TYPE_HED_UNSEEN_BASE, 'w') as f:
            f.write('\nTR 2\n\n')
            # Load trees
            f.write('// Load trees\n')
            for cur_stream in self.conf.STREAMS:
                f.write('LT "%s/%s.%s"\n\n' % (self._cmp_tree_path, cur_stream["kind"], self.conf.GEN["tree_ext"]))

            # Make unseen
            f.write('// Make unseen\n')
            f.write('AU "%s"\n\n' % self.conf.LABEL_LIST_FNAME)

            # Compact model
            f.write('// Compact\n')
            f.write('CO "%s_cmp"\n\n' % self.conf.TYPE_TIED_LIST_BASE)

    def run(self):
        """Generate the model adapted to the synthesis for the CMP part

        :returns: None
        :rtype:

        """
        self.mk_unseen_script()

        self.logger.info("CMP unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
              (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.cmp_model_fpath, self.conf.TMP_CMP_MMF, self.conf.TYPE_HED_UNSEEN_BASE+'_cmp.hed', self.full_list_fpath)
        subprocess.call(cmd.split(), stdout=self.out_handle)


class DURComposition(Process):
    """ Class to generate the duration models based on a given set of labels, the trained models and decision trees.
    This class is a process to be able to be run in parallel.
    """

    def __init__(self, conf, _dur_tree_path, dur_model_fpath, full_list_fpath, logger, out_handle):
        """ Constructor

        :param conf: the configuration object
        :param _dur_tree_path: the path of the decision tree file
        :param dur_model_fpath: the path of the model file
        :param full_list_fpath: the path of the file containing the list of needed labels
        :param logger: the logger
        :param out_handle: the handle to dump the standard output of the command
        :returns: None
        :rtype:

        """
        Process.__init__(self)
        self.conf = conf
        self._dur_tree_path = _dur_tree_path
        self.dur_model_fpath = dur_model_fpath
        self.full_list_fpath = full_list_fpath
        self.out_handle = out_handle
        self.logger = logger

    def mk_unseen_script(self):
        """Generate the HHEd script which contains the command to generate an adapted model file
        for the synthesis stage.

        :returns:None
        :rtype:

        """
        with open('%s_dur.hed' % self.conf.TYPE_HED_UNSEEN_BASE, 'w') as f:
            f.write('\nTR 2\n\n')

            # Load trees
            f.write('// Load trees\n')
            f.write('LT "%s/dur.%s"\n\n' % (self._dur_tree_path, self.conf.GEN["tree_ext"]))

            # Make unseen
            f.write('// Make unseen\n')
            f.write('AU "%s"\n\n' % self.conf.LABEL_LIST_FNAME)

            # Compact model
            f.write('// Compact\n')
            f.write('CO "%s_dur"\n\n' % self.conf.TYPE_TIED_LIST_BASE)

    def run(self):
        """Generate the model adapted to the synthesis for the duration part

        :returns: None
        :rtype:

        """
        self.mk_unseen_script()

        self.logger.info("Duration unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
              (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.dur_model_fpath, self.conf.TMP_DUR_MMF, self.conf.TYPE_HED_UNSEEN_BASE+'_dur.hed', self.full_list_fpath)
        subprocess.call(cmd.split(), stdout=self.out_handle)

class GVComposition(Process):
    """ Class to generate the global variance.
    This class is a process to be able to be run in parallel.
    """

    def __init__(self, conf, _gv_path, logger,out_handle):
        """ Constructor

        :param conf: the configuration object
        :param _gv_path: the path of the directory containing all the needed files for the GV stage
        :param logger: the logger
        :param out_handle: the handle to dump the standard output of the command
        :returns: None
        :rtype:

        """
        Process.__init__(self)
        self.conf = conf
        self.gv_path = _gv_path
        self.out_handle = out_handle
        self.logger = logger

    def mk_unseen_script(self):
        """Generate the HHEd script which contains the command to generate an adapted model file
        for the synthesis stage.

        :returns:None
        :rtype:

        """
        with open(self.conf.GV_HED_UNSEEN_BASE + '.hed', 'w') as f:
            f.write('\nTR 2\n\n')

            # Load trees
            f.write('// Load trees\n')
            for cur_stream in self.conf.STREAMS:
                f.write('LT "%s/%s.inf"\n\n' % (self.gv_path, cur_stream["kind"]))

            # Make unseen
            f.write('// Make unseen\n')
            f.write('AU "%s"\n\n' % self.conf.LABEL_LIST_FNAME)

            # Compact model
            f.write('// Compact\n')
            f.write('CO "%s"\n\n' % self.conf.GV_TIED_LIST_TMP)

    def run(self):
        """Generate the model adapted to the synthesis for the global variance part

        :returns: None
        :rtype:

        """
        self.mk_unseen_script()

        self.logger.info("Global variance unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
            (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.gv_path+'/clustered.mmf', self.conf.TMP_GV_MMF, self.conf.GV_HED_UNSEEN_BASE+'.hed',
             self.gv_path+'/gv.list')
        subprocess.call(cmd.split(), stdout=self.out_handle)
