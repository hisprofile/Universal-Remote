import bpy, random, pickle, typing, gzip, traceback, threading
import blf
from . import XInput, icons
#from importlib import reload
from bpy.utils import register_class, unregister_class
from bpy.props import *
from bpy.types import (Operator, Panel, PropertyGroup, UIList)
from mathutils import *
from math import *
from bpy.app.handlers import persistent
from .udp_listener import controllers, start_udp_listener
from .utils import *

bl_info = {
    "name": "Universal Remote",
    "description": "Single line explaining what this script exactly does.",
    "author": "hisanimations",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Universal Remote",
    "warning": "", # used for warning icon and text in addons panel
    "doc_url": "http://archive.blender.org/wiki/2015/index.php/Extensions:2.6/Py/Scripts/My_Script",
    "tracker_url": "https://developer.blender.org/maniphest/task/edit/form/2/",
    "support": "COMMUNITY",
    "category": "Add Mesh",
}

import importlib, sys, os
#for filename in [ f for f in os.listdir(os.path.dirname(os.path.realpath(__file__))) if f.endswith(".py") ]:
#	if filename == os.path.basename(__file__): continue
#	module = sys.modules.get("{}.{}".format(__name__,filename[:-3]))
#	if module: importlib.reload(module)

params = {}

'''def round(number, decimal_places=0):
    """
    Function:
    - Rounds a float value to a specified number of decimal places
    - Fixes issues with floating point binary approximation rounding in python
    Requires:
    - `number`:
        - Type: int|float
        - What: The number to round
    Optional:
    - `decimal_places`:
        - Type: int 
        - What: The number of decimal places to round to
        - Default: 0
    Example:
    ```
    hard_round(5.6,1)
    ```
    """
    return int(number*(10**decimal_places)+0.5)/(10**decimal_places)'''

Buttons = [
    "btnSouth",
    "btnEast",
    "btnWest",
    "btnNorth",
    "leftBumper",
    "rightBumper",
    "dpadUp",
    "dpadDown",
    "dpadLeft",
    "dpadRight",
    "Start",
    "Back",
    "leftThumb",
    "rightThumb",
]

Axes = [
    'leftJoystickX',
    'leftJoystickY',
    'rightJoystickX',
    'rightJoystickY'
]

Triggers = [
    'leftTrigger',
    'rightTrigger'
]

Extras = [
    'angVelPitch',
    'angVelYaw',
    'angVelRoll',
    'accelXG',
    'accelYG',
    'accelZG',
    'Home',
    'touchButton',
    'touch1Active',
    'touch1X',
    'touch1Y',
    'touch2Active',
    'touch2X',
    'touch2Y',
]

def format_error(err: Exception):
    last = traceback.extract_tb(err.__traceback__)[-1]
    line = last.lineno
    return str(str(err)+':'+str(line))

def v_map(x,a,b,c,d, clamp=None) -> float:
    try:
        y=(x-a)/(b-a)*(d-c)+c
    except ZeroDivisionError:
        return 0
    if clamp:
        return round(min(max(y, c), d), 10)
    else:
        return round(y, 10)
    
def mix(a, b, factor) -> float:
    result = (1-factor)*a + b*factor
    if type(result) == complex:
        return 0
    return result

def getControllers(self, context):
    items = [('None', 'None', 'No Controller')]
    for num, controller in enumerate(context.scene.uremote_props.controllers):
        items.append((controller.name, controller.name, controller.name))
    return items

def getBindsets(self, context):
    items = [('None', 'No Bindset ', 'No Bindset')]
    for num, bindset in enumerate(context.scene.uremote_props.bindingsets):
        items.append((str(num), bindset.name, bindset.name))
    return items

def textBox(self, sentence, icon='NONE', line=56):
    layout = self.box().column()
    sentence = sentence.split(' ')
    mix = sentence[0]
    sentence.pop(0)
    broken = False
    while True:
        add = ' ' + sentence[0]
        if len(mix + add) < line:
            mix += add
            sentence.pop(0)
            if sentence == []:
                layout.row().label(text=mix, icon='NONE' if broken else icon)
                return None

        else:
            layout.row().label(text=mix, icon='NONE' if broken else icon)
            broken = True
            mix = sentence[0]
            sentence.pop(0)
            if sentence == []:
                layout.row().label(text=mix)
                return None

def draw_callback_px(self, context):
    font_id = 0
    spacing = 15
    error_id = 1

    props = context.scene.uremote_props
    blf.enable(font_id, blf.SHADOW)
    blf.enable(error_id, blf.SHADOW)
    blf.size(font_id, 12)
    blf.color(font_id, 1, 1, 1, 1)
    #blf.shadow(font_id, 5, 1, 0, 0, 1)
    for controller in reversed(props.controllers):
        if not (controller.connected and controller.bindset == 'None'): continue
        blf.position(font_id, 15, spacing, 0)
        blf.shadow(font_id, 5, 0, 0, 0, 1)
        blf.shadow_offset(font_id, 1, -1)
        blf.draw(font_id, f'{controller.name} has not been assigned a bindset')
        spacing += 15


    for set_ind, bindset in enumerate(reversed(props.bindingsets)):
        error = False
        for bind_ind, bind in enumerate(reversed(bindset.binds)):
            if bind.error == False: continue
            error = True
            blf.position(error_id, 30, spacing, 0)
            blf.color(error_id, 0.750133, 0.122727, 0.122727, 1.000000)
            blf.shadow(error_id, 5, 0, 0, 0, 1)
            blf.shadow_offset(font_id, 1, -1)
            blf.draw(error_id, f'{bind_ind}:{bind.name} {bind.error_msg}')
            spacing += 15
            
        if error:#True in {bind.error for bind in bindset.binds}:
            blf.position(error_id, 15, spacing, 0)
            blf.color(error_id, 0.750133, 0.122727, 0.122727, 1.000000)
            blf.shadow(error_id, 5, 0, 0, 0, 1)
            blf.shadow_offset(font_id, 1, -1)
            blf.draw(error_id, f'{set_ind}:{bindset.name} ERROR:')
            spacing += 15

    blf.position(font_id, 15, spacing, 0)
    blf.size(font_id, 12)
    blf.color(font_id, 1, 1, 1, 1)
    blf.shadow(font_id, 5, 0, 0, 0, 1)
    blf.shadow_offset(font_id, 1, -1)
    blf.draw(font_id, "Universal Remote: Running!")

class Inputs(PropertyGroup):
    name: StringProperty()
    min: IntProperty(default=0)
    max: IntProperty(default=0)
    from_min: FloatProperty(default=0.0)
    from_max: FloatProperty(default=1.0)
    to_min: FloatProperty(default=0.0)
    to_max: FloatProperty(default=1.0, min=0.001)
    clamp: BoolProperty(default=True)
    smooth_fac: FloatProperty(default=0.0, min=0.0, max=1.0, name='Smoothing Factor')
    use_own_smooth: BoolProperty(default=False, name='Individual Smoothing Factor')
    real_val: FloatProperty()
    prev_val: FloatProperty()
    mapped_val: FloatProperty()
    value: FloatProperty()
    type: StringProperty()
    deadzone: IntProperty()

