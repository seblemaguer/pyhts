#!/usr/bin/env python3
#-*- coding: utf-8 -*-

"""Usage: synth.py [-h] [-v] (--config=CONFIG) [--input_is_list] [--pg_type=PG_TYPE]
                   [--nb_proc=NB_PROC] [--preserve] [--imposed_duration]
                   [--renderer RENDERER] [--generator GENERATOR]
                   [--impose_f0_dir=F0] [--impose_mgc_dir=MGC] [--impose_bap_dir=BAP]
                   [--impose_interpolated_f0_dir=INT_F0] [--straight_path=STRAIGHT]
                   <input> <output>

Arguments:
  input                                           the input file (label by default but can be a list of files)
  output                                          the output directory

Options:
  -h --help                                       Show this help message and exit.
  -v --verbose                                    Verbose output.
  -c CONFIG --config=CONFIG                       Configuration file.
  -s --input_is_list                              the input is a scp formatted file.
  -p PG_TYPE --pg_type=PG_TYPE                    parameter generation type [default: 0].
  -P NB_PROC --nb_proc=NB_PROC                    Activate parallel mode [default: 1].
  -r --preserve                                   not delete the intermediate and temporary files.
  -D --imposed_duration                           imposing the duration at a phone level.
  -R RENDERER --renderer=RENDERER                 override the renderer
  -G GENERATOR --generator=GENERATOR              override the generator
  -M MGC --impose_mgc_dir=MGC                     MGC directory to use at the synthesis level.
  -B BAP --impose_bap_dir=BAP                     BAP directory to use at the synthesis level.
  -F F0 --impose_f0_dir=F0                        F0 directory to use at the synthesis level.
  -I INT_F0 --impose_interpolated_f0_dir=INT_F0   interpolated F0 directory to use at the synthesis level.
  -S STRAIGHT --straight_path=STRAIGHT            the path of the straight scripts

DESCRIPTION

    **TODO** This describes how to use this script. This docstring
        will be printed by the script if there is an error or
        if the user requests help (-h or --help).

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
from docopt import docopt

import os
import sys
import traceback
import argparse as ap

import time
import subprocess       # Shell command calling
import re
import logging
import shutil

from shutil import copyfile # For copying files
from pyhts_configuration import Configuration
import numpy as np
import rendering
import generation

################################################################################
### Utils
################################################################################
def copy_imposed_files(_in_path, _out_path, gen_labfile_base_lst, ext):
    """Helper to copy the imposed files listed in gen_labfile_base_lst whose extension is ext from _in_path to _out_path
    """
    for base in gen_labfile_base_lst:
        logger.info("copy %s/%s.%s to %s/%s.%s" % (_in_path, base, ext, _out_path, base, ext))
        copyfile("%s/%s.%s" % (_in_path, base, ext),
                 "%s/%s.%s" %  (_out_path, base, ext))

def adapt_f0_files(_in_path, _out_path, gen_labfile_base_lst, ext):
    """Helper to copy the imposed files listed in gen_labfile_base_lst whose extension is ext from _in_path to _out_path.
    This helper is specific to F0 as the voicing mask of the F0 predicted by HTS is also applied.
    """
    for base in gen_labfile_base_lst:
        logger.info("copy %s/%s.%s to %s/%s.%s" % (_in_path, base, ext, _out_path, base, ext))
        # Retrieve mask
        mask = np.fromfile("%s/%s.%s" % (_out_path, base, ext), dtype=np.float32)

        # Retrieve F0
        lf0 = np.fromfile("%s/%s.%s" % (_in_path, base, ext), dtype=np.float32)
        for i in range(0, min(lf0.size, mask.size)):
            if mask[i] == -1e10: # FIXME: only log supported for now
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

    conf = Configuration(args)


    # Out directory
    out_path = os.path.join(conf.CWD_PATH, args["<output>"])

    # Create output directory if none, else pass
    try:
        os.mkdir(out_path)
    except OSError:
        pass

    # 0. Generate list file
    gen_labfile_list_fname = conf.TMP_GEN_LABFILE_LIST_FNAME
    if args["--input_is_list"]:
        gen_labfile_list_fname = args["<input>"]
    else:
        with open(gen_labfile_list_fname, 'w') as f:
            f.write(args["<input>"] + '\n')

    gen_labfile_base_lst = []
    gen_labfile_lst = []
    with open(gen_labfile_list_fname) as f:
        for line in f:
            gen_labfile_lst.append(line.strip())
            gen_labfile_base_lst.append(os.path.splitext(os.path.basename(line.strip()))[0])

    generate_label_list(conf, gen_labfile_lst)

    # Parameter generation
    parameter_generator = generation.generateGenerator(conf, out_handle, logger,
                                                       int(args["--nb_proc"]), args["--preserve"])
    parameter_generator.generate(out_path, gen_labfile_list_fname, conf.use_gv)

    # 5. Convert/adapt parameters
    if args["--impose_f0_dir"] and args["--impose_interpolated_f0_dir"]:
        raise Exception("cannot impose 2 kind of F0 at the same time")

    if args["--impose_f0_dir"]:
        logger.info("replace f0 using imposed one")
        copy_imposed_files(args["--impose_f0_dir"], out_path, gen_labfile_base_lst, "lf0")
    if args["--impose_interpolated_f0_dir"]:
        logger.info("replace f0 using interpolated one")
        adapt_f0_files(args["--impose_interpolated_f0_dir"], out_path, gen_labfile_base_lst, "lf0")
    if args["--impose_bap_dir"]:
        copy_imposed_file(args["--impose_mgc_dir"], out_path, gen_labfile_base_lst, "mgc")
    if args["--impose_bap_dir"]:
        copy_imposed_file(args["--impose_bap_dir"], out_path, gen_labfile_base_lst, "bap")

    # 6. Call straight to synthesize
    renderer = rendering.generateRenderer(conf, out_handle, logger,
                                          int(args["--nb_proc"]), args["--preserve"])
    renderer.render(out_path, gen_labfile_base_lst)


    if not args["--preserve"]:
        shutil.rmtree(conf.TMP_PATH)

################################################################################
### Enveloping
################################################################################

if __name__ == '__main__':
    try:
        args = docopt(__doc__)

        # Debug time
        logger = setup_logging(args["--verbose"])
        if args["--verbose"]:
            out_handle = sys.stdout
        else:
            out_handle = subprocess.DEVNULL

        # Debug time
        start_time = time.time()
        if args["--verbose"]:
            logger.debug(time.asctime())

        # Running main function <=> run application
        main()

        # Debug time
        if args["--verbose"]:
            logger.debug(time.asctime())
        if args["--verbose"]:
            logger.debug("TOTAL TIME IN MINUTES: %f" % ((time.time() - start_time) / 60.0))

    except KeyboardInterrupt as e:  # Ctrl-C
        raise e

    except SystemExit as e:  # sys.exit()
        print("ERROR, UNEXPECTED EXCEPTION")
        print(str(e))
        traceback.print_exc()
        # os._exit(1)
        sys.exit(1)
    except Exception as e:
        print("ERROR, UNEXPECTED EXCEPTION")
        print(str(e))
        traceback.print_exc()
        # os._exit(1)
        sys.exit(1)
