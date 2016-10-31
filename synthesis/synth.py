#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""
SYNOPSIS

    synth [-h,--help] [-v,--verbose] [--version]

DESCRIPTION

    **TODO** This describes how to use this script. This docstring
        will be printed by the script if there is an error or
        if the user requests help (-h or --help).

EXAMPLES

    %run /Volumes/Python/pyhts/synthesis/synth.py
            -m models/cmp/re_clustered.mmf
            -d models/dur/re_clustered.mmf
            -t trees/cmp
            -u trees/dur
            -i data/limsi_fr_tat_0001.lab
            -o OUT_WAV
            -l data/lists/full.list
            -p 0

EXIT STATUS

    **TODO** List exit codes

AUTHORS

    Sébastien Le Maguer     <sebastien.le_maguer@irisa.fr>
    Marc Evrard             <marc.evrard@limsi.fr>

LICENSE

    This script is in the public domain, free from copyrights or restrictions.

VERSION

    $Id$
"""
import os
import sys
import traceback
import argparse as ap

import time
import subprocess       # Shell command calling
import re
import logging
import shutil

from threading import Thread
from shutil import copyfile # For copying files
from pyhts_configuration import Configuration
import numpy as np
import rendering

################################################################################
### Model composition Threads
################################################################################
class CMPComposition(Thread):
    def __init__(self, conf, _cmp_tree_path, cmp_model_fpath, full_list_fpath, out_handle):
        Thread.__init__(self)
        self.conf = conf
        self._cmp_tree_path = _cmp_tree_path
        self.cmp_model_fpath = cmp_model_fpath
        self.full_list_fpath = full_list_fpath
        self.out_handle = out_handle

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

        logger.info("CMP unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
              (self.conf.HHEd, self.conf.TRAIN_CONFIG, cmp_model_fpath, self.conf.TMP_CMP_MMF, self.conf.TYPE_HED_UNSEEN_BASE+'_cmp.hed', self.full_list_fpath)
        subprocess.call(cmd.split(), stdout=self.out_handle)

class DURComposition(Thread):
    def __init__(self, conf, _dur_tree_path, dur_model_fpath, full_list_fpath, out_handle):
        Thread.__init__(self)
        self.conf = conf
        self._dur_tree_path = _dur_tree_path
        self.dur_model_fpath = dur_model_fpath
        self.full_list_fpath = full_list_fpath
        self.out_handle = out_handle

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

        logger.info("Duration unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
              (self.conf.HHEd, self.conf.TRAIN_CONFIG, dur_model_fpath, self.conf.TMP_DUR_MMF, self.conf.TYPE_HED_UNSEEN_BASE+'_dur.hed', self.full_list_fpath)
        subprocess.call(cmd.split(), stdout=self.out_handle)

class GVComposition(Thread):
    def __init__(self, conf, gv_dir, out_handle):
        Thread.__init__(self)
        self.conf = conf
        self.gv_dir = gv_dir
        self.out_handle = out_handle

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

        logger.info("Global variance unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
            (self.conf.HHEd, self.conf.TRAIN_CONFIG, self.gv_dir+'/clustered.mmf', self.conf.TMP_GV_MMF, self.conf.GV_HED_UNSEEN_BASE+'.hed',
             self.gv_dir+'/gv.list')
        subprocess.call(cmd.split(), stdout=self.out_handle)

################################################################################
### Utils
################################################################################
def copy_imposed_files(_in_path, _out_path, gen_labfile_base_lst, ext):
    """
    """
    for base in gen_labfile_base_lst:
        logger.info("copy %s/%s.%s to %s/%s.%s" % (_in_path, base, ext, _out_path, base, ext))
        copyfile("%s/%s.%s" % (_in_path, base, ext),
                 "%s/%s.%s" %  (_out_path, base, ext))

def adapt_f0_files(_in_path, _out_path, gen_labfile_base_lst, ext):
    """
    """
    for base in gen_labfile_base_lst:
        logger.info("copy %s/%s.%s to %s/%s.%s" % (_in_path, base, ext, _out_path, base, ext))
        # Retrieve mask
        mask = np.fromfile("%s/%s.%s" % (_out_path, base, ext), dtype=np.float32)

        # Retrieve F0
        lf0 = np.fromfile("%s/%s.%s" % (_in_path, base, ext), dtype=np.float32)
        for i in range(0, min(lf0.size, mask.size)):
            if mask[i] == -1e10:
                lf0[i] = mask[i]

        # Finally save the F0
        lf0.tofile("%s/%s.%s" % (_out_path, base, ext))


################################################################################
### Config + script functions
################################################################################
def generate_label_list(input_label_list):
    """
    Generate the label list file to get it through the tree
    """
    pattern = re.compile('[ \t]*([0-9]+)[ \t]+([0-9]+)[ \t]+(.*)')
    full_set = set()

    # Fullcontext list (Training + generation)
    for input_label in input_label_list:
        with open(input_label) as lab_file:
            for line in lab_file:
                line = line.strip()
                m = pattern.match(line)
                if m is not None:
                    lab = m.group(3)
                else:
                    lab = line
                full_set.add(lab)

    with open(conf.LABEL_LIST_FNAME, 'w') as list_file:
        list_file.write('\n'.join(full_set))


def generate_training_configuration():
    """
    Generate 'training configuration' => needed for the tree search
    """
    # Training configuration
    with open(conf.TRAIN_CONFIG, 'w') as f:
        f.write('NATURALREADORDER = T\n')
        f.write('NATURALWRITEORDER = T\n')

        # Variance floor options
        f.write('APPLYVFLOOR = T\n')

        cur_stream_idx = 0
        tmp_vflr_val = ''
        for cur_stream in conf.STREAMS:
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
        f.write('DURVARFLOORPERCENTILE = %f\n' % (100 * float(conf.DUR["vflr"])))

        # Duration specific
        f.write('MAXSTDDEVCOEF = %s\n' % conf.MODELLING['maxdev'])
        f.write('MINDUR = %s\n' % conf.MODELLING['mindur'])


def generate_synthesis_configuration(_use_gv):
    """
    Generate the synthesis configuration file needed by HMGenS
    """
    # Synthesis configuration

    # config file for parameter generation
    with open(conf.SYNTH_CONFIG, 'w') as f:

        # Global parameters
        f.write('NATURALREADORDER = T\n')
        f.write('NATURALWRITEORDER = T\n')
        f.write('USEALIGN = T\n')
        f.write('MAXEMITER = %s\n' % conf.GEN['maxemiter'])

        # Counting streams
        f.write('PDFSTRSIZE = "IntVec %d' % len(conf.STREAMS))    # PdfStream structure
        for cur_stream in conf.STREAMS:
            if cur_stream["is_msd"]:
                f.write(' %d' % len(cur_stream["winfiles"]))
            else:
                f.write(' 1')
        f.write('"\n')

        # Order of each coefficients
        f.write('PDFSTRORDER = "IntVec %d' % len(conf.STREAMS))    # PdfStream structure
        for cur_stream in conf.STREAMS:
            f.write(' %d' % (cur_stream["order"]+1))
        f.write('"\n')

        # Extension
        f.write('PDFSTREXT = "StrVec %d' % len(conf.STREAMS))
        for cur_stream in conf.STREAMS:
            f.write(' %s' % cur_stream["kind"])
        f.write('"\n')

        # Windows
        f.write('WINFN = "')                                        # WINFN: Name of window coefficient files

        #
        win_dir = "%s/%s" % (os.path.relpath(conf.TMP_PATH), "win")
        if os.path.exists(win_dir):
            shutil.rmtree(win_dir)

        if project_path is not None:
            shutil.copytree("%s/%s" % (project_path, "win"), win_dir)
        else:
            os.mkdir(win_dir)

        for cur_stream in conf.STREAMS:
            win = ""

            for w in cur_stream["winfiles"]:
                if project_path is None:
                    shutil.copy("%s/%s" % (conf.PROJECT_DIR, w), "%s/%s" % (win_dir, w))

                win = win + "%s/%s " % (win_dir, os.path.basename(w))

            f.write('StrVec %d %s' % (len(cur_stream["winfiles"]), win))
        f.write('"\n')

        # Global variance
        if _use_gv:
            f.write('EMEPSILON  = %f\n' % conf.GV['emepsilon'])
            f.write('USEGV      = TRUE\n')
            f.write('GVMODELMMF = %s\n' % conf.TMP_GV_MMF)
            f.write('GVHMMLIST  = %s\n' % conf.GV_TIED_LIST_TMP)
            f.write('MAXGVITER  = %d\n' % conf.GV['maxgviter'])
            f.write('GVEPSILON  = %f\n' % conf.GV['gvepsilon'])
            f.write('MINEUCNORM = %f\n' % conf.GV['mineucnorm'])
            f.write('STEPINIT   = %f\n' % conf.GV['stepinit'])
            f.write('STEPINC    = %f\n' % conf.GV['stepinc'])
            f.write('STEPDEC    = %f\n' % conf.GV['stepdec'])
            f.write('HMMWEIGHT  = %f\n' % conf.GV['hmmweight'])
            f.write('GVWEIGHT   = %f\n' % conf.GV['gvweight'])
            f.write('OPTKIND    = %s\n' % conf.GV['optkind'])

            if conf.GV["slnt"] is not None:
                f.write('GVOFFMODEL = "StrVec %d %s"\n' % (len(conf.GV["slnt"]), ' '.join(conf.GV["slnt"])))

            if conf.GV['cdgv']:
                f.write('CDGV = TRUE\n')
            else:
                f.write('CDGV = FALSE\n')
        else:
            f.write('USEGV      = FALSE\n')


################################################################################
### Main function
################################################################################

def setup_logging(is_verbose):
    """
    Setup logging according to the verbose mode
    """
    logging.basicConfig(format='[%(asctime)s] %(levelname)s : %(message)s')

    if not is_verbose:
        level = logging.INFO
    else:
        level = logging.DEBUG

    # handler = ColorizingStreamHandler(sys.stderr)
    # root.setLevel(logging.DEBUG)
    # if root.handlers:
    #     for handler in root.handlers:
    #         root.removeHandler(handler)
    # formatter = logging.Formatter(datefmt='%Y/%m/%d %H:%M',
    #                               fmt='[%(asctime)s %(name)s  %(levelname)s] %(message)s')
    # handler.setFormatter(formatter)
    # logging.getLogger().addHandler(handler)

    _logger = logging.getLogger('EXTRACT_STRAIGHT')
    _logger.setLevel(level)

    return _logger


def main():
    """
    Main entry function
    """
    global args

    # Create output directory if none, else pass
    try:
        os.mkdir(out_path)
    except OSError:
        pass

    # 0. Generate list file
    gen_labfile_list_fname = conf.TMP_GEN_LABFILE_LIST_FNAME
    if args.input_is_list:
        gen_labfile_list_fname = args.input_fname
    else:
        with open(gen_labfile_list_fname, 'w') as f:
            f.write(args.input_fname + '\n')

    gen_labfile_base_lst = []
    gen_labfile_lst = []
    with open(gen_labfile_list_fname) as f:
        for line in f:
            gen_labfile_lst.append(line.strip())
            gen_labfile_base_lst.append(os.path.splitext(os.path.basename(line.strip()))[0])

    generate_label_list(gen_labfile_lst)

    # 1. Generate configs
    generate_training_configuration()
    generate_synthesis_configuration(use_gv)


    # 3. Compose models
    #    * CMP
    thread_cmp = CMPComposition(conf, cmp_tree_path, cmp_model_fpath, full_list_fpath, out_handle)
    thread_cmp.start()
    if not args.is_parallel:
        thread_cmp.join()

    #    * DUR
    thread_dur = DURComposition(conf, dur_tree_path, dur_model_fpath, full_list_fpath, out_handle)
    thread_dur.start()
    if not args.is_parallel:
        thread_dur.join()


    #    * GV
    if use_gv:
        thread_gv = GVComposition(conf, gv_path, out_handle)
        thread_gv.start()
        thread_gv.join()


    if args.is_parallel:
       thread_cmp.join()
       thread_dur.join()

    # 4. Generate parameters
    logger.info("Parameter generation")
    if args.imposed_duration:
        cmd = '%s -m -A -B -C %s -D -T 1 -S %s -t %s -c %d -H %s -N %s -M %s %s %s' % \
              (conf.HMGenS, conf.SYNTH_CONFIG, gen_labfile_list_fname,
               conf.MODELLING["beam"], int(args.pg_type), conf.TMP_CMP_MMF, conf.TMP_DUR_MMF,
               out_path, conf.TYPE_TIED_LIST_BASE+'_cmp', conf.TYPE_TIED_LIST_BASE+'_dur')
    else:
        cmd = '%s -A -B -C %s -D -T 1 -S %s -t %s -c %d -H %s -N %s -M %s %s %s' % \
              (conf.HMGenS, conf.SYNTH_CONFIG, gen_labfile_list_fname,
               conf.MODELLING["beam"], int(args.pg_type), conf.TMP_CMP_MMF, conf.TMP_DUR_MMF,
               out_path, conf.TYPE_TIED_LIST_BASE+'_cmp', conf.TYPE_TIED_LIST_BASE+'_dur')
    subprocess.call(cmd.split(), stdout=out_handle)

    # 5. Convert/adapt parameters
    if args.impose_f0_dir and args.impose_interpolated_f0_dir:
        raise Exception("cannot impose 2 kind of F0 at the same time")

    if args.impose_f0_dir:
        logger.info("replace f0 using imposed one")
        copy_imposed_files(args.impose_f0_dir, out_path, gen_labfile_base_lst, "lf0")
    if args.impose_interpolated_f0_dir:
        logger.info("replace f0 using interpolated one")
        adapt_f0_files(args.impose_interpolated_f0_dir, out_path, gen_labfile_base_lst, "lf0")
    if args.impose_mgc_dir:
        copy_imposed_file(args.impose_mgc_dir, out_path, gen_labfile_base_lst, "mgc")
    if args.impose_bap_dir:
        copy_imposed_file(args.impose_bap_dir, out_path, gen_labfile_base_lst, "bap")

    # 6. Call straight to synthesize
    renderer = rendering.generateRenderer(conf, out_handle, logger, args.is_parallel, args.preserve_intermediate)
    renderer.render(out_path, gen_labfile_base_lst)


    if not args.preserve_intermediate:
        shutil.rmtree(conf.TMP_PATH)

################################################################################
### Enveloping
################################################################################

if __name__ == '__main__':
    try:
        argp = ap.ArgumentParser(description=globals()['__doc__'], formatter_class=ap.RawDescriptionHelpFormatter)

        argp.add_argument('-v', '--verbose', action='store_true',
                          default=False, help='verbose output')

        # Configuration
        argp.add_argument('-c', '--config', dest='config_fname',
                          help="Configuration file", metavar='FILE')

        # models
        argp.add_argument('-m', '--cmp', dest='cmp_model_fname',
                          help="CMP model file", metavar='FILE')
        argp.add_argument('-d', '--dur', dest='dur_model_fname',
                          help="Duration model file", metavar='FILE')
        argp.add_argument('-l', '--list', dest='full_list_fname',
                          help="Label list training lab files", metavar='FILE')
        argp.add_argument('-t', '--cmp_tree', dest='cmp_tree_dir',
                          help="Directory which contains the coefficient trees")
        argp.add_argument('-u', '--dur_tree', dest='dur_tree_dir',
                          help="Directory which contains the duration tree")
        argp.add_argument('-g', '--gv', dest='gv_dir',
                          help="Define the global variance model directory")

        # Options
        argp.add_argument('-p', '--pg_type', dest='pg_type', default=0,
                          help="Parameter generation type")
        argp.add_argument('-s', '--with_scp', dest='input_is_list', action='store_true',
                          default=False, help="the input is a scp formatted file")
        argp.add_argument('-P', '--parallel', dest="is_parallel", action="store_true",
                          default=False, help="Activate parallel mode")
        argp.add_argument('-R', '--preserve', dest="preserve_intermediate", action="store_true",
                          default=False, help="do not delete the intermediate and temporary files")

        # Imposing
        argp.add_argument("-D", "--imposed_duration", dest="imposed_duration", action="store_true",
                          default=False, help="imposing the duration at a phone level")
        argp.add_argument("-F", "--imposed_f0_dir", dest="impose_f0_dir",
                          help="F0 directory to use at the synthesis level")
        argp.add_argument("-I", "--imposed_interpolated_f0_dir", dest="impose_interpolated_f0_dir",
                          help="Interpolated F0 directory to use at the synthesis level (unvoiced property is predicted by the F0 from HTS directly)")
        argp.add_argument("-M", "--imposed_mgc_dir", dest="impose_mgc_dir",
                          help="MGC directory to use at the synthesis level")
        argp.add_argument("-B", "--imposed_bap_dir", dest="impose_bap_dir",
                          help="BAP directory to use at the synthesis level")

        # input/output
        argp.add_argument('-i', '--input', dest='input_fname', required=True,
                          help="Input lab file for synthesis", metavar='FILE')
        argp.add_argument('-o', '--output', dest='output', required=True,
                          help="Output wav directory", metavar='FILE')


        args = argp.parse_args()

        conf = Configuration(args.config_fname)

        # PATH
        if args.cmp_model_fname is not None:
            project_path = None
            cmp_model_fpath = os.path.join(conf.CWD_PATH, args.cmp_model_fname)
            dur_model_fpath = os.path.join(conf.CWD_PATH, args.dur_model_fname)
            full_list_fpath = os.path.join(conf.CWD_PATH, args.full_list_fname)
            cmp_tree_path = os.path.join(conf.CWD_PATH, args.cmp_tree_dir)
            dur_tree_path = os.path.join(conf.CWD_PATH, args.dur_tree_dir)

            # GV checking
            use_gv = args.gv_dir
            gv_path = args.gv_dir
        else:
            project_path = os.path.dirname(args.config_fname)
            cmp_model_fpath = os.path.join(project_path, "models/re_clustered_cmp.mmf")
            dur_model_fpath = os.path.join(project_path, "models/re_clustered_dur.mmf")
            full_list_fpath = os.path.join(project_path, "full.list")
            cmp_tree_path = os.path.join(project_path, "trees")
            dur_tree_path = os.path.join(project_path, "trees")

            use_gv = False
            if (os.path.isdir(os.path.join(project_path, "gv"))):
                use_gv = True
                gv_path = os.path.join(project_path, "gv")

        # Out directory
        out_path = os.path.join(conf.CWD_PATH, args.output)


        # Debug time
        logger = setup_logging(args.verbose)
        if args.verbose:
            out_handle = sys.stdout
        else:
            out_handle = subprocess.DEVNULL

        # Debug time
        start_time = time.time()
        if args.verbose:
            logger.debug(time.asctime())

        # Running main function <=> run application
        main()

        # Debug time
        if args.verbose:
            logger.debug(time.asctime())
        if args.verbose:
            logger.debug("TOTAL TIME IN MINUTES: %f" % ((time.time() - start_time) / 60.0))

        # Exit program
        sys.exit(0)
    except KeyboardInterrupt as e:  # Ctrl-C
        raise e
    except SystemExit as e:         # sys.exit()
        pass
    except Exception as e:
        print("ERROR, UNEXPECTED EXCEPTION")
        print(str(e))
        traceback.print_exc()
        # os._exit(1)
        sys.exit(1)
