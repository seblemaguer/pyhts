#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION
    Module which contains the generators used to produced the coefficients based on the labels and the HTS models.

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created:  7 January 2017
"""

from generation.nonegenerator import *
from generation.defaultgenerator import *
from generation.dnngenerator import *

def generateGenerator(conf, is_parallel=False, preserve=False):
    """Helper to instanciate the accurate generator based on the given configuration object conf.
    out_handle, logger, is_parallel and preserve are the arguments of the constructor of the generator.
    """
    try:
        return globals()[conf.generator.upper() + "Generator"](conf, is_parallel, preserve)
    except KeyError:
        raise Exception("Acoustic generator " + conf.generator.upper() + "Generator" + " unknown")
