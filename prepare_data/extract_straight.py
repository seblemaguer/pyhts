#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SYNOPSIS

    extract_straight [-h,--help] [-v,--verbose] [--version]

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
import bitstring
from bitstring import ConstBitStream
import numpy
import subprocess
from subprocess import call, Popen # For running external commands
import math
import string
import sys, os, traceback, optparse
import time
import re
import logging
#from pexpect import run, spawn


FNULL = open(os.devnull, 'w') # dev/null handler constant

################################################################################
### Extraction functions
################################################################################
def extractStraight(wav_dir, sp_dir, f0_dir, ap_dir):
    """
    Extract STRAIGHT coefficients to their respective directories
    """
    global configuration, logger

    logger.info("START STRAIGHT EXTRACTION")
    
    frameshift_ms = float(configuration.get("extract", "frameshift")) / float(configuration.get("extract", "sampfreq")) * 1000

    # Generate script header
    script_content = """
addpath('%s');
prm.F0frameUpdateInterval = %f;
prm.F0searchUpperBound = %s;
prm.F0searchLowerBound = %s;
prm.spectralUpdateInterval = %f;
    
    """ % (configuration.get("tools", "straight"),
           frameshift_ms,
           configuration.get("f0", "upperf0"),
           configuration.get("f0", "lowerf0"),
           frameshift_ms)

    # Generate script content
    for wav_fn in glob.iglob(wav_dir + "/*.wav"):
        base = os.path.basename(wav_fn)[:-4]
        sp_fn = sp_dir + "/" + base + ".sp"
        ap_fn = ap_dir + "/" + base + ".ap"
        f0_fn = f0_dir + "/" + base + ".f0"

        script_content += """
fprintf(1,'Processing %s\\n');
[x, fs] = wavread('%s');
[f0, ap] = exstraightsource(x, fs, prm);
[sp] = exstraightspec(x, f0, fs, prm);
ap = ap';
sp = sp';

f = fopen('%s', 'wb'); fwrite(f, sp, 'float'); fclose(f);
f = fopen('%s', 'wb'); fwrite(f, f0, 'float'); fclose(f);
f = fopen('%s', 'wb'); fwrite(f, ap, 'float'); fclose(f);
        """ % (wav_fn, wav_fn, sp_fn, f0_fn, ap_fn);
        
    # Save script
    if not os.path.isdir(configuration.get("directories", "script_dir")):
        os.mkdir(configuration.get("directories", "script_dir"))
    f_script = open(configuration.get("directories", "script_dir") + "/extract_straight.m", "w")
    f_script.write(script_content)
    f_script.close()
    
    # Execute matlab
    if not os.path.isdir(sp_dir):
        os.mkdir(sp_dir)
        os.mkdir(f0_dir)
        os.mkdir(ap_dir)

    f_script = open(configuration.get("directories", "script_dir") + "/extract_straight.m")
    try:
        call(["matlab", "-nodisplay", "-nosplash", "-nojvm"], stdin=f_script, stdout=FNULL)
    finally:
        f_script.close()

    logger.info("END STRAIGHT EXTRACTION")
    
def sp2mgc(sp_dir, mgc_dir):
    """
    Generate MGC coefficients from the spectrum extracted by STRAIGHT
    """
    global configuration, logger
    
    logger.info("START SP2MGC CONVERSION")
    
    # Create directory
    if not os.path.isdir(mgc_dir):
        os.mkdir(mgc_dir)
        
    sampfreq_khz = int(configuration.get("extract", "sampfreq")) * 0.001 

    for sp_fn in glob.iglob(sp_dir + "/*.sp"):
        base = os.path.basename(sp_fn)[:-4]
        mgc_fn = mgc_dir + "/" + base + ".mgc"

        logger.debug("convert %s ...." % sp_fn)
        
        cmd_mgcep = ["mgcep",
               "-a " + configuration.get("mgc", "freqwarp"),
               "-m " + configuration.get("mgc", "order"),
               "-l 2048 -e 1.0E-08 -j 0 -f 0.0 -q 3" # FIXME: constants
              ]
        if int(configuration.get("mgc", "gamma")) != 0:
            cmd_mgcep += ["-o 4 "]  # FIXME: constants
            cmd_lpc2lsp = ["lpc2lsp",
                           "-n 2048 -p 8 -d 1.0E-08", # FIXME: constants
                           "-m " + configuration.get("mgc", "order"),
                           "-s " + str(sampfreq_khz)
                           ]
            if int(configuration.get("mgc", "lngain")) == 1:
                cmd_lpc2lsp += ["-l"]

            #cmd += ["> " + mgc_fn]


        f_sp = open(sp_fn)
        f_mgc = open(mgc_fn, "w")
        try:
            call(string.join(cmd_mgcep), shell=True, stdin=f_sp, stdout=f_mgc)
                
        except Exception:
            logger.error(traceback.format_exc())
        finally:
            f_sp.close()
            f_mgc.close()
    logger.info("END SP2MGC CONVERSION")
    