class Controllers(PropertyGroup):
    name: StringProperty()
    gamepad_name: StringProperty()
    number: IntProperty()
    padId: IntProperty(name='UDP Pad ID', min=-1, max=3, default=-1)
    bindset: EnumProperty(items=getBindsets, name='Bindset')
    connected: BoolProperty(default=False)
    inputs: CollectionProperty(type=Inputs)
    smooth_fac: FloatProperty(default=0.0, min=0.0, max=1.0, name='Smoothing Factor')
    input_index: IntProperty()

class Binds(PropertyGroup):
    name: StringProperty(default='New Control')
    use: BoolProperty(default=True)
    method: EnumProperty(items=[ 
        ('Additive', 'Additive', 'Adds onto the existing value'),
        ('Absolute', 'Absolute', 'Sets the existing value')
        ],
    name='Method')
    input: StringProperty(name='Input', description='Input from which to take values')

    expression: StringProperty(default=r'var', name='Expression', description='''Variable's name is "var"''')

    threshold: FloatProperty(default=0.5, name='Threshold')
    state: BoolProperty(default=False)
    toggle: BoolProperty(default=True, name='Toggle', description='Toggle the property')

    type: EnumProperty(items=[
        ('INPUT', 'Basic Input', 'Take the value of the input', 'RESTRICT_SELECT_OFF', 0),
        ('SWITCH', 'Switch', 'Output a boolean value based on a threshold', 'EVENT_SHIFT', 1),
        ('SCRIPT', 'Script', 'Only use the bind to execute a script every tick', 'TEXT', 2)
    ], name='Bind Type', description='What this bind does', options=set())

    pre_exec: StringProperty()
    pre_use_block: BoolProperty(name='Use Text File', description='Use a script from the text editor')
    pre_exec_block: PointerProperty(type=bpy.types.Text)
    
    post_exec: StringProperty()
    post_use_block: BoolProperty(name='Use Text File', description='Use a script from the text editor')
    post_exec_block: PointerProperty(type=bpy.types.Text)

    use_long_path: BoolProperty()
    id: PointerProperty(type=bpy.types.ID)
    id_type: EnumProperty(items=[
        ('', 'ID Type', ''),
        ('ACTION', 'Action', '', 'ACTION', 0),
        ('ARMATURE', 'Armature', '', 'ARMATURE_DATA', 1),
        ('BRUSH', 'Brush', '', 'BRUSH_DATA', 2),
        ('CACHEFILE', 'Cache File', '', 'FILE', 3),
        ('CAMERA', 'Camera', '', 'CAMERA_DATA', 4),
        ('COLLECTION', 'Collection', '', 'OUTLINER_COLLECTION', 5),
        ('CURVE', 'Curve', '', 'CURVE_DATA', 6),
        ('CURVES', 'Curves', '', 'CURVES_DATA', 7),
        ('FONT', 'Font', '', 'FONT_DATA', 8),
        ('GREASEPENCIL', 'Grease Pencil', '', 'GREASEPENCIL', 9),
        ('IMAGE', 'Image', '', 'IMAGE_DATA', 11),
        ('KEY', 'Key', '', 'SHAPEKEY_DATA', 12),
        ('LATTICE', 'Lattice', '', 'LATTICE_DATA', 13),
        ('LIBRARY', 'Library', '', 'LIBRARY_DATA_DIRECT', 14),
        ('LIGHT', 'Light', '', 'LIGHT_DATA', 15),
        ('LIGHT_PROBE', 'Light Probe', '', 'LIGHTPROBE_CUBEMAP', 16),
        ('LINESTYLE', 'Line Style', '', 'LINE_DATA', 17),
        ('MASK', 'Mask', '', 'MOD_MASK', 18),
        ('MATERIAL', 'Material', '', 'MATERIAL_DATA', 19),
        ('MESH', 'Mesh', '', 'MESH_DATA', 20),
        ('META', 'Metaball', '', 'META_DATA', 21),
        ('MOVIECLIP', 'Movie Clip', '', 'TRACKER', 22),
        ('NODETREE', 'Node Tree', '', 'NODETREE', 23),
        ('OBJECT', 'Object', '', 'OBJECT_DATA', 24),
        ('PAINTCURVE', 'Paint Curve', '', 'CURVE_BEZCURVE', 25),
        ('PALETTE', 'Palette', '', 'COLOR', 26),
        ('PARTICLE', 'Particle', '', 'PARTICLE_DATA', 27),
        ('POINTCLOUD', 'Point Cloud', '', 'POINTCLOUD_DATA', 28),
        ('SCENE', 'Scene', '', 'SCENE_DATA', 29),
        ('SCREEN', 'Screen', '', 'WORKSPACE', 30),
        ('SOUND', 'Sound', '', 'SOUND', 31),
        ('SPEAKER', 'Speaker', '', 'SPEAKER', 32),
        ('TEXT', 'Text', '', 'TEXT', 33),
        ('TEXTURE', 'Texture', '', 'TEXTURE_DATA', 34),
        ('VOLUME', 'Volume', '', 'VOLUME_DATA', 35),
        ('WINDOWMANAGER', 'Window Manager', '', 'WINDOW', 36),
        ('WORKSPACE', 'Workspace', '', 'WORKSPACE', 37),
        ('WORLD', 'World', '', 'WORLD_DATA', 38)
        ],
        name='ID Type',
        description='Type of data block to set values to',
        options={'SKIP_SAVE'},
        default='OBJECT')
    multiplier: FloatProperty(default=1.0, name='Overall Multiplier', step=4)
    error: BoolProperty()
    error_msg: StringProperty(default='|')
    subtarget: StringProperty(name='Subtarget')
    index: IntProperty(name='Index', min=-1, default=-1)#StringProperty(name='Index')
    data_path: StringProperty(name='Data Path', description='Data path to property of data block')
    long_data_path: StringProperty(name='Data Path', description='Absolute data path to property')

class BindingSets(PropertyGroup):
    name: StringProperty(default='New Binding Set')
    binds: CollectionProperty(type=Binds)
    bindindex: IntProperty()
    use: BoolProperty(name='Use', default=True)

class URemoteProps(PropertyGroup):
    controllers: CollectionProperty(type=Controllers)
    controller_index: IntProperty(default=0)
    controller_scan: BoolProperty(default=False)

    bindingsets: CollectionProperty(type=BindingSets)
    bindingsetindex: IntProperty()

    calibration: BoolProperty(default=False)
    running: BoolProperty(default=False)
    rate: IntProperty(min=1, max=100, default=60)
    keyframe: BoolProperty(default = False)

    initialized: BoolProperty(default=False)

    use_udp_server: BoolProperty(name='Use UDP Listener', description='Start a UDP listening service to receive more controller data, such as Gyroscope values. Supoprts DS4Windows and reWASD.', default=False)
    udp_addr: StringProperty(name='UDP Server', description='Address for the UDP server.', default='127.0.0.1')
    udp_port: StringProperty(name='UDP Port', description='Port for the UDP server', default='26760')
    server_fail: BoolProperty(name='server fail', default=True)

    #pygame_debug: BoolProperty(default=False)

