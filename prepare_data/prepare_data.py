#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SYNOPSIS

    prepare_data [-h,--help] [-v,--verbose] [--version]

DESCRIPTION

    TODO This describes how to use this script. This docstring
    will be printed by the script if there is an error or
    if the user requests help (-h or --help).

EXAMPLES

    TODO: Show some examples of how to use this script.

EXIT STATUS

    TODO: List exit codes

AUTHOR

    Sébastien Le Maguer <Sebastien.Le_maguer@irisa.fr>

LICENSE

    This script is in the public domain, free from copyrights or restrictions.

VERSION

    $Id$
"""

import glob                        # For listing all *.XXX files
import ConfigParser                # For configuration file management
import numpy                       # Vector processing (dynamic computation pre-requisite)
from os import listdir
from os.path import isfile, join   # list only files
import sys, os, traceback, optparse
import time
import re
import logging
#from pexpect import run, spawn

################################################################################
### Util functions
################################################################################

def getDynamics(coef):
    """
    Compute the dynamic parts and concatenate it to the static part to get the observation vector
    """
    global configuration
    pass


################################################################################
### Generate composite file
################################################################################
def generateCMP():
    """
    Generate the CMP file which contains observations in the HTS compatible format
    """
    global configuration
    pass

################################################################################
### Generate lists
################################################################################

def generateMLF():
    """
    Generate the MLF Files
    """
    global configuration
    lab_dir = "%s/%s/%s" % (configuration.get("directories", "root"),
                            configuration.get("directories", "data_dir"),
                            configuration.get("directories", "lab_dir"))
    
    f = open("%s/mono.mlf" % lab_dir, "w")
    f.write("\"*/*.lab\" -> \"%s/%s\"" % (os.path.abspath(lab_dir),
                                          configuration.get("directories",
                                                            "mono_lab_dir")))
    f.close()

    f = open("%s/full.mlf" % lab_dir, "w")
    f.write("\"*/*.lab\" -> \"%s/%s\"" % (os.path.abspath(lab_dir),
                                          configuration.get("directories",
                                                            "full_lab_dir")))
    f.close()

def generateList():
    """
    Generate the list files
    """
    global configuration
    lab_dir = "%s/%s/%s" % (configuration.get("directories", "root"),
                            configuration.get("directories", "data_dir"),
                            configuration.get("directories", "lab_dir"))
    
    mono_dir = "%s/%s" % (os.path.abspath(lab_dir),
                          configuration.get("directories",
                                            "mono_lab_dir"))
    
    full_dir = "%s/%s" % (os.path.abspath(lab_dir),
                          configuration.get("directories",
                                            "full_lab_dir"))
    
    gen_dir = "%s/%s" % (os.path.abspath(lab_dir),
                          configuration.get("directories",
                                            "gen_lab_dir"))
    # FIXME: add cmp checking
    
    mono_lab = [ f for f in listdir(mono_dir) if isfile(join(full_dir,f)) ]
    full_lab = [ f for f in listdir(full_dir) if isfile(join(full_dir,f)) ]
    gen_lab = [ f for f in listdir(gen_dir) if isfile(join(gen_dir,f)) ]
    
    list_dir = "%s/%s/%s" % (configuration.get("directories", "root"),
                            configuration.get("directories", "data_dir"),
                            configuration.get("directories", "list_dir"))
    
    if not os.path.isdir(list_dir):
        os.mkdir(list_dir)
    inters = set(mono_lab)
    inters.intersection_update(full_lab)

    p = re.compile('[ \t]+')

    # Monophone list
    mono_set = set()
    for f in inters:
        with open("%s/%s" % (mono_dir, f)) as cur_lab_file:
            for cur_line in cur_lab_file:
                cur_line = cur_line.strip()
                lab = p.split(cur_line)[2]
                mono_set.add(lab)
                # mono_set.add(.split(" ").split("\t"))

    with open('%s/mono.list' % list_dir, 'w') as f_list:
        f_list.write("\n".join(mono_set))

    # Fullcontext list (Training)
    full_set = set()
    for f in inters:
        with open("%s/%s" % (full_dir, f)) as cur_lab_file:
            for cur_line in cur_lab_file:
                cur_line = cur_line.strip()
                lab = p.split(cur_line)[2]
                full_set.add(lab)
                # full_set.add(.split(" ").split("\t"))
                
    with open('%s/full.list' % list_dir, 'w') as f_list:
        f_list.write("\n".join(full_set))

    # Fullcontext list (Training + generation)
    for f in gen_lab:
        with open("%s/%s" % (gen_dir, f)) as cur_lab_file:
            for cur_line in cur_lab_file:
                cur_line = cur_line.strip()
                lab = p.split(cur_line)[2]
                full_set.add(lab)
                # full_set.add(.split(" ").split("\t"))

                
    with open('%s/full_all.list' % list_dir, 'w') as f_list:
        f_list.write("\n".join(full_set))
################################################################################
### Configuration loading and logging setup functions
################################################################################
def loadConfiguration(conf_file):
    """
    Loading the configuration file conf_file
    """
    global configuration

    configuration = ConfigParser.SafeConfigParser()
    configuration.read(conf_file)
    
def setupLogging(is_verbose):
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


    logger = logging.getLogger("EXTRACT_STRAIGHT")
    logger.setLevel(level)

    return logger

################################################################################
### Main function
################################################################################
def main():
    """Main entry function
    """
    global options, args

    # Init
    loadConfiguration(args[0])


    # Data part
    data_dir = configuration.get("directories", "root") + "/" + configuration.get("directories", "data_dir")
        
    # Labels part
    generateMLF()
    generateList()

################################################################################
### Main part encapsulation
################################################################################
if __name__ == '__main__':
    try:
        parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(),
                                       usage=globals()['__doc__'],
                                       version='$Id$')
        parser.add_option('-v', '--verbose', action='store_true',
                          default=False, help='verbose output')
        (options, args) = parser.parse_args()

        logger = setupLogging(options.verbose)
        
         # Debug time
        start_time = time.time()
        if options.verbose: logger.debug(time.asctime())

        # Running main function <=> run application
        main()

        # Debug time
        if options.verbose: logger.debug(time.asctime())
        if options.verbose: logger.debug('TOTAL TIME IN MINUTES: %f' % ((time.time() - start_time) / 60.0))

        # Exit program
        sys.exit(0)
    except KeyboardInterrupt, e: # Ctrl-C
        raise e
    except SystemExit, e: # sys.exit()
        pass
    except Exception, e:
        print 'ERROR, UNEXPECTED EXCEPTION'
        print str(e)
        traceback.print_exc()
        os._exit(1)
