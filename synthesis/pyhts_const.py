#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import configparser as cfp


TMP_DIR = 'tmp'
THIS_PATH = os.path.dirname(os.path.realpath(__file__))
PYHTS_PATH = os.path.join(THIS_PATH, os.pardir)


################################################################################
### Config
################################################################################

CFG_FPATH = os.path.join(PYHTS_PATH, 'config/config.cfg')

cfg = cfp.ConfigParser(inline_comment_prefixes='#')
with open(CFG_FPATH) as cfg_f:
    cfg.read_file(cfg_f)                                # not .read() (since file in mandatory, see ConfigParser doc)

SIGNAL = cfg['SIGNAL']
PATH = cfg['PATH']
ORDER = cfg['ORDER']
GEN = cfg['GEN']
GV = cfg['GV']
HMM = cfg['HMM']
VFLR = cfg['VFLR']
STRB = cfg['STRB']
STRE = cfg['STRE']
NWIN = cfg['NWIN']

# Create TMP_DIR if it doesn't exist
try:
    os.mkdir(TMP_DIR)
except FileExistsError:
    pass

## TMP PATHs
# Configs
TRAIN_CONFIG = os.path.join(TMP_DIR, "train%d.cfg" % os.getpid())
SYNTH_CONFIG = os.path.join(TMP_DIR, "synth%d.cfg" % os.getpid())

# Lists
GV_TIED_LIST_TMP = os.path.join(TMP_DIR, "tiedlist_%d_gv" % os.getpid())
TYPE_TIED_LIST_BASE = os.path.join(TMP_DIR, "tiedlist_%d" % os.getpid())
LABEL_LIST_FN = os.path.join(TMP_DIR, "list_all%d" % os.getpid())
TMP_LABELS_LIST_FN = os.path.join(TMP_DIR, "list_input_labels%d" % os.getpid())

# Tmp Scripts
GV_HED_UNSEEN_BASE = os.path.join(TMP_DIR, "mku_%d_gv" % os.getpid())
TYPE_HED_UNSEEN_BASE = os.path.join(TMP_DIR, "mku_%d" % os.getpid())
STRAIGHT_SCRIPT = os.path.join(TMP_DIR, "straight_%d.m" % os.getpid())

# Models
TMP_GV_MMF = os.path.join(TMP_DIR, "gv_%d.mmf" % os.getpid())
TMP_CMP_MMF = os.path.join(TMP_DIR, "cmp_%d.mmf" % os.getpid())
TMP_DUR_MMF = os.path.join(TMP_DIR, "dur_%d.mmf" % os.getpid())


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
SAMPLERATE = SIGNAL['SAMPFREQ']
FREQWARPING = FREQWARP_DIC[str(SAMPLERATE)]

WIN_PATH = 'win'    # FIXME


## Wanted types
TYPE_MAP = {'CMP': ('MGC', 'LF0', 'BAP'), 'DUR': 'DUR'}


## GV
SLNT = ('pau', 'h#', 'brth', 'start', 'end', 'spause', 'insp', 'ssil', 'sil')