class UNIREM_OT_bindingset_manipulator(Operator):
    bl_idname = 'bindingset.manipulator'
    bl_label = 'Bindingset Manipulator'
    
    operation: EnumProperty(items=[
        ('CHANGE', 'CHANGE', 'CHANGE'),
        ('MOVE', 'MOVE', 'MOVE')
    ])
    Add: BoolProperty()
    Move: IntProperty()

    def execute(self, context):
        props = context.scene.uremote_props
        bindingsets = props.bindingsets
        index = props.bindingsetindex
        if self.operation == 'CHANGE':
            if self.Add:
                bindingsets.add()
                props.bindingsetindex = len(bindingsets) - 1
            else:
                bindingsets.remove(index)
                props.bindingsetindex = min(index, len(bindingsets) - 1)
        if self.operation == 'MOVE':
            bindingsets.move(index, index - self.Move)
            props.bindingsetindex = min(max(index - self.Move, 0), len(bindingsets) - 1)
        return {'FINISHED'}
    
class UNIREM_OT_bind_manipulator(Operator):
    bl_idname = 'bind.manipulator'
    bl_label = 'Bindingset Manipulator'
    options = {'UNDO'}
    operation: EnumProperty(items=[
        ('CHANGE', 'CHANGE', 'CHANGE'),
        ('MOVE', 'MOVE', 'MOVE')
    ])
    Add: BoolProperty()
    Move: IntProperty()

    def execute(self, context):
        props = context.scene.uremote_props
        bindingset = props.bindingsets[props.bindingsetindex]
        binds = bindingset.binds
        index = bindingset.bindindex
        if self.operation == 'CHANGE':
            if self.Add:
                binds.add()
                bindingset.bindindex = len(binds) - 1
            else:
                if len(binds) == 0:
                    return {'CANCELLED'}
                binds.remove(bindingset.bindindex)
                bindingset.bindindex = min(index, len(binds) - 1)
            return {'FINISHED'}
        if len(binds) == 0:
            return {'CANCELLED'}
        if self.operation == 'MOVE':
            binds.move(index, index - self.Move)
            bindingset.bindindex = min(max(index - self.Move, 0), len(binds) - 1)
        return {'CANCELLED'}
    
class UNIREM_OT_end(Operator):
    bl_idname = 'uremote.stop'
    bl_label = 'Stop Controller Connection'

    def execute(self, context):
        props = context.scene.uremote_props
        props.running=False
        return {'FINISHED'}
    
class UNIREM_OT_duplicate_bindset(Operator):
    bl_idname = 'uremote.duplicatebindset'
    bl_label = 'Duplicate Bind'

    def execute(self, context):
        props = context.scene.uremote_props
        if len(props.bindingsets) == 0: return {'CANCELLED'}
        bindset = props.bindingsets[props.bindingsetindex]
        new_set = props.bindingsets.add()
        new_set.name = bindset.name

        for bind in bindset.binds:
            new = new_set.binds.add()
            for key in bind.bl_rna.properties.keys()[2:]:
                setattr(new, key, getattr(bind, key))

        props.bindingsetindex = len(props.bindingsets) - 1
        return {'FINISHED'}

class UNIREM_OT_duplicate_bind(Operator):
    bl_idname = 'uremote.duplicatebind'
    bl_label = 'Duplicate Bind'

    def execute(self, context):
        props = context.scene.uremote_props
        bindset = props.bindingsets[props.bindingsetindex]
        if len(bindset.binds) == 0: return {'CANCELLED'}
        bind = bindset.binds[bindset.bindindex]
        new = bindset.binds.add()

        for key in bind.bl_rna.properties.keys()[2:]:
            setattr(new, key, getattr(bind, key))
        
        bindset.bindindex = len(bindset.binds) - 1

        return {'FINISHED'}

class UNIREM_OT_import_export(Operator):
    bl_idname = 'uremote.transferbindset'
    bl_label = 'Transfer Bindset'
    bl_description = "Used for importing/exporting other people's bindsets"

    export: BoolProperty()
    data: StringProperty()

    def transfer(self, context):
        props = context.scene.uremote_props
        bindset = props.bindingsets[props.bindingsetindex]
        if self.export:
            root_data = {}
            root_data['NAME'] = bindset.name
            root_data['DATA'] = {}

            for num, bind in enumerate(bindset.binds):
                data = root_data['DATA'][num] = {}
                data['name'] = bind.name
                data['input'] = bind.input
                data['multiplier'] = bind.multiplier
                data['type'] = bind.type
                data['pre_exec'] = bind.pre_exec_block.as_string() if (bind.pre_use_block) and (bind.pre_exec_block != None) else bind.pre_exec
                data['post_exec'] = bind.post_exec_block.as_string() if (bind.post_use_block) and (bind.post_exec_block != None) else bind.post_exec

                if not bind.use_long_path and bind.id != None:
                    data['long_data_path'] = bind.id.__repr__()

                else:
                    data['long_data_path'] = bind.long_data_path
                
                data['data_path'] = bind.data_path
                data['index'] = bind.index
                data['expression'] = bind.expression
                data['method'] = bind.method

            txt = str(pickle.dumps(root_data))[2:-1]
            self.data = txt

        else:
            data = bytes(self.data, 'utf-8').decode('unicode_escape').encode('raw_unicode_escape')
            data = pickle.loads(data)
            new_set = props.bindingsets.add()
            new_set.name = data['NAME']

            for bind, bind_data in data['DATA'].items():
                bind = new_set.binds.add()
                for attr, dat in bind_data.items():
                    setattr(bind, attr, dat)

                bind.use_long_path = True

    def execute(self, context):
        if not self.export:
            self.transfer(context)

        return {'FINISHED'}
    
    def draw(self, context):
        layout = self.layout
        if self.export:
            layout.label(text='Copy data to clipboard!')
        else:
            layout.label(text='Paste data from clipboard!')
        layout.prop(self, 'data', text='Data')
    
    def invoke(self, context, event):

        self.data = ''
        if self.export:
            self.transfer(context)
        return context.window_manager.invoke_props_dialog(self)

