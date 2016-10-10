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

from shutil import copyfile # For copying files
from pyhts_configuration import Configuration
import numpy as np

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

        for cur_stream in conf.STREAMS:
            win = ""
            for w in cur_stream["winfiles"]:
                win = win + " %s/%s" % (conf.PROJECT_DIR, w)
            f.write(' StrVec %d%s' % (len(cur_stream["winfiles"]), win))
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


def mk_unseen_script(_cmp_tree_path, _dur_tree_path, _use_gv, gv_dir=None):
    """
    Generate hed
    """
    # Generate GV script
    if _use_gv:
        with open(conf.GV_HED_UNSEEN_BASE + '.hed', 'w') as f:
            f.write('\nTR 2\n\n')

            # Load trees
            f.write('// Load trees\n')
            for cur_stream in conf.STREAMS:
                f.write('LT "%s/%s.inf"\n\n' % (gv_dir, cur_stream["kind"]))

            # Make unseen
            f.write('// Make unseen\n')
            f.write('AU "%s"\n\n' % conf.LABEL_LIST_FNAME)

            # Compact model
            f.write('// Compact\n')
            f.write('CO "%s"\n\n' % conf.GV_TIED_LIST_TMP)

    # CMP
    with open('%s_cmp.hed' % conf.TYPE_HED_UNSEEN_BASE, 'w') as f:
        f.write('\nTR 2\n\n')
        # Load trees
        f.write('// Load trees\n')
        for cur_stream in conf.STREAMS:
            f.write('LT "%s/%s.%s"\n\n' % (_cmp_tree_path, cur_stream["kind"], conf.GEN["tree_ext"]))

        # Make unseen
        f.write('// Make unseen\n')
        f.write('AU "%s"\n\n' % conf.LABEL_LIST_FNAME)

        # Compact model
        f.write('// Compact\n')
        f.write('CO "%s_cmp"\n\n' % conf.TYPE_TIED_LIST_BASE)

    # DUR
    with open('%s_dur.hed' % conf.TYPE_HED_UNSEEN_BASE, 'w') as f:
        f.write('\nTR 2\n\n')

        # Load trees
        f.write('// Load trees\n')
        f.write('LT "%s/dur.%s"\n\n' % (_dur_tree_path, conf.GEN["tree_ext"]))

        # Make unseen
        f.write('// Make unseen\n')
        f.write('AU "%s"\n\n' % conf.LABEL_LIST_FNAME)

        # Compact model
        f.write('// Compact\n')
        f.write('CO "%s_dur"\n\n' % conf.TYPE_TIED_LIST_BASE)


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

        # bap => aperiodicity
        for cur_stream in conf.STREAMS:
            if cur_stream["kind"] == "lf0":
                # lf0 => f0
                cmd = '%s -magic -1.0E+10 -EXP -MAGIC 0.0 %s/%s.lf0' % \
                  (conf.SOPR, _out_path, base)
                with open('%s/%s.f0' % (_out_path, base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)
            elif cur_stream["kind"] == "bap":
                cmd = '%s -a %f -g 0 -m %d -l 2048 -o 0 %s/%s.bap' % \
                  (conf.MGC2SP, conf.FREQWARPING, cur_stream["order"], _out_path, base)
                with open('%s/%s.ap' % (_out_path, base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)
            elif cur_stream["kind"] == "mgc":
                # mgc => spectrum TODO
                cmd = '%s -a %f -g %f -m %d -l 2048 -o 2 %s/%s.mgc' % \
                  (conf.MGC2SP, conf.FREQWARPING, cur_stream['parameters']['gamma'], cur_stream["order"], _out_path, base)
                with open('%s/%s.sp' % (_out_path, base), 'w') as f:
                    subprocess.call(cmd.split(), stdout=f)

        # Clean [TODO: do with options]
        # os.remove('%s/%s.lf0' % (_out_path, base))
        os.remove('%s/%s.mgc' % (_out_path, base))
        os.remove('%s/%s.bap' % (_out_path, base))
        # os.remove('%s/%s.dur' % (_out_path, base))


def straight_generation(_out_path, gen_labfile_base_lst):
    """
    """
    # Generate STRAIGHT script
    with open(conf.STRAIGHT_SCRIPT, 'w') as f:
        # Header
        f.write("path(path, '%s');\n" % conf.STRAIGHT_PATH)
        f.write("prm.spectralUpdateInterval = %f;\n" % conf.SIGNAL['frameshift'])
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

            # Spectrum normalization    # FIXME (why ?) => not compatible with our corpus podalydes
            f.write("sp = sp * %f;\n" % (1024.0 / (2200.0 * 32768.0)))

            # Synthesis process part 2
            f.write("[sy] = exstraightsynth(f0, sp, ap, %d, prm);\n" % conf.SIGNAL["samplerate"])
            f.write("audiowrite('%s/%s.wav', sy, %d);\n" % (_out_path, base, conf.SIGNAL["samplerate"]))

        # Ending
        f.write("quit;\n")

    # Synthesis!
    cmd = '%s -nojvm -nosplash -nodisplay < %s' % (conf.MATLAB, conf.STRAIGHT_SCRIPT)
    subprocess.call(cmd.split(), stdout=out_handle)

    # Clean  [TODO: do with options]
    os.remove(conf.STRAIGHT_SCRIPT)
    for base in gen_labfile_base_lst:
        os.remove('%s/%s.sp' % (_out_path, base))
        os.remove('%s/%s.ap' % (_out_path, base))
        os.remove('%s/%s.f0' % (_out_path, base))


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

    # 2. Generate scripts
    mk_unseen_script(cmp_tree_path, dur_tree_path, use_gv, args.gv_dir)

    # 3. Compose models
    #    * CMP
    logger.info("CMP unseen model building")
    cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
        (conf.HHEd, conf.TRAIN_CONFIG, cmp_model_fpath, conf.TMP_CMP_MMF, conf.TYPE_HED_UNSEEN_BASE+'_cmp.hed', full_list_fpath)
    subprocess.call(cmd.split(), stdout=out_handle)

    #    * DUR
    logger.info("Duration unseen model building")
    cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
        (conf.HHEd, conf.TRAIN_CONFIG, dur_model_fpath, conf.TMP_DUR_MMF, conf.TYPE_HED_UNSEEN_BASE+'_dur.hed', full_list_fpath)
    subprocess.call(cmd.split(), stdout=out_handle)

    #    * GV
    if use_gv:
        logger.info("Global variance unseen model building")
        cmd = '%s -A -B -C %s -D -T 1 -p -i -H %s -w %s %s %s' % \
            (conf.HHEd, conf.TRAIN_CONFIG, args.gv_dir+'/clustered.mmf', conf.TMP_GV_MMF, conf.GV_HED_UNSEEN_BASE+'.hed',
             args.gv_dir+'/gv.list')
        subprocess.call(cmd.split(), stdout=out_handle)
        # FIXME: change directory to file (args.gv_dir+'/clustered.mmf')

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
    logger.info("Parameter conversion (could be quite long)")
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
    parameter_conversion(out_path, gen_labfile_base_lst)

    # 6. Call straight to synthesize
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
        argp.add_argument('-p', '--pg_type', dest='pg_type', default=0,
                          help="Parameter generation type")

        # Options
        argp.add_argument('-s', '--with_scp', dest='input_is_list', action='store_true',
                          default=False, help="the input is a scp formatted file")
        argp.add_argument('-g', '--gv', dest='gv_dir',
                          help="Define the global variance model directory")

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
        argp.add_argument('-c', '--config', dest='config_fname', required=True,
                          help="Configuration file", metavar='FILE')
        argp.add_argument('-i', '--input', dest='input_fname', required=True,
                          help="Input lab file for synthesis", metavar='FILE')
        argp.add_argument('-o', '--output', dest='output', required=True,
                          help="Output wav directory", metavar='FILE')


        args = argp.parse_args()

        conf = Configuration(args.config_fname)

        # PATH
        cmp_model_fpath = os.path.join(conf.CWD_PATH, args.cmp_model_fname)
        dur_model_fpath = os.path.join(conf.CWD_PATH, args.dur_model_fname)
        full_list_fpath = os.path.join(conf.CWD_PATH, args.full_list_fname)
        cmp_tree_path = os.path.join(conf.CWD_PATH, args.cmp_tree_dir)
        dur_tree_path = os.path.join(conf.CWD_PATH, args.dur_tree_dir)
        out_path = os.path.join(conf.CWD_PATH, args.output)

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
