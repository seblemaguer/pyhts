#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AUTHOR

    Sébastien Le Maguer <slemaguer@coli.uni-saarland.de>

DESCRIPTION

    Module which contains the renderers used to produced the "final product"
    (audio, video, ...) based on the parameters produced by the generator.

LICENSE
    This script is in the public domain, free from copyrights or restrictions.
    Created: 10 October 2016
"""


from rendering.straightrenderer import *
from rendering.worldrenderer import *
from rendering.emarenderer import *
from rendering.straightemarenderer import *
from rendering.weightrenderer import *

def generateRenderer(conf, is_parallel=False, preserve=False):
    try:
        return globals()[conf.renderer.upper() + "Renderer"](conf, is_parallel, preserve)
    except KeyError:
        raise Exception("Renderer " + conf.renderer.upper() + "Renderer" + " unknown")