class UNIREM_OT_runner(Operator):
    bl_idname = 'uremote.startsession'
    bl_label = 'Start Session'
    bl_description = 'Start a session with your controllers'

    _timer = None

    @classmethod
    def poll(cls, context):
        props = context.scene.uremote_props
        return 1 - props.running

    def modal(self, context, event):
        props = context.scene.uremote_props
        if props.running == False:
            self.cancel(context)
            return {'CANCELLED'}

        if event.type == 'TIMER':
            connected = XInput.get_connected()

            for controller_num, status in enumerate(connected):
                controller = props.controllers[controller_num]
                if not status:
                    controller.connected = False
                    continue
                
                controller.connected = True

                '''
                >>> INPUT READER
                '''

                ##### Get state of a controller
                try:
                    state = XInput.get_state(controller_num)
                except XInput.XInputNotConnectedError:
                    continue
                #####
                
                ##### Get input values of state
                inputs = [
                        *XInput.get_thumb_values(state).items(),
                        *XInput.get_button_values(state).items(), 
                        *XInput.get_trigger_values(state).items(), 
                        ]
                
                #print(inputs)
                
                if controller.padId != -1:
                    udp_con = controllers.get(controller.padId)
                    #print(controllers.get(controller.padId))
                    udp_con = udp_con[0]
                    inputs += [(extra, getattr(udp_con, extra)) for extra in Extras]
                    #print(inputs)

                #####
                
                ##### Update input values of a controller
                for input, value in inputs:
                    input = controller.inputs[input]
                    input.real_val = value
                    input.prev_val = input.value
                    input.value = mix(value, input.value, input.smooth_fac if 
                                    input.use_own_smooth else controller.smooth_fac)
                #####


                inputs = controller.inputs

                '''
                >>> INPUT APPLICATOR
                '''

                if controller.bindset == 'None':
                    continue

                # Get bindset assigned to controller
                try:
                    bindset = props.bindingsets[int(controller.bindset)]
                except:
                    controller.bindset = 'None'
                    continue

                # Iterate through binds of bindset
                for bind in bindset.binds:
                    if not bind.use: continue

                    try: # Commands to execute pre-application
                        if bind.pre_use_block and (bind.pre_exec_block != None):
                            block = bind.pre_exec_block
                            exec(block.as_string())
                        else:
                            exe = bytes(bind.pre_exec, 'utf-8').decode('unicode_escape')
                            exec(exe)
                        bind.error = False
                    except Exception as e:
                        bind.error = True
                        bind.error_msg = 'pre_exec|' + format_error(e)
                        continue

                    bind: Binds

                    if bind.type == 'SCRIPT': continue
                    if bind.expression == '': continue
                    if bind.data_path == '' and (not bind.use_long_path): continue
                    if (bind.id == None) and (not bind.use_long_path): continue
                    if bind.use_long_path and (bind.long_data_path == ''): continue

                    # If no input is provided, assume the expression takes in multiple inputs
                    if bind.input == '':
                        var = 0
                    else:
                        input = controller.inputs[bind.input]
                        var = input.value * bind.multiplier

                    # Operation
                    if bind.type == 'INPUT':
                        if bind.method == 'Additive':
                            operation = '+='
                        else:
                            operation = '='

                        # If the operation is absolute, input is NOT none, and the input's value hasn't changed, then continue in the loop.
                        # This is done to save on resources.
                        if (bind.method == 'Absolute') and (bind.input != '') \
                        and (input.value == input.prev_val): continue

                        try: # Evaluation of expression
                            value = eval(bind.expression)
                        except Exception as e:
                            bind.error = True
                            bind.error_msg = 'expr|' + format_error(e)
                            continue
                    if bind.type == 'SWITCH':
                        operation = '='

                        if bind.toggle:
                            if (input.value > bind.threshold) and (input.prev_val < bind.threshold):
                                bind.state = 1 - bind.state
                            value = bind.state
                            
                        else:
                            value = input.value > bind.threshold
                    
                    if bind.index != '':
                        index = f'[{bind.index}]'
                    else:
                        index = ''
                    index = bind.index
                    try: # Application of evaluation to property
                        
                        #object: bpy.Types.Object
                        #object: bpy.types.Object
                        
                        if bind.use_long_path:
                            object = eval(bind.long_data_path)
                            #print(object, bind.long_data_path)
                        else:
                            object = bind.id
                            #data = getattr(object, bind.data_path)
                        #data = getattr(object, bind.data_path)
                        #if data == None: raise Exception(f'{object.name} ({bind.id_type}) has no property "{bind.data_path}"')
                        #    if hasattr(data, '__getitem__') and bind.index.isdigit():
                        #        if bind.method == 'Absolute' or bind.type == 'SWITCH':
                        #            data[int(bind.index)] = value
                        #        else:
                        #            data[int(bind.index)] += value
                        #    
                        #    else:
                        #        if bind.method == 'Absolute' or bind.type == 'SWITCH':
                        #            setattr(object, bind.data_path, value)
                        #        else:
                        #            setattr(object, bind.data_path, data+value)

                        #if bind.method == 'Absolute':

                        #if not bind.use_long_path:
                        data = object.path_resolve(bind.data_path, False)
                        data_val = object.path_resolve(bind.data_path, True)
                        data_str = repr(data)
                        id_data = data.id_data
                        id_data_str = repr(id_data)
                        second_last_attr = data.data
                        second_last_attr_str = repr(second_last_attr)
                        last_attr_str = data_str[len(second_last_attr_str):].lstrip('.')
                        #print(data_str, second_last_attr_str, last_attr_str)

                        if bind.index != -1:
                            if bind.type == 'INPUT':
                                if bind.method == 'Additive':
                                    data_val[index] += value
                                else:
                                    data_val[index] = value
                                #exec(f'{data} {operation} value')
                            else:
                                data_val[index] = value
                        else:
                            #data = object.path_resolve(bind.data_path, False).__repr__() + index
                            if bind.type == 'INPUT':
                                if bind.method == 'Additive':
                                    setattr(second_last_attr, last_attr_str, data_val + value)
                                else:
                                    setattr(second_last_attr, last_attr_str, value)
                                #exec(f'{data} {operation} value')
                            else:
                                setattr(second_last_attr, last_attr_str, value)
                            #exec(f'{data} = value')

                    except Exception as e:
                        bind.error = True
                        bind.error_msg = 'application|' + format_error(e)
                        continue

                    try: # Commands to execute post-application
                        if bind.post_use_block and (bind.post_exec_block != None):
                            block = bind.post_exec_block
                            exec(block.as_string())
                        else:
                            exe = bytes(bind.post_exec, 'utf-8').decode('unicode_escape')
                            exec(exe)

                    except Exception as e:
                        bind.error = True
                        bind.error_msg = 'post_exec|' + format_error(e)
                        continue

                    if props.keyframe:
                        id_data.keyframe_insert(data.path_from_id(), index=index)
                        #object.keyframe_insert(bind.data_path, index=int(bind.index) if bind.index else -1)
                    
                    bind.error = False

        return {'PASS_THROUGH'}

    def execute(self, context):
        #reload(XInput)
        props: URemoteProps
        self.report({'INFO'}, 'U-Remote Session Start!')
        wm = context.window_manager
        props = context.scene.uremote_props
        props.running = True
        if props.use_udp_server:
            udp_listener = threading.Thread(target=start_udp_listener, args=(props, self), daemon=True)
            udp_listener.start()

        for input in [input for c in props.controllers for input in c.inputs if input.name in Extras]:
            input.value = 0

        self._timer = wm.event_timer_add(1/props.rate, window=context.window)
        wm.modal_handler_add(self)
        self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_callback_px, (self, context), 'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    def cancel(self, context):
        self.report({'INFO'}, 'U-Remote Session Ended!')
        bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

class UNIREM_OT_genericText(bpy.types.Operator):
    bl_idname = 'uremote.textbox'
    bl_label = 'Hints'
    bl_description = 'A window will display any possible questions you have'

    text: StringProperty(default='')
    icons: StringProperty()
    size: StringProperty()
    width: IntProperty(default=400)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=self.width)
    
    def draw(self, context):
        sentences = self.text.split('\n')
        icons = self.icons.split(',')
        sizes = self.size.split(',')
        for sentence, icon, size in zip(sentences, icons, sizes):
            textBox(self.layout, sentence, icon, int(size))

    def execute(self, context):
        return {'FINISHED'}
    
