import bpy
import bpy.utils.previews
import os


pcoll = None


def id(identifier):
    global pcoll

    #try:
    pcoll
    return pcoll[identifier].icon_id

    #except:
        #return pcoll['missing'].icon_id


def register():
    global pcoll
    pcoll = bpy.utils.previews.new()
    directory = os.path.dirname(__file__)
    names = []

    for filename in os.listdir(directory):
        path = os.path.join(directory, filename)
        if not os.path.isfile(path):
            continue
        if not path.endswith('.png'): continue
        #if filename.lower().endswith('.png') or filename.lower().endswith('.svg'):
        name = filename[:filename.rindex('.')]
        names.append(name)
        pcoll.load(name, path, 'IMAGE', True)
    
    for name in names:
        p = pcoll[name]
        p.icon_size = p.image_size
        p.icon_pixels = p.image_pixels

    bpy.types.Scene.fart = pcoll


def unregister():
    global pcoll
    bpy.utils.previews.remove(pcoll)