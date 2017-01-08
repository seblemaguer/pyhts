#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
"""

from generation.defaultgenerator import *
#from generation.dnngenerator import *

def generateGenerator(conf, out_handle, logger, is_parallel=False, preserve=False):
    try:
        return globals()[conf.generator.upper() + "Generator"](conf, out_handle, logger, is_parallel, preserve)
    except KeyError:
        raise Exception("Acoustic generator " + conf.generator.upper() + "Generator" + " unknown")
