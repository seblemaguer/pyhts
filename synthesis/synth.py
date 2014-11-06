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

import sys
import traceback
import argparse as ap

import time
import subprocess       # Shell command calling
import re
import logging

from pyhts_const import *


################################################################################
### Config + script functions
################################################################################

def generate_label_list(input_label_list):
    """
    Generate the label list file to get it through the tree
    """
    pattern = re.compile('[ \t]+')
    full_set = set()

    # Fullcontext list (Training + generation)
    for input_label in input_label_list:
        with open(input_label) as lab_file:
            for line in lab_file:
                line = line.strip()
                lab = pattern.split(line)[2]
                full_set.add(lab)

    with open(LABEL_LIST_FNAME, 'w') as list_file:
        list_file.write('\n'.join(full_set))


def generate_training_configuration():
    """
    Generate 'training configuration' => needed for the tree search
    """
    # Training configuration
    with open(TRAIN_CONFIG, 'w') as f:
        f.write('NATURALREADORDER = T\n')
        f.write('NATURALWRITEORDER = T\n')

        # Variance floor options
        f.write('APPLYVFLOOR = T\n')
        f.write('VFLOORSCALESTR = "Vector %d' % (max([int(STRE[cur_type]) for cur_type in TYPE_MAP['CMP']])))
        for cur_type in TYPE_MAP['CMP']:
            f.write(' ')
            f.write(' '.join(['%s' % VFLR[cur_type]] * (int(STRE[cur_type]) - int(STRB[cur_type]) + 1)))

        f.write('"\n')
        f.write('APPLYDURVARFLOOR = T\n')
        f.write('DURVARFLOORPERCENTILE = %f\n' % (100 * float(VFLR['DUR'])))

        # Duration specific
        f.write('MAXSTDDEVCOEF = %s\n' % GEN['MAXDEV_HSMM'])
        f.write('MINDUR = %s\n' % GEN['MINDUR'])


def generate_synthesis_configuration(_use_gv):
    """
    Generate the synthesis configuration file needed by HMGenS
    """
    # Synthesis configuration

    # config file for parameter generation
    with open(SYNTH_CONFIG, 'w') as f:

        # Global parameters
        f.write('NATURALREADORDER = T\n')
        f.write('NATURALWRITEORDER = T\n')
        f.write('USEALIGN = T\n')
        f.write('MAXEMITER = %s\n' % GEN['MAXEMITER'])

        # Counting streams
        f.write('PDFSTRSIZE = "IntVec %d' % len(TYPE_MAP['CMP']))    # PdfStream structure
        for cur_type in TYPE_MAP['CMP']:
            f.write(' %d' % (int(STRE[cur_type]) - int(STRB[cur_type]) + 1))
        f.write('"\n')

        # Order of each coefficients
        f.write('PDFSTRORDER = "IntVec %d' % len(TYPE_MAP['CMP']))    # PdfStream structure
        for cur_type in TYPE_MAP['CMP']:
            f.write(' %s' % (ORDER[cur_type]))
        f.write('"\n')

        # Extension
        f.write('PDFSTREXT = "StrVec %d %s"\n' % (len(TYPE_MAP['CMP']), ' '.join(TYPE_MAP['CMP'])))

        # Windows
        f.write('WINFN = "')                                        # WINFN: Name of window coefficient files
        for cur_type in TYPE_MAP['CMP']:
            # FIXME in the middle of the source => move
            win_fnames = ' '.join('%s.win%d' % (cur_type, d) for d in range(1, int(NWIN[cur_type]) + 1))
            f.write(' StrVec %d %s' % (int(NWIN[cur_type]), win_fnames))
        f.write('"\n')
        f.write('WINDIR = %s\n' % WIN_PATH)

        # Global variance
        if _use_gv:
            f.write('EMEPSILON  = %f\n' % GEN['EMEPSILON'])
            f.write('USEGV      = TRUE\n')
            f.write('GVMODELMMF = %s\n' % TMP_GV_MMF)
            f.write('GVHMMLIST  = %s\n' % GV_TIED_LIST_TMP)
            f.write('MAXGVITER  = %d\n' % GEN['MAXGVITER'])
            f.write('GVEPSILON  = %f\n' % GEN['GVEPSILON'])
            f.write('MINEUCNORM = %f\n' % GEN['MINEUCNORM'])
            f.write('STEPINIT   = %f\n' % GEN['STEPINIT'])
            f.write('STEPINC    = %f\n' % GEN['STEPINC'])
            f.write('STEPDEC    = %f\n' % GEN['STEPDEC'])
            f.write('HMMWEIGHT  = %f\n' % GEN['HMMWEIGHT'])
            f.write('GVWEIGHT   = %f\n' % GEN['GVWEIGHT'])
            f.write('OPTKIND    = %s\n' % GEN['OPTKIND'])

            f.write('GVOFFMODEL = "StrVec %d %s"\n' % (len(SLNT), ' '.join(SLNT)))
            if GV['CDGV']:
                f.write('CDGV = TRUE\n')
            else:
                f.write('CDGV = FALSE\n')
        else:
            f.write('USEGV      = FALSE\n')


