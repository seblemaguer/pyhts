#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 10 October 2016
"""


from rendering.straightgeneration import *
from rendering.worldgeneration import *
from rendering.emageneration import *

def generateRenderer(conf, out_handle, logger, is_parallel=False, preserve=False):
    try:
        return globals()[conf.kind.upper() + "Generation"](conf, out_handle, logger, is_parallel, preserve)
    except KeyError:
        raise Exception("Synthesizer " + conf.kind.upper() + "Generation" + " unknown")
