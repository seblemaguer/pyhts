#!/usr/bin/env python3
#-*- coding: utf-8 -*-


import os
import configparser as cfp


THIS_PATH = os.path.dirname(os.path.realpath(__file__))
PYHTS_PATH = os.path.join(THIS_PATH, os.pardir)
CWD_PATH = os.getcwd()

TMP_PATH = os.path.join(CWD_PATH, 'tmp')

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

HHEd = os.path.join(PATH['HTS'], 'HHEd')
HMGenS = os.path.join(PATH['HTS'], 'HMGenS')

# Create TMP_PATH if it doesn't exist
try:
    os.mkdir(TMP_PATH)
except FileExistsError:
    pass

## TMP PATHs
# Configs
TRAIN_CONFIG = os.path.join(TMP_PATH, "train_%d.cfg" % os.getpid())
SYNTH_CONFIG = os.path.join(TMP_PATH, "synth_%d.cfg" % os.getpid())

# Lists
GV_TIED_LIST_TMP = os.path.join(TMP_PATH, "tiedlist_%d_gv" % os.getpid())
TYPE_TIED_LIST_BASE = os.path.join(TMP_PATH, "tiedlist_%d" % os.getpid())
LABEL_LIST_FNAME = os.path.join(TMP_PATH, "list_all_%d" % os.getpid())
TMP_GEN_LABFILE_LIST_FNAME = os.path.join(TMP_PATH, "list_input_labels_%d" % os.getpid())

# Tmp Scripts
GV_HED_UNSEEN_BASE = os.path.join(TMP_PATH, "mku_%d_gv" % os.getpid())
TYPE_HED_UNSEEN_BASE = os.path.join(TMP_PATH, "mku_%d" % os.getpid())
STRAIGHT_SCRIPT = os.path.join(TMP_PATH, "straight_%d.m" % os.getpid())

# Models
TMP_GV_MMF = os.path.join(TMP_PATH, "gv_%d.mmf" % os.getpid())
TMP_CMP_MMF = os.path.join(TMP_PATH, "cmp_%d.mmf" % os.getpid())
TMP_DUR_MMF = os.path.join(TMP_PATH, "dur_%d.mmf" % os.getpid())


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