class UNIREM_OT_add_from_path(Operator):
    bl_idname = 'uremote.add_from_path'
    bl_label = 'Add from Path'
    bl_description = 'Set the data-block based on a Full Path'

    path: StringProperty(default='', name='Full Path')

    bl_options = {'UNDO'}

    #def invoke(self, context, event):
        #return context.window_manager.invoke_props_popup(self, event)
    
    def execute(self, context):



        props = context.scene.uremote_props
        bindingset = props.bindingsets[props.bindingsetindex]
        bind = bindingset.binds[bindingset.bindindex]

        iterr = -1
        path = context.window_manager.clipboard
        #path_index = str(path)
        index = -1
        if path.endswith(']'):
            while path[iterr] != '[':
                iterr -= 1
            index_try = path[iterr+1:-1]
            print(index_try.isdigit())
            if index_try.isdigit():
                index = int(index_try)
                path = path[:iterr]
            print(index, type(index))
  
        split = path.split('.')
        for i in range(1, len(split)):
            try:
                ID_str = '.'.join(split[:i])
                ID: bpy.types.ID = eval('.'.join(split[:i]))
                if isinstance(ID, bpy.types.ID):
                    rest = '.'.join(split[i:])
                    break
            except:
                continue
        else:
            self.report({'ERROR'}, "Bad path!")
            return {'CANCELLED'}
        
        final = ID.path_resolve(rest, False)
        final_str = repr(final)
        id_data = final.id_data
        if isinstance(id_data, bpy.types.NodeTree):
            id_data = ID
            data_path = 'node_tree.'+final.path_from_id()
        else:
            data_path = final.path_from_id()

        id_type = id_data.bl_rna.identifier.upper()

        bind.id_type = id_type
        bind.id = id_data
        bind.long_data_path = repr(id_data)
        bind.data_path = data_path
        bind.index = index

        return {'FINISHED'}

class UNIREM_OT_batch_adjust(Operator):
    bl_idname = 'uremote.batchadjust'
    bl_label = 'Batch Adjust'
    bl_description = 'Set attributes of a list of binds'

    name: StringProperty(default='New Control')
    use: BoolProperty(default=True)
    method: EnumProperty(items=[ 
        ('Additive', 'Additive', 'Adds onto the existing value'),
        ('Absolute', 'Absolute', 'Sets the existing value')
        ],
    name='Method')
    input: StringProperty(name='Input', description='Input from which to take values')

    #expr_use_block: BoolProperty()
    expression: StringProperty(default=r'var', name='Expression', description='''Variable's name is "var"''')
    #expr_block: PointerProperty(type=bpy.types.Text, description='Use a text file t')

    pre_exec: StringProperty()
    pre_use_block: BoolProperty(name='Use Text File', description='Use a script from the text editor')
    pre_exec_block: PointerProperty(type=bpy.types.Text)
    
    post_exec: StringProperty()
    post_use_block: BoolProperty(name='Use Text File', description='Use a script from the text editor')
    post_exec_block: PointerProperty(type=bpy.types.Text)

    use_long_path: BoolProperty()
    id: PointerProperty(type=bpy.types.ID)
    id_type: EnumProperty(items=[
        ('', 'ID Type', ''),
        ('ACTION', 'Action', '', 'ACTION', 0),
        ('ARMATURE', 'Armature', '', 'ARMATURE_DATA', 1),
        ('BRUSH', 'Brush', '', 'BRUSH_DATA', 2),
        ('CACHEFILE', 'Cache File', '', 'FILE', 3),
        ('CAMERA', 'Camera', '', 'CAMERA_DATA', 4),
        ('COLLECTION', 'Collection', '', 'OUTLINER_COLLECTION', 5),
        ('CURVE', 'Curve', '', 'CURVE_DATA', 6),
        ('CURVES', 'Curves', '', 'CURVES_DATA', 7),
        ('FONT', 'Font', '', 'FONT_DATA', 8),
        ('GREASEPENCIL', 'Grease Pencil', '', 'GREASEPENCIL', 9),
        ('IMAGE', 'Image', '', 'IMAGE_DATA', 11),
        ('KEY', 'Key', '', 'SHAPEKEY_DATA', 12),
        ('LATTICE', 'Lattice', '', 'LATTICE_DATA', 13),
        ('LIBRARY', 'Library', '', 'LIBRARY_DATA_DIRECT', 14),
        ('LIGHT', 'Light', '', 'LIGHT_DATA', 15),
        ('LIGHT_PROBE', 'Light Probe', '', 'LIGHTPROBE_CUBEMAP', 16),
        ('LINESTYLE', 'Line Style', '', 'LINE_DATA', 17),
        ('MASK', 'Mask', '', 'MOD_MASK', 18),
        ('MATERIAL', 'Material', '', 'MATERIAL_DATA', 19),
        ('MESH', 'Mesh', '', 'MESH_DATA', 20),
        ('META', 'Metaball', '', 'META_DATA', 21),
        ('MOVIECLIP', 'Movie Clip', '', 'TRACKER', 22),
        ('NODETREE', 'Node Tree', '', 'NODETREE', 23),
        ('OBJECT', 'Object', '', 'OBJECT_DATA', 24),
        ('PAINTCURVE', 'Paint Curve', '', 'CURVE_BEZCURVE', 25),
        ('PALETTE', 'Palette', '', 'COLOR', 26),
        ('PARTICLE', 'Particle', '', 'PARTICLE_DATA', 27),
        ('POINTCLOUD', 'Point Cloud', '', 'POINTCLOUD_DATA', 28),
        ('SCENE', 'Scene', '', 'SCENE_DATA', 29),
        ('SCREEN', 'Screen', '', 'WORKSPACE', 30),
        ('SOUND', 'Sound', '', 'SOUND', 31),
        ('SPEAKER', 'Speaker', '', 'SPEAKER', 32),
        ('TEXT', 'Text', '', 'TEXT', 33),
        ('TEXTURE', 'Texture', '', 'TEXTURE_DATA', 34),
        ('VOLUME', 'Volume', '', 'VOLUME_DATA', 35),
        ('WINDOWMANAGER', 'Window Manager', '', 'WINDOW', 36),
        ('WORKSPACE', 'Workspace', '', 'WORKSPACE', 37),
        ('WORLD', 'World', '', 'WORLD_DATA', 38)
        ],
        name='ID Type',
        description='Type of data block to set values to',
        options={'SKIP_SAVE'},
        default='OBJECT')
    multiplier: FloatProperty(default=1.0, name='Overall Multiplier', step=4)
    error: BoolProperty()
    error_msg: StringProperty(default='|')
    subtarget: StringProperty(name='Subtarget')
    #index: IntProperty(default=0, name='Index')
    index: StringProperty(name='Index')
    data_path: StringProperty(name='Data Path', description='Data path to property of data block')
    long_data_path: StringProperty(name='Data Path', description='Absolute data path to property')

    def execute(self, context):
        pass

class UNIREM_UL_controller_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        row = layout.row()
        row.label(text=item.name, icon='RADIOBUT_ON' if item.connected else 'RADIOBUT_OFF')
        if not item.connected:
            layout.alert = True
        row.prop(item, 'bindset', text='')

