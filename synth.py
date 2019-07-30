#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <lemagues@tcd.ie>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 30 July 2019
"""

# System/default
import sys
import os
import shutil

# Arguments
import argparse

# Messaging/logging
import traceback
import time
import logging

# Regular expression
import re

# Math
import numpy as np

# Subpackages
from pyhts_configuration import Configuration
import rendering
import generation

# NOTE: get rid of stupid tensorflow warning
import absl.logging
logging.root.removeHandler(absl.logging._absl_handler)
absl.logging._warn_preinit_stderr = False


###############################################################################
# global constants
###############################################################################
LEVEL = [logging.WARNING, logging.INFO, logging.DEBUG]

###############################################################################
# Functions
###############################################################################

def copy_imposed_files(_in_path, _out_path, gen_labfile_base_lst, ext):
    """Helper to copy the imposed files listed in gen_labfile_base_lst whose extension is ext from _in_path to _out_path
    """
    for base in gen_labfile_base_lst:
        logger.info("copy %s/%s.%s to %s/%s.%s" % (_in_path, base, ext, _out_path, base, ext))
        shutil.copyfile("%s/%s.%s" % (_in_path, base, ext),
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

        # Applying mask!
        for i in range(0, min(lf0.size, mask.size)):
            if mask[i] == -1e10: # FIXME: only log supported for now
                lf0[i] = mask[i]

        # Finally save the F0
        lf0.tofile("%s/%s.%s" % (_out_path, base, ext))

def generate_label_list(conf, in_path, input_label_list):
    """
    Generate the label list file to get it through the tree
    """
    pattern = re.compile('[ \t]*([0-9]+)[ \t]+([0-9]+)[ \t]+(.*)')
    full_set = set()

    # Fullcontext list (Training + generation)
    for input_label in input_label_list:
        with open("%s/%s.lab" % (in_path, input_label)) as lab_file:
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

###############################################################################
# Main function
###############################################################################
def main():
    """Main entry function
    """
    global args

    conf = Configuration(args)

    # Out directory
    in_path = args.input
    out_path = os.path.join(conf.CWD_PATH, args.output)

    # Create output directory if none, else pass
    try:
        os.mkdir(out_path)
    except OSError:
        pass

    # 0. Generate list file
    gen_labfile_base_lst = []
    for r, d, f in os.walk(in_path):
        for file in f:
            if '.lab' in file:
                tmp = os.path.join(r, file).replace(".lab", "").replace(in_path, "")
                tmp = re.sub(r"^/", "", tmp)
                gen_labfile_base_lst.append(tmp)
                logger.info("Add %s" % file)
    if conf.generator.upper() != "NONE":
        generate_label_list(conf, in_path, gen_labfile_base_lst)

    # Parameter generation
    parameter_generator = generation.generateGenerator(conf, int(args.nb_proc), args.preserve)
    parameter_generator.generate(in_path, out_path, gen_labfile_base_lst, conf.use_gv)

    # 5. Convert/adapt parameters
    if (args.impose_f0_dir is not None) and (args.impose_interpolated_f0_dir  is not None):
        raise Exception("cannot impose 2 kind of F0 at the same time")

    if args.impose_f0_dir is not None:
        logger.info("replace f0 using imposed one")
        copy_imposed_files(args.impose_f0_dir, out_path, gen_labfile_base_lst, "lf0")
    if args.impose_interpolated_f0_dir is not None:
        logger.info("replace f0 using interpolated one")
        adapt_f0_files(args.impose_interpolated_f0_dir, out_path, gen_labfile_base_lst, "lf0")
    if args.impose_bap_dir is not None:
        copy_imposed_files(args.impose_mgc_dir, out_path, gen_labfile_base_lst, "mgc")
    if args.impose_bap_dir is not None:
        copy_imposed_files(args.impose_bap_dir, out_path, gen_labfile_base_lst, "bap")

    # 6. Call straight to synthesize
    renderer = rendering.generateRenderer(conf, int(args.nb_proc), args.preserve)
    renderer.render(in_path, out_path, gen_labfile_base_lst)

    # if not args["--preserve"]:
    #     shutil.rmtree(conf.TMP_PATH)


###############################################################################
#  Envelopping
###############################################################################
if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description="")

        # Add options
        parser.add_argument("-c", "--config", required=True,
                            help="Configuration file")
        parser.add_argument("-p", "--pg-type", default=0, type=int,
                            help="The parameter generation type (0, 1 or 2!)")
        parser.add_argument("-P", "--nb_proc", default=1, type=int,
                            help="The number of parallel processes authorized")
        parser.add_argument("-r", "--preserve", action="store_true",
                            help="Preserve the intermediate and temporary files")
        parser.add_argument("-D", "--imposed_duration", action="store_true",
                            help="Impose the duration at the phone level. (duration should be in the input label file)")
        parser.add_argument("-R", "--renderer", type=str, default=None,
                            help="Override the configuration renderer")
        parser.add_argument("-G", "--generator", type=str, default=None,
                            help="Override the configuration generator")

        parser.add_argument("-M", "--impose_mgc_dir", type=str, default=None,
                            help="MGC directory to use at the rendering stage")
        parser.add_argument("-B", "--impose_bap_dir", type=str, default=None,
                            help="BAP directory to use at the rendering stage")
        parser.add_argument("-F", "--impose_f0_dir", type=str, default=None,
                            help="F0 directory to use at the rendering stage")
        parser.add_argument("-I", "--impose_interpolated_f0_dir", type=str, default=None,
                            help="Interpolated F0 directory to use at the rendering stage")

        parser.add_argument("-S", "--straight_path", type=str, default=None,
                            help="Overriding configuration path to the STRAIGHT toolkit")

        parser.add_argument("-l", "--log_file", default=None, type=str,
                            help="Logger file")
        parser.add_argument("-v", "--verbosity", action="count", default=0,
                            help="increase output verbosity")

        # Add arguments
        parser.add_argument("input", help="The input file/directory")
        parser.add_argument("output", help="The output directory")

        # Parsing arguments
        args = parser.parse_args()

        # create logger and formatter
        logger = logging.getLogger()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Verbose level => logging level
        log_level = args.verbosity
        if (args.verbosity >= len(LEVEL)):
            log_level = len(LEVEL) - 1
            logger.setLevel(log_level)
            logging.warning("verbosity level is too high, I'm gonna assume you're taking the highest (%d)" % log_level)
        else:
            logger.setLevel(LEVEL[log_level])

        # create console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # create file handler
        if args.log_file is not None:
            fh = logging.FileHandler(args.log_file)
            logger.addHandler(fh)

        # Debug time
        start_time = time.time()
        logger.info("start time = " + time.asctime())

        # Running main function <=> run application
        main()

        # Debug time
        logging.info("end time = " + time.asctime())
        logging.info('TOTAL TIME IN MINUTES: %02.2f' %
                     ((time.time() - start_time) / 60.0))

        # Exit program
        sys.exit(0)
    except KeyboardInterrupt as e:  # Ctrl-C
        raise e
    except SystemExit:  # sys.exit()
        pass
    except Exception as e:
        logging.error('ERROR, UNEXPECTED EXCEPTION')
        logging.error(str(e))
        traceback.print_exc(file=sys.stderr)
        sys.exit(-1)