def f02lf0(f0_dir, lf0_dir):
    """
    Convert F0 to the log scale
    """
    global configuration, logger
    
    logger.info("START F02LF0 CONVERSION")
    
    # Create directory
    if not os.path.isdir(lf0_dir):
        os.mkdir(lf0_dir)

    for f0_fn in glob.iglob(f0_dir + "/*.f0"):
        base = os.path.basename(f0_fn)[:-4]
        logger.debug("convert %s ...." % f0_fn)
        lf0_fn = lf0_dir + "/" + base + ".lf0"

        f_in = open(f0_fn, "rb")
        raw_data = ConstBitStream(f_in)
        f_in.close()

        float_num = raw_data.readlist('floatle:32')
        f_out = open(lf0_fn, "wb")
        try:
            while True:
                if float_num[0] == 0:
                    float_num = numpy.float32(-1e+10)
                else:
                    float_num = numpy.float32(math.log(float_num[0]))
                f_out.write(float_num)
                float_num = raw_data.readlist('floatle:32')
        except bitstring.ReadError:
            pass
        finally:
            f_out.close()
            
    logger.info("END F02LF0 CONVERSION")
    
def ap2bap(ap_dir, bap_dir):
    """
    Generate band values from the aperiodicity extracted by STRAIGHT
    """
    global configuration, logger
    
    logger.info("START AP2BAP CONVERSION")
    
    # Create directory
    if not os.path.isdir(bap_dir):
        os.mkdir(bap_dir)

    for ap_fn in glob.iglob(ap_dir + "/*.ap"):
        base = os.path.basename(ap_fn)[:-4]
        bap_fn = bap_dir + "/" + base + ".bap"

        logger.debug("convert %s ...." % bap_fn)
        
        f_ap = open(ap_fn)
        f_bap = open(bap_fn, "w")

        try:
            cmd = ["mgcep",
                "-a", configuration.get("mgc", "freqwarp"),
                "-m", configuration.get("bap", "order"),
                # FIXME: constants
                "-l",  "2048",  "-e",  "1.0E-08",  "-j",  "0",  "-f",  "0.0",  "-q",  "1"]
            call(cmd, shell=True, stdout=f_bap, stdin=f_ap)
        except Exception:
            # FIXME: message
            logger.error(traceback.format_exc())
        finally:
            f_ap.close()
            f_bap.close()
            
    logger.info("END AP2BAP CONVERSION")
    


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
    data_dir = configuration.get("directories", "root") + "/" + configuration.get("directories", "data_dir")

    # STRAIGHT coefficient extraction
    extractStraight(data_dir + "/" + configuration.get("directories", "wav_dir"),
                     data_dir + "/" + configuration.get("directories", "sp_dir"),
                     data_dir + "/" + configuration.get("directories", "f0_dir"),
                     data_dir + "/" + configuration.get("directories", "ap_dir"))

    # STRAIGHT coefficient conversion
    sp2mgc(data_dir + "/" + configuration.get("directories", "sp_dir"),
           data_dir + "/" + configuration.get("directories", "mgc_dir"))
    f02lf0(data_dir + "/" + configuration.get("directories", "f0_dir"),
           data_dir + "/" + configuration.get("directories", "lf0_dir"))
    ap2bap(data_dir + "/" + configuration.get("directories", "ap_dir"),
           data_dir + "/" + configuration.get("directories", "bap_dir"))
    

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