class UNIREM_UL_input_list(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        row = layout.row()
        split = row.split(factor=0.6)
        split.label(text=item.name)
        split = row.split()
        split.progress(factor=v_map(item.value, item.from_min, item.from_max, 0, 1, True), type='BAR')

class UNIREM_UL_bindingsets(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        row = layout.row()
        row.alignment = 'LEFT'
        row.prop(item, 'name', emboss=False, text='')
        row.prop(item, 'use', toggle=True, text='', icon='CHECKMARK')

class UNIREM_UL_binds(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index, flt_flag):
        row = layout.row()
        #split = row.split(factor=0.7)
        row.alert = item.error
        row.prop(item, 'name', emboss=False, text='', icon='ERROR' if item.error else 'NONE')
        row.prop(item, 'type', expand=True, text='')
        #row.prop(item, 'exec_only', text='', icon='TEXT')
        #row.prop(item, 'use', toggle=True, text='', icon='ERROR' if item.error else ('CHECKMARK' if item.use else 'X'))
        row.prop(item, 'use', toggle=True, text='', icon='X' if not item.use else ('ERROR' if item.error else 'CHECKMARK'))

class UNIREM_PT_controllers(Panel):
    bl_parent_id = "UNIREM_PT_main_panel"
    bl_label = ''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    def draw_header(self, context):
        layout = self.layout
        layout.alignment = 'EXPAND'
        layout.separator()
        layout.label(text='Controllers', icon_value=icons.id('controller'))#icon='MOUSE_LMB_DRAG')
        op = layout.operator('uremote.textbox', text='', icon='QUESTION')
        layout.separator()
        op.width = 330
        op.text = '''A list of controllers allowed for use with a symbol indicating whether or not they are plugged in.
Smoothing Factor is a global factor at which all inputs' values will be smoothed by mixing their current value with their previous. It is possible for inputs to have their own smoothing rates.'''
        op.size = '53,60'
        op.icons = 'NONE,MOD_SMOOTH'

    def draw(self, context):
        layout = self.layout
        props = context.scene.uremote_props
        if len(props.controllers) == 0:
            layout.label(text='No controller(s) detected!')
        else:
            controller = props.controllers[props.controller_index]
            layout = self.layout.box()
            layout.row().template_list('UNIREM_UL_controller_list', 'Controllers', props, 'controllers', props, 'controller_index')
            col = layout.column()
            layout.prop(controller, 'smooth_fac', slider=True)
            layout.prop(controller, 'padId')

class UNIREM_PT_inputs(Panel):
    bl_parent_id = 'UNIREM_PT_main_panel'
    bl_label = ''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    @classmethod
    def poll(cls, context):
        return len(context.scene.uremote_props.controllers) != 0
    
    def draw_header(self, context):
        layout = self.layout
        layout.alignment = 'EXPAND'
        layout.separator()
        layout.label(text='Inputs', icon_value=icons.id('buttons'))# icon='MOUSE_LMB_DRAG')
        op = layout.operator('uremote.textbox', text='', icon='QUESTION')
        layout.separator()
        op.width = 330
        op.text = '''The list of inputs you are allowed to use and access under this addon.
To make an input have its own smoothing rate, enable "Individual Smoothing" and set a factor.'''
        op.size = '53,60'
        op.icons = 'NONE,MOD_SMOOTH'

    def draw(self, context):
        layout = self.layout
        props = context.scene.uremote_props
        if len(props.controllers) == 0:
            layout.label(text='No inputs added!')
            return None
        controller = props.controllers[props.controller_index]
        if len(controller.inputs) == 0:
            layout.label(text='No inputs added!')
            return None
        input = controller.inputs[controller.input_index]
        box = layout.box()
        box.row().template_list('UNIREM_UL_input_list', 'Inputs', controller, 'inputs', controller, 'input_index')
        col = box.column()
        col.row().label(text=f'Real Value: {input.real_val}')
        col.row().label(text=f'Smoothed Value: {input.value}')
        col = box.row().column(align=True)
        col.row().prop(input, 'use_own_smooth')
        row = col.row()
        row.enabled = input.use_own_smooth
        row.prop(input, 'smooth_fac', slider=True)
        #col.row().label(text='Value Mapping')
        #row = col.row(align=True)
        #row.prop(input, 'from_min', text='From Min')
        #row.prop(input, 'from_max', text='From Max')
        #row = col.row(align=True)
        #row.prop(input, 'to_min', text='To Min')
        #row.prop(input, 'to_max', text='To Max')

class UNIREM_PT_bindingsets(Panel):
    bl_parent_id = 'UNIREM_PT_main_panel'
    bl_label = ''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED', 'HEADER_LAYOUT_EXPAND'}

    def draw_header(self, context):
        layout = self.layout
        layout.alignment = 'EXPAND'
        layout.separator()
        layout.label(text='Binding Sets', icon='ASSET_MANAGER')
        op = layout.operator('uremote.textbox', text='', icon='QUESTION')
        layout.separator()
        op.width = 330
        op.text = '''Create sets of binds to assign to a controller.'''
        op.size = '53'
        op.icons = 'NONE'

    '''@classmethod
    def poll(cls, context):
        props = context.scene.uremote_props
        if len(context.scene.uremote_props.controllers) == 0:
            return False
        controller = props.controllers[props.controller_index]
        if len(controller.inputs) == 0'''

    def draw(self, context):
        layout = self.layout
        props = context.scene.uremote_props
        if len(context.scene.uremote_props.controllers) == 0:
            layout.row().label(text='Add a controller!')
            return None
        
        controller = props.controllers[props.controller_index]
        if len(controller.inputs) == 0:
            layout.row().label(text='Add some inputs!')
            return None
        
        row = layout.row()
        col = row.column()
        col.template_list('UNIREM_UL_bindingsets', 'Binding Sets', props, 'bindingsets', props, 'bindingsetindex')
        col = row.column()

        op = col.operator('bindingset.manipulator', text='', icon='ADD')
        op.operation = 'CHANGE'
        op.Add = True

        op = col.operator('bindingset.manipulator', text='', icon='REMOVE')
        op.operation = 'CHANGE'
        op.Add = False

        col.separator()

        op = col.operator('bindingset.manipulator', text='', icon='TRIA_UP')
        op.operation = 'MOVE'
        op.Move = 1

        op = col.operator('bindingset.manipulator', text='', icon='TRIA_DOWN')
        op.operation = 'MOVE'
        op.Move = -1

        col.operator('uremote.duplicatebindset', text='', icon='DUPLICATE')

        row = layout.row()
        op = row.operator('uremote.transferbindset', text='Import')
        op.export = False
        op = row.operator('uremote.transferbindset', text='Export')
        op.export = True

        if len(props.bindingsets) == 0:
            layout.label(text='Add a bind set!')
            return None
        bindset = props.bindingsets[props.bindingsetindex]


# from https://blender.stackexchange.com/a/293222
def template_any_ID(layout: typing.Any, data: typing.Any, property: str, type_property: str, text: str='', text_ctxt: str='', translate: bool=True) -> None:
    id_type_to_collection_name = {
        'ACTION': 'actions',
        'ARMATURE': 'armatures',
        'BRUSH': 'brushes',
        'CAMERA': 'cameras',
        'CACHEFILE': 'cache_files',
        'COLLECTION': 'collections',
        'CURVE': 'curves',
        'CURVES': 'curves',
        'FONT': 'fonts',
        'GREASEPENCIL': 'grease_pencils',
        'IMAGE': 'images',
        'KEY': 'shape_keys',
        'LATTICE': 'lattices',
        'LIBRARY': 'libraries',
        'LIGHT': 'lights',
        'LIGHT_PROBE': 'lightprobes',
        'LINESTYLE': 'linestyles',
        'MASK': 'masks',
        'MATERIAL': 'materials',
        'MESH': 'meshes',
        'META': 'metaballs',
        'MOVIECLIP': 'movieclips',
        'NODETREE': 'node_groups',
        'OBJECT': 'objects',
        'PAINTCURVE': 'paint_curves',
        'PALETTE': 'palettes',
        'PARTICLE': 'particles',
        'POINTCLOUD': 'pointclouds',
        'SCENE': 'scenes',
        'SCREEN': 'screens',
        'SOUND': 'sounds',
        'SPEAKER': 'speakers',
        'TEXT': 'texts',
        'TEXTURE': 'textures',
        'VOLUME': 'volumes',
        'WINDOWMANAGER': 'window_managers',
        'WORKSPACE': 'workspaces',
        'WORLD': 'worlds'
        }
    #split = layout.split(factor=0.33)
    split = layout.split(factor=0.25)

    # FIRST PART
    row = split.row()

    # Label - either use the provided text, or will become "ID-Block:"
    if text != '':
        row.label(text=text, text_ctxt=text_ctxt, translate=translate)
    elif data.bl_rna.properties[property].name != '':
        row.label(text='Data Block:', text_ctxt=text_ctxt, translate=translate)
    else:
        row.label(text="ID-Block:")

    # SECOND PART
    row = split.row(align=True)
    #row.label(text='f')
    # ID-Type Selector - just have a menu of icons

    # HACK: special group just for the enum,
    # otherwise we get ugly layout with text included too...
    sub = row.row(align=True)
    #sub.row().label(text='')
    sub.prop(data, type_property, icon_only=True, text='')

    # ID-Block Selector - just use pointer widget..
    # HACK: special group to counteract the effects of the previous enum,
    # which now pushes everything too far right.
    sub = row.row(align=True)
    sub.alignment = 'EXPAND'

    type_name = getattr(data, type_property)
    if type_name in id_type_to_collection_name:
        icon = data.bl_rna.properties[type_property].enum_items[type_name].icon
        sub.prop_search(data, property, bpy.data, id_type_to_collection_name[type_name], text='', icon=icon)

class UNIREM_PT_binds(Panel):
    bl_parent_id = 'UNIREM_PT_main_panel'#'UNIREM_PT_bindingsets'
    bl_label = ''
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_options = {'HEADER_LAYOUT_EXPAND'}

    @classmethod
    def poll(cls, context):
        props = context.scene.uremote_props
        '''if len(context.scene.uremote_props.controllers) == 0:
            return False
        controller = props.controllers[props.controller_index]
        if len(controller.inputs) == 0:
            return False'''
        if len(props.bindingsets) == 0:
            return False
        return True
        #bindingset = props.bindingsets[props.bindingsetindex]
    
    def draw_header(self, context):
        layout = self.layout
        layout.alignment = 'EXPAND'
        layout.separator()
        layout.label(text='Binds', icon='RESTRICT_SELECT_OFF')
        op = layout.operator('uremote.textbox', text='', icon='QUESTION')
        layout.separator()
        op.width = 330
        op.text = '''Determine where an input's value should go by assigning it to a bind. You may modify this value through an expression and executable strings to fit your needs.
Reserved Variables: "var" is the assigned input's value. "inputs" is a collection of all inputs through which you may index. Each item has a "value" attribute you may access. "controller" represents the controller bound to the binding set. "bindset" represents the bind set a bind belongs to.'''
        op.size = '53,60'
        op.icons = 'RESTRICT_SELECT_OFF,SCRIPTPLUGINS'
        

    def draw(self, context):
        layout = self.layout
        props = context.scene.uremote_props
        bindingset = props.bindingsets[props.bindingsetindex]
        binds = bindingset.binds
        index = bindingset.bindindex

        row = layout.row()
        col = row.column()
        col.template_list('UNIREM_UL_binds', 'Binds', bindingset, 'binds', bindingset, 'bindindex')

        col = row.column()

        op = col.operator('bind.manipulator', text='', icon='ADD')
        op.operation = 'CHANGE'
        op.Add = True

        op = col.operator('bind.manipulator', text='', icon='REMOVE')
        op.operation = 'CHANGE'
        op.Add = False

        col.separator()

        op = col.operator('bind.manipulator', text='', icon='TRIA_UP')
        op.operation = 'MOVE'
        op.Move = 1

        op = col.operator('bind.manipulator', text='', icon='TRIA_DOWN')
        op.operation = 'MOVE'
        op.Move = -1

        col.operator('uremote.duplicatebind', text='', icon='DUPLICATE')

        if len(binds) == 0:
            return None
        bind = binds[index]

        error = bind.error
        try:
            err_type, msg = bind.error_msg.split('|')
        except:
            print(bind.error_msg)
            raise

        controller = props.controllers['Controller 0']

        if bind.type == 'SCRIPT':
            box = layout.box()
            row = box.row()
            row.label(text='Script to Execute')
            op = row.operator('uremote.textbox', text='', icon='QUESTION')
            op.width = 330
            op.text = 'Enter Python commands to execute before applying values.'
            op.size = '72'
            op.icons = 'NONE'
            row = box.row(align=True)
            row.prop(bind, 'pre_use_block', icon='TEXT', text='', toggle=True)
            if not bind.pre_use_block:
                row.prop(bind, 'pre_exec', text='')
            else:
                row.prop(bind, 'pre_exec_block', text='')

            if error and err_type == 'pre_exec':
                box.alert = True
                box.row().label(text=msg, icon='ERROR')
                box.alert = False

            op.width = 340
            op.text = '''Point to a data block and its property path to set it to the value created by the expression.
    Indices are used if you want to set a single element of an array. If the property you are pointing to is not an array, leave the index blank.
    To get the path of a property: Hover over a property, right click, and select "Copy Data Path." Use "Copy Full Data Path" when using long data paths.'''
            op.size = '64,64,64'
            op.icons = 'SHAPEKEY_DATA,EYEDROPPER,ERROR'
            row.alignment = 'EXPAND'

#            box = layout.box()
#            row = box.row()
#            row.label(text='Data Block Selector')
#            op = row.operator('uremote.textbox', text='', icon='QUESTION')
#            op.width = 340
#            op.text = '''Point to a data block and its property path to set it to the value created by the expression.
#    Indices are used if you want to set a single element of an array. If the property you are pointing to is not an array, leave the index blank.
#    To get the path of a property: Hover over a property, right click, and select "Copy Data Path." Use "Copy Full Data Path" when using long data paths.'''
#            op.size = '64,64,64'
#            op.icons = 'SHAPEKEY_DATA,EYEDROPPER,ERROR'
#            row.alignment = 'EXPAND'
#
#            if not bind.use_long_path:
#                template_any_ID(box, bind, 'id', 'id_type')
#                
#            else:
#                box.row().prop(bind, 'long_data_path')
#
#            box.row().prop(bind, 'use_long_path', text='Use Text-Based Data Block')

            return None
        
        if bind.type != 'SCRIPT':
            box = layout.box()
            box.row().prop_search(bind, 'input', controller, 'inputs')
            col = box.column(align=True)
            col.row().prop(bind, 'multiplier', text='Multiplier')

        ### Space Allocation
        pre_exec = layout.column(align=True).box()
        if bind.type == 'INPUT': expr = layout.column(align=True).box()
        ###
        
        ### Operation
        box = layout.box()
        if bind.type == 'INPUT':
            box.row().label(text='Operation')
            box.row().prop(bind, 'method', expand=True)
        elif bind.type == 'SWITCH':
            box.row().label(text='Switch Properties')
            row = box.row()
            row.prop(bind, 'threshold')
            row.prop(bind, 'toggle')
        #layout.row().split().prop_tabs_enum(bind, 'method')
        ###

        ### Space Allocation
        application = layout.column(align=True).box()
        post_exec = layout.column(align=True).box()
        ###

        ### Pre Execution
        row = pre_exec.row()
        row.row().label(text='Pre-Executable String')
        op = row.operator('uremote.textbox', text='', icon='QUESTION')
        op.width = 330
        op.text = 'Enter Python commands to execute before applying values.'
        op.size = '72'
        op.icons = 'NONE'
        row = pre_exec.row(align=True)
        row.prop(bind, 'pre_use_block', icon='TEXT', text='', toggle=True)
        if not bind.pre_use_block:
            row.prop(bind, 'pre_exec', text='')
        else:
            row.prop(bind, 'pre_exec_block', text='')
        ###

        ### Expression
        if bind.type == 'INPUT':
            row = expr.row()
            row.label(text='Expression')
            op = row.operator('uremote.textbox', text='', icon='QUESTION')
            op.width = 330
            op.text = 'Create an expression to determine a value. This value will be applied to a data path.'
            op.size = '64'
            op.icons = 'NONE'
            row = expr.row(align=True)
            row.prop(bind, 'expression', text='')
        ###

        ### Data Block
        row = application.row()
        row.label(text='Data Block Selector')
        op = row.operator('uremote.add_from_path')
        op = row.operator('uremote.textbox', text='', icon='QUESTION')
        op.width = 340
        op.text = '''Point to a data block and its property path to set it to the value created by the expression.
Indices are used if you want to set a single element of an array. If the property you are pointing to is not an array, leave the index blank.
To get the path of a property: Hover over a property, right click, and select "Copy Data Path." Use "Copy Full Data Path" when using long data paths.'''
        op.size = '64,64,64'
        op.icons = 'SHAPEKEY_DATA,EYEDROPPER,ERROR'
        row.alignment = 'EXPAND'

        if not bind.use_long_path:
            template_any_ID(application, bind, 'id', 'id_type')
            
        else:
            application.row().prop(bind, 'long_data_path')

        row = application.row()
        row.alignment = 'EXPAND'
        row.template_path_builder(bind, 'data_path', bind.id, text='Prop Path')
        row = row.row()
        row.alignment = 'RIGHT'
        row.label(text='Index')
        row = row.row()
        row.prop(bind, 'index', text='')
        row.scale_x = 0.2
        application.row().prop(bind, 'use_long_path', text='Use Text-Based Data Block')
        ###

        ### Post Execution
        row = post_exec.row()
        row.label(text='Post-Executable String')
        op = row.operator('uremote.textbox', text='', icon='QUESTION')
        op.width = 330
        op.text = 'Enter Python commands to execute after applying values.'
        op.size = '64'
        op.icons = 'NONE'
        row = post_exec.row(align=True)
        row.prop(bind, 'post_use_block', text='', icon='TEXT', toggle=True)
        
        if not bind.post_use_block:
            row.prop(bind, 'post_exec', text='')
        else:
            row.prop(bind, 'post_exec_block', text='')
        ###

        if error:
            if err_type == 'pre_exec':
                pre_exec.alert = True
                pre_exec.row().label(text=msg, icon='ERROR')
                pre_exec.alert = False
            
            elif err_type == 'expr':
                expr.alert = True
                expr.row().label(text=msg, icon='ERROR')
                expr.alert = False

            elif err_type == 'application':
                application.alert = True
                application.row().label(text=msg, icon='ERROR')

            else:
                post_exec.alert = True
                post_exec.row().label(text=msg, icon='ERROR')
                post_exec.alert = False


class UNIREM_PT_main_panel(Panel):
    bl_label = 'Universal Remote'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Universal Remote'

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        props = context.scene.uremote_props
        row = box.row()
        row.enabled = not props.running
        row.prop(props, 'rate', text='Polling Rate Hz')
        box.row().prop(props, 'keyframe', text='Keyframe Data Blocks')
        box.row().operator('uremote.startsession')
        box.row().operator('uremote.stop')

        box = layout.box()
        box.prop(props, 'use_udp_server')
        
        col = box.column_flow(columns=2)
        col.label(text='UDP Server')
        col.prop(props, 'udp_addr', text='')
        col.label(text='UDP Port')
        col.prop(props, 'udp_port', text='')
        #box.prop(props, 'pygame_debug')
        #row = box.row().split(factor=0.8)
        #row.prop(props, 'udp_addr')
        #row.prop(props, 'udp_port')
        
        pass
        '''layout = self.layout

        layout.row().operator('uremote.start')
        layout.row().operator('uremote.stop')
        if len(controller.inputs) == 0:
            layout.label(text='No inputs detected!')
        else:
            controller_inps = controller.inputs[controller.input_index]
            layout.row().template_list('UNIREM_UL_input_list', 'Inputs', controller, 'inputs', controller, 'input_index')'''
        #layout.progress()

@persistent
def initializer(dummy = None):
    C = bpy.context
    props = C.scene.uremote_props
    props.running = False
    if props.initialized: return None
    props.initialized = True

    props.controllers.clear()

    for i in range(4):
        new = props.controllers.add()
        new.name = f'Controller {i}'

        for axis in Axes:
            new_inp = new.inputs.add()
            new_inp.name = axis
            new_inp.from_min = -1.0
            new_inp.to_min = -1.0
            new_inp.from_max = 1.0
        
        for trigger in Triggers:
            new_inp = new.inputs.add()
            new_inp.name = trigger

        for button in Buttons:
            new_inp = new.inputs.add()
            new_inp.name = button

        for extra in Extras:
            new_inp = new.inputs.add()
            new_inp.name = extra

classes = [
    Inputs,
    Controllers,
    Binds,
    BindingSets,
    URemoteProps,
    UNIREM_OT_bindingset_manipulator,
    UNIREM_OT_bind_manipulator,
    UNIREM_OT_end,
    UNIREM_OT_runner,
    UNIREM_OT_duplicate_bindset,
    UNIREM_OT_duplicate_bind,
    UNIREM_OT_import_export,
    UNIREM_OT_genericText,
    UNIREM_UL_controller_list,
    UNIREM_UL_input_list,
    UNIREM_UL_bindingsets,
    UNIREM_UL_binds,
    UNIREM_PT_main_panel,
    UNIREM_PT_controllers,
    UNIREM_PT_inputs,
    UNIREM_PT_bindingsets,
    UNIREM_PT_binds,
    UNIREM_OT_add_from_path
]

def register():
    for i in classes:
        register_class(i)
    bpy.types.Scene.uremote_props = bpy.props.PointerProperty(type=URemoteProps)
    bpy.app.handlers.load_post.append(initializer)
    icons.register()

def unregister():
    for i in reversed(classes):
        unregister_class(i)
    bpy.app.handlers.load_post.remove(initializer)
    del bpy.types.Scene.uremote_props
    icons.unregister()