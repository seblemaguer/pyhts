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
    def __init__(self, conf, _cmp_tree_path, cmp_model_fpath, full_list_fpath, logger, out_handle):
        Process.__init__(self)
        self.conf = conf
        self._cmp_tree_path = _cmp_tree_path
        self.cmp_model_fpath = cmp_model_fpath
        self.full_list_fpath = full_list_fpath
        self.out_handle = out_handle
        self.logger = logger

    def mk_unseen_script(self):
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
        self.mk_unseen_script()

        self.logger.info("CMP unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
              (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.cmp_model_fpath, self.conf.TMP_CMP_MMF, self.conf.TYPE_HED_UNSEEN_BASE+'_cmp.hed', self.full_list_fpath)
        subprocess.call(cmd.split(), stdout=self.out_handle)

class DURComposition(Process):
    def __init__(self, conf, _dur_tree_path, dur_model_fpath, full_list_fpath, logger, out_handle):
        Process.__init__(self)
        self.conf = conf
        self._dur_tree_path = _dur_tree_path
        self.dur_model_fpath = dur_model_fpath
        self.full_list_fpath = full_list_fpath
        self.out_handle = out_handle
        self.logger = logger

    def mk_unseen_script(self):
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
        self.mk_unseen_script()

        self.logger.info("Duration unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
              (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.dur_model_fpath, self.conf.TMP_DUR_MMF, self.conf.TYPE_HED_UNSEEN_BASE+'_dur.hed', self.full_list_fpath)
        subprocess.call(cmd.split(), stdout=self.out_handle)

class GVComposition(Process):
    def __init__(self, conf, gv_dir, logger,out_handle):
        Process.__init__(self)
        self.conf = conf
        self.gv_dir = gv_dir
        self.out_handle = out_handle
        self.logger = logger

    def mk_unseen_script(self):
        with open(self.conf.GV_HED_UNSEEN_BASE + '.hed', 'w') as f:
            f.write('\nTR 2\n\n')

            # Load trees
            f.write('// Load trees\n')
            for cur_stream in self.conf.STREAMS:
                f.write('LT "%s/%s.inf"\n\n' % (self.gv_dir, cur_stream["kind"]))

            # Make unseen
            f.write('// Make unseen\n')
            f.write('AU "%s"\n\n' % self.conf.LABEL_LIST_FNAME)

            # Compact model
            f.write('// Compact\n')
            f.write('CO "%s"\n\n' % self.conf.GV_TIED_LIST_TMP)

    def run(self):
        self.mk_unseen_script()

        self.logger.info("Global variance unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
            (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.gv_dir+'/clustered.mmf', self.conf.TMP_GV_MMF, self.conf.GV_HED_UNSEEN_BASE+'.hed',
             self.gv_dir+'/gv.list')
        subprocess.call(cmd.split(), stdout=self.out_handle)
