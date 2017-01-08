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


from rendering.straightrenderer import *
from rendering.worldrenderer import *
from rendering.emarenderer import *
from rendering.straightemarenderer import *
from rendering.weightrenderer import *

def generateRenderer(conf, out_handle, logger, is_parallel=False, preserve=False):
    try:
        return globals()[conf.renderer.upper() + "Renderer"](conf, out_handle, logger, is_parallel, preserve)
    except KeyError:
        raise Exception("Renderer " + conf.renderer.upper() + "Renderer" + " unknown")
