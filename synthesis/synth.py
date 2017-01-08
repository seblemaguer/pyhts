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
import generation

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
def generate_label_list(conf, input_label_list):
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
    global args, logger

    conf = Configuration(args.config_fname)

    # PATH
    conf.imposed_duration = args.imposed_duration
    if args.cmp_model_fname is not None:
        conf.project_path = None
        conf.hts_file_pathes["cmp_model"] = os.path.join(conf.CWD_PATH, args.cmp_model_fname)
        conf.hts_file_pathes["dur_model"] = os.path.join(conf.CWD_PATH, args.dur_model_fname)
        conf.hts_file_pathes["full_list"] = os.path.join(conf.CWD_PATH, args.full_list_fname)
        conf.hts_file_pathes["cmp_tree"]  = os.path.join(conf.CWD_PATH, args.cmp_tree_dir)
        conf.hts_file_pathes["dur_tree"]  = os.path.join(conf.CWD_PATH, args.dur_tree_dir)

        # GV checking
        conf.use_gv = args.gv_dir
        conf.hts_file_pathes["gv"] = args.gv_dir
    else:
        conf.project_path = os.path.dirname(args.config_fname)
        conf.hts_file_pathes["cmp_model"] = os.path.join(conf.project_path, "models/re_clustered_cmp.mmf")
        conf.hts_file_pathes["dur_model"] = os.path.join(conf.project_path, "models/re_clustered_dur.mmf")
        conf.hts_file_pathes["full_list"] = os.path.join(conf.project_path, "full.list")
        conf.hts_file_pathes["cmp_tree"]  =   os.path.join(conf.project_path, "trees")
        conf.hts_file_pathes["dur_tree"]  =   os.path.join(conf.project_path, "trees")

        conf.use_gv = False
        if (os.path.isdir(os.path.join(conf.project_path, "gv"))):
            conf.use_gv = True
            conf.hts_file_pathes["gv"] = os.path.join(conf.project_path, "gv")

    # Out directory
    out_path = os.path.join(conf.CWD_PATH, args.output)


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

    generate_label_list(conf, gen_labfile_lst)

    # Parameter generation
    parameter_generator = generation.generateGenerator(conf, out_handle, logger, args.is_parallel, args.preserve_intermediate)
    parameter_generator.generate(out_path, gen_labfile_list_fname, conf.use_gv)

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
