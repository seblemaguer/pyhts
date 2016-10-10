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

from STRAIGHTGeneration import *


def generateSynthesizer(conf, out_handle):
    try:
        return globals()[conf.kind.upper() + "Generation"](conf, out_handle)
    except KeyError:
        raise Exception("Synthesizer " + conf.kind.upper() + "Generation" + " unknown")