def mk_unseen_script(_cmp_tree_path, _dur_tree_path, _use_gv, gv_dir=None):
    """
    Generate hed
    """
    # Generate GV script
    if _use_gv:
        with open(GV_HED_UNSEEN_BASE + '.hed', 'w') as f:
            f.write('\nTR 2\n\n')

            # Load trees
            f.write('// Load trees\n')
            for cur_type in TYPE_MAP['CMP']:
                f.write('LT "%s/%s.inf"\n\n' % (gv_dir, cur_type))

            # Make unseen
            f.write('// Make unseen\n')
            f.write('AU "%s"\n\n' % LABEL_LIST_FNAME)

            # Compact model
            f.write('// Compact\n')
            f.write('CO "%s"\n\n' % GV_TIED_LIST_TMP)

    # CMP
    with open('%s_cmp.hed' % TYPE_HED_UNSEEN_BASE, 'w') as f:
        f.write('\nTR 2\n\n')

        # Load trees
        f.write('// Load trees\n')
        for cur_type in TYPE_MAP['CMP']:
            f.write('LT "%s/%s.inf.untied"\n\n' % (_cmp_tree_path, cur_type))

        # Make unseen
        f.write('// Make unseen\n')
        f.write('AU "%s"\n\n' % LABEL_LIST_FNAME)

        # Compact model
        f.write('// Compact\n')
        f.write('CO "%s_cmp"\n\n' % TYPE_TIED_LIST_BASE)

    # DUR
    with open('%s_dur.hed' % TYPE_HED_UNSEEN_BASE, 'w') as f:
        f.write('\nTR 2\n\n')

        # Load trees
        f.write('// Load trees\n')
        f.write('LT "%s/dur.inf"\n\n' % _dur_tree_path)

        # Make unseen
        f.write('// Make unseen\n')
        f.write('AU "%s"\n\n' % LABEL_LIST_FNAME)

        # Compact model
        f.write('// Compact\n')
        f.write('CO "%s_dur"\n\n' % TYPE_TIED_LIST_BASE)


################################################################################
### Parameter transformation function
################################################################################

# TODO : add post-filtering functions
# def post_filtering_mcp(base, _out_path):
#     """
#     """
#     str_pf_mcp = '%f' % SIGNAL['PF_MCP']
#     cmd = 'echo 1 1 %s | x2x +af > %s/weights' % (' '.join([str_pf_mcp] * ORDER['MGC']), _out_path)

#     # TODO: finish but not needed for the moment
#     pass

#     # # Clean
#     # os.remove('%s/weights' % _out_path)


