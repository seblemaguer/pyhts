import json
import os

import bpy
import bmesh
import mathutils
import numpy

from mathutils import Vector

# ATTENTION: make sure that the multilinearmodel module is accessible by blender
import multilinearmodel

# https://wiki.blender.org/index.php/Dev:Py/Scripts/Cookbook/Code_snippets/Three_ways_to_create_objects

def createMeshFromData(name, origin, verts, faces):
    # Create mesh and object
    me = bpy.data.meshes.new(name+'Mesh')
    ob = bpy.data.objects.new(name, me)
    ob.location = origin
    ob.show_name = True

    # Link object to scene and make active
    scn = bpy.context.scene
    scn.objects.link(ob)
    scn.objects.active = ob
    ob.select = True

    # Create mesh from given verts, faces.
    me.from_pydata(verts, [], faces)

    # Update mesh with new data
    me.update()

    # return created mesh
    return me

# open model file
builder = multilinearmodel.ModelBuilder()

modelData = builder.build_from(os.getenv("model_file"))

# open ema data
with open(os.getenv('input_file')) as inputFile:
    emaData = json.load(inputFile)

# initialize reconstructor object
reconstructor = multilinearmodel.ModelReconstructor(modelData)

# create a mesh showing the mean of the model
# this is only used for initialization
speakerVariations = [0,0,0,0,0,0,0,0,0,0,0,0]
phonemeVariations = [0,0,0,0,0,0,0,0,0,0,0,0,0]

weights = multilinearmodel.ModelWeights()
weights.speakerWeights = numpy.array(speakerVariations)
weights.phonemeWeights = numpy.array(phonemeVariations)

verts = reconstructor.reconstruct_from_variations(weights)
faces = modelData.faces

baseMesh = createMeshFromData("model", ((0,0,0)),  verts, faces)

# create a bmesh version for manipulation purposes
bm = bmesh.new()
bm.from_mesh(baseMesh)

# ensure that a look up table is present
# http://blender.stackexchange.com/questions/31738/how-to-fix-outdated-internal-index-table-in-an-addon
bm.verts.ensure_lookup_table()

# keep track of the frame number
frameNumber = -1

# read base name of output files
outputBase = os.getenv('output_file')

output_frame_number= 0
# iterate through the ema data frames
for frame in emaData:
    # increase frame number
    frameNumber += 1 # FIXME: hardcoded

#    if (frameNumber % 12) != 0:
#        print("I skip %d => %d" % (frameNumber, frameNumber % 10))
#        continue

    # get speaker weights
    weights.speakerWeights = numpy.array(frame["speakerWeights"])
    # get phoneme weights
    weights.phonemeWeights = numpy.array(frame["phonemeWeights"])

    # reconstruct vertex positions for current weights
    verts = reconstructor.reconstruct_from_weights(weights)

    # use bmesh to manipulate vertex positions
    for i in range(0, len(bm.verts)):
        bm.verts[i].co = verts[i]

    # update base mesh
    bm.to_mesh(baseMesh)
    baseMesh.update()

    # create output file name and render scene
    # http://stackoverflow.com/questions/14982836/rendering-and-saving-images-through-blender-python
    bpy.data.scenes["Scene"].render.filepath = '{0}_{1:07d}.png'.format(outputBase, output_frame_number)
    bpy.ops.render.render(write_still=True)
    output_frame_number += 1