def parameter_conversion(_out_path, gen_labfile_base_lst):
    """
    Convert parameter to STRAIGHT params
    """
    for base in gen_labfile_base_lst:
        # lf0 => f0
        cmd = '%s -magic -1.0E+10 -EXP -MAGIC 0.0 %s/%s.lf0' % \
            (SOPR, _out_path, base)
        with open('%s/%s.f0' % (_out_path, base), 'w') as f:
            subprocess.call(cmd.split(), stdout=f)

        # bap => aperiodicity
        cmd = '%s -a %f -g 0 -m %d -l 2048 -o 0 %s/%s.bap' % \
            (MGC2SP, FREQWARPING, int(ORDER['BAP'])-1, _out_path, base)
        with open('%s/%s.ap' % (_out_path, base), 'w') as f:
            subprocess.call(cmd.split(), stdout=f)

        # mgc => spectrum
        cmd = '%s -a %f -g %f -m %d -l 2048 -o 2 %s/%s.mgc' % \
            (MGC2SP, float(FREQWARPING), float(SIGNAL['GAMMA']), int(ORDER['MGC'])-1, _out_path, base)
        with open('%s/%s.sp' % (_out_path, base), 'w') as f:
            subprocess.call(cmd.split(), stdout=f)
        # FIXME: include int(), float()... in the pyhts_const.py (or change %d, %f... in %s)

        # # Clean [TODO: do with options]
        # os.remove('%s/%s.lf0' % (_out_path, base))
        # os.remove('%s/%s.mgc' % (_out_path, base))
        # os.remove('%s/%s.bap' % (_out_path, base))
        # os.remove('%s/%s.dur' % (_out_path, base))     # TODO : must be an option in the synth config


def straight_generation(_out_path, gen_labfile_base_lst):
    """
    """
    # Generate STRAIGHT script
    with open(STRAIGHT_SCRIPT, 'w') as f:
        # Header
        f.write("path(path, '%s');\n" % PATH['STRAIGHT'])
        f.write("prm.spectralUpdateInterval = %f;\n" % float(SIGNAL['FRAMESHIFT_MS']))
        f.write("prm.levelNormalizationIndicator = 0;\n\n")

        # Read STRAIGHT params
        for base in gen_labfile_base_lst:
            f.write("fid_sp = fopen('%s/%s.sp', 'r', 'ieee-le');\n" % (_out_path, base))
            f.write("fid_ap = fopen('%s/%s.ap', 'r', 'ieee-le');\n" % (_out_path, base))
            f.write("fid_f0 = fopen('%s/%s.f0', 'r', 'ieee-le');\n" % (_out_path, base))

            nb_frames = os.path.getsize('%s/%s.f0' % (_out_path, base)) / 4
            f.write("sp = fread(fid_sp, [%d %d], 'float');\n" % (1025, nb_frames))
            f.write("ap = fread(fid_ap, [%d %d], 'float');\n" % (1025, nb_frames))
            f.write("f0 = fread(fid_f0, [%d %d], 'float');\n" % (1, nb_frames))

            f.write("fclose(fid_sp);\n")
            f.write("fclose(fid_ap);\n")
            f.write("fclose(fid_f0);\n")

            # Spectrum normalisation # FIXME (why ?) => not compatible with our corpus podalydes
            # f.write("sp = sp * %f;\n" % (1024.0 / (2200.0 * 32768.0)))

            # Synthesis process part 2
            f.write("[sy] = exstraightsynth(f0, sp, ap, %d, prm);\n" % int(SAMPLERATE))
            f.write("wavwrite(sy, %d, '%s/%s.wav');\n" % (int(SAMPLERATE), _out_path, base))

        # Ending
        f.write("quit;\n")

    # Synthesis!
    cmd = '%s -nojvm -nosplash -nodisplay < %s' % (MATLAB, STRAIGHT_SCRIPT)
    subprocess.call(cmd.split(), stdout=out_handle)

    # # Clean  [TODO: do with options]
    # os.remove(STRAIGHT_SCRIPT)
    # for base in gen_labfile_base_lst:
    #     os.remove('%s/%s.sp' % (_out_path, base))
    #     os.remove('%s/%s.ap' % (_out_path, base))
    #     os.remove('%s/%s.f0' % (_out_path, base))


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
    # Create output directory if none, else pass
    try:
        os.mkdir(out_path)
    except FileExistsError:
        pass

    # 0. Generate list file
    gen_labfile_list_fname = TMP_GEN_LABFILE_LIST_FNAME
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

    # 2. Generate scripts
    mk_unseen_script(cmp_tree_path, dur_tree_path, use_gv, args.gv_dir)

    # 3. Compose models
    #    * CMP
    logger.info("CMP unseen model building")
    cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
        (HHEd, TRAIN_CONFIG, cmp_model_fpath, TMP_CMP_MMF, TYPE_HED_UNSEEN_BASE+'_cmp.hed', full_list_fpath)
    subprocess.call(cmd.split(), stdout=out_handle)
    #    * DUR
    logger.info("Duration unseen model building")
    cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
        (HHEd, TRAIN_CONFIG, dur_model_fpath, TMP_DUR_MMF, TYPE_HED_UNSEEN_BASE+'_dur.hed', full_list_fpath)
    subprocess.call(cmd.split(), stdout=out_handle)
    
    #    * GV
    if use_gv:
        logger.info("Global variance unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
            (HHEd, TRAIN_CONFIG, args.gv_dir+'/clustered.mmf', TMP_GV_MMF, GV_HED_UNSEEN_BASE+'.hed',
             args.gv_dir+'/gv.list')
        subprocess.call(cmd.split(), stdout=out_handle)
        # FIXME: change directory to file (args.gv_dir+'/clustered.mmf')

    # 4. Generate parameters
    logger.info("Parameter generation")
    cmd = '%s -A -B -C %s -D -T 1 -S %s -t %s -c %d -H %s -N %s -M %s %s %s' % \
        (HMGenS, SYNTH_CONFIG, gen_labfile_list_fname, HMM['BEAM_STEPS'], int(args.pg_type), TMP_CMP_MMF, TMP_DUR_MMF,
         out_path, TYPE_TIED_LIST_BASE+'_cmp', TYPE_TIED_LIST_BASE+'_dur')
    subprocess.call(cmd.split(), stdout=out_handle)

    # 5. Call straight to synthesize
    logger.info("Parameter conversion (could be quite long)")
    parameter_conversion(out_path, gen_labfile_base_lst)
    
    logger.info("Audio rendering (could be quite long)")
    straight_generation(out_path, gen_labfile_base_lst)


################################################################################
### Enveloping
################################################################################

if __name__ == '__main__':
    try:
        argp = ap.ArgumentParser(description=globals()['__doc__'], formatter_class=ap.RawDescriptionHelpFormatter)

        # argp.add_argument('--version', action='version', version='$Id$')
        argp.add_argument('-v', '--verbose', action='store_true',
                          default=False, help='verbose output')

        # models
        argp.add_argument('-m', '--cmp', dest='cmp_model_fname', required=True,
                          help="CMP model file", metavar='FILE')
        argp.add_argument('-d', '--dur', dest='dur_model_fname', required=True,
                          help="Duration model file", metavar='FILE')
        argp.add_argument('-l', '--list', dest='full_list_fname', required=True,
                          help="Label list training lab files", metavar='FILE')
        argp.add_argument('-t', '--cmp_tree', dest='cmp_tree_dir', required=True,
                          help="Directory which contains the coefficient trees")
        argp.add_argument('-u', '--dur_tree', dest='dur_tree_dir', required=True,
                          help="Directory which contains the duration tree")
        # Options
        argp.add_argument('-s', '--with_scp', dest='input_is_list', action='store_true',
                          default=False, help="the input is a scp formatted file")
        argp.add_argument('-g', '--gv', dest='gv_dir',
                          help="Define the global variance model directory")
        argp.add_argument('-p', '--pg_type', dest='pg_type',
                          help="Parameter generation type")
        # input/output
        argp.add_argument('-i', '--input', dest='input_fname', required=True,
                          help="Input lab file for synthesis", metavar='FILE')
        argp.add_argument('-o', '--output', dest='output', required=True,
                          help="Output wav directory", metavar='FILE')

        args = argp.parse_args()

        # PATHs
        cmp_model_fpath = os.path.join(CWD_PATH, args.cmp_model_fname)
        dur_model_fpath = os.path.join(CWD_PATH, args.dur_model_fname)
        full_list_fpath = os.path.join(CWD_PATH, args.full_list_fname)
        cmp_tree_path = os.path.join(CWD_PATH, args.cmp_tree_dir)
        dur_tree_path = os.path.join(CWD_PATH, args.dur_tree_dir)
        out_path = os.path.join(CWD_PATH, args.output)

        use_gv = args.gv_dir

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
