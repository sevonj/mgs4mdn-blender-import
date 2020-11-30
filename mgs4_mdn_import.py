bl_info = {
    "name": "MGS4 MDN Import",
    "description": "Imports MDN files from Metal Gear Solid 4.",
    "author": "MyRightArmTheGodHand",
    "version": (0, 0, 1),
    "blender": (2, 80, 0), # I have no clue on compatibility. I'm running this on 2.90.10.
    "category": "Import-Export"
    }
import bpy
import struct
import os.path
from bpy.props import CollectionProperty

def read_byte(file_object, endian = '>'):
    data = struct.unpack(endian+'B', file_object.read(1))[0]
    return data
def read_short(file_object, endian = '>'):
    data = struct.unpack(endian+'H', file_object.read(2))[0]
    return data
def read_uint(file_object, endian = '>'):
    data = struct.unpack(endian+'I', file_object.read(4))[0]
    return data
def read_int(file_object, endian = '>'):
    data = struct.unpack(endian+'i', file_object.read(4))[0]
    return data
def read_float(file_object, endian = '>'):
    data = struct.unpack(endian+'f', file_object.read(4))[0]
    return data
def read_half(file_object):
    float16 = read_short(file_object)
    s = int((float16 >> 15) & 0x00000001)    # sign
    e = int((float16 >> 10) & 0x0000001f)    # exponent
    f = int(float16 & 0x000003ff)            # fraction
    if e == 0:
        if f == 0:
            return int(s << 31)
        else:
            while not (f & 0x00000400):
                f = f << 1
                e -= 1
            e += 1
            f &= ~0x00000400
    elif e == 31:
        if f == 0:
            return int((s << 31) | 0x7f800000)
        else:
            return int((s << 31) | 0x7f800000 | (f << 13))
    e = e + (127 -15)
    f = f << 13
    temp = int((s << 31) | (e << 23) | f)
    str = struct.pack('I',temp)
    return struct.unpack('f',str)[0]

class VertIndex:
    MeshGroupIndex: int
    unknown: int
    FaceSectionCount: int
    FaceSectionStart: int
    VertId: int
    BonePalletId: int
    VertCount: int
    nullbytes: int
    MaxX: float
    MaxY: float
    MaxZ: float
    MaxW: float
    MinX: float
    MinY: float
    MinZ: float
    MinW: float
    PosX: float
    PosY: float
    PosZ: float
    PosW: float
class VertDef:
    nullbytes: int
    DefCount: int
    Size: int
    Start: int
    Definition: bytearray
    Position: bytearray
class FaceIndex:
    Type: int
    Count: int
    Offset: int
    MatGroup: int
    Start: int
    Size: int
class Mesh:
    Verts = []
    Edges = []
    Faces = []
    uvs = []

def read_some_data(context, filepath, use_some_setting):
    print()
    print("Opening file: ", filepath)
    f = open(filepath, 'rb')
    

    # --- Get Header Data --- #
    mdn_magicbyte               = f.read(4)
    fname                       = read_uint(f)
    mdn_filename = '{:0>8}'.format('{:x}'.format(fname))
    
    mdn_BoneCount               = read_uint(f)
    mdn_MeshGroupCount          = read_uint(f)
    mdn_MeshCount               = read_uint(f)
    mdn_FaceIndexCount          = read_uint(f)
    mdn_VertDefCount            = read_uint(f)
    mdn_MaterialCount           = read_uint(f)
    mdn_TextureCount            = read_uint(f)
    mdn_BonePalletCount         = read_uint(f)
     
    mdn_BoneOffset              = read_uint(f)
    mdn_MeshGroupOffset         = read_uint(f)
    mdn_VertIndexOffset         = read_uint(f)
    mdn_FaceIndexOffset         = read_uint(f)
    mdn_VertDefOffset           = read_uint(f)
    mdn_MaterialOffset          = read_uint(f)
    mdn_TextureOffset           = read_uint(f)
    mdn_BonePalletOffset        = read_uint(f)
    
    mdn_VertBufferOffset        = read_uint(f)
    mdn_VertBufferSize          = read_uint(f)
    mdn_FaceBufferOffset        = read_uint(f)
    mdn_FaceBufferSize          = read_uint(f)
    mdn_nullbytes               = read_uint(f)
    mdn_filesize                = read_uint(f)
    
    #   _______
    #   \     /
    #    \   /
    #     \_/     Some of this data may be labeled incorrectly
    #      _      (materials and textures are likely at least)
    #     (_)
    #
    
    print()
    print("--- Header data ---")
    print("Magic Bytes:           ", mdn_magicbyte.decode('utf-8'))
    print("Filename               ", mdn_filename)
    print()
    print("Count Bones:           ", mdn_BoneCount)
    print("Count MeshGroups:      ", mdn_MeshGroupCount)
    print("Count Mesh:            ", mdn_MeshCount)
    print("Count Face Index:      ", mdn_FaceIndexCount)
    print("Count Vert Definition: ", mdn_VertDefCount)
    print("Count Materials:       ", mdn_MaterialCount)
    print("Count Textures:        ", mdn_TextureCount)
    print("Count Bone Pallet:     ", mdn_BonePalletCount)
    print()
    print("Offset Bones:          ", hex(mdn_BoneOffset))
    print("Offset MeshGroups:     ", hex(mdn_MeshGroupOffset))
    print("Offset Vert Index:     ", hex(mdn_VertIndexOffset))
    print("Offset Face Index:     ", hex(mdn_FaceIndexOffset))
    print("Offset Vert Definition:", hex(mdn_VertDefOffset))
    print("Offset Materials:      ", hex(mdn_MaterialOffset))
    print("Offset Textures:       ", hex(mdn_TextureOffset))
    print("Offset Bone Pallet:    ", hex(mdn_BonePalletOffset))
    print()
    print("Offset Vertex Buffer:  ", hex(mdn_VertBufferOffset))
    print("Size of Vertex Buffer: ", hex(mdn_VertBufferSize))
    print("Offset FaceBuffer      ", hex(mdn_FaceBufferOffset))
    print("Size of FaceBuffer     ", hex(mdn_FaceBufferSize))
    print("nullbytes              ", hex(mdn_nullbytes))
    print("Filesize:              ", hex(mdn_filesize))
    
    
    # --- other --- #
    meshes = []
    
    
    # --- bonestuff here --- #
    """
    bpy.ops.object.add(type='ARMATURE', enter_editmode=True)
    object = bpy.context.object
    object.name = 'name'
    armature = object.data
    armature.name = 'name'
    
    
    
    
    f.seek(mdn_BoneOffset)
    for i in range(mdn_BoneCount):
        name = read_uint(f)
        y0 = read_uint(f)
        parent = read_uint(f)
        w0 = read_uint(f)
        rotx = read_float(f)
        roty = read_float(f)
        rotz = read_float(f)
        rotw = read_float(f)
        posx = read_float(f) / 1000
        posy = read_float(f) / 1000
        posz = read_float(f) / 1000
        posw = read_float(f)
        
        minx = read_float(f) / 1000
        miny = read_float(f) / 1000
        minz = read_float(f) / 1000
        minw = read_float(f) / 1000
        maxx = read_float(f) / 1000
        maxy = read_float(f) / 1000
        maxz = read_float(f) / 1000
        maxw = read_float(f) / 1000
        
        print(i)
        
        print(name)
        print(y0)
        print(parent)
        print(w0)
        print(rotx)
        print(roty)
        print(rotz)
        print(rotw)
        print(posx)
        print(posy)
        print(posz)
        print(posw)
        
        print(minx)
        print(miny)
        print(minz)
        print(minw)
        print(maxx)
        print(maxy)
        print(maxz)
        print(maxw)
        
        bone = armature.edit_bones.new(str(name))
        bone.head = (posx, posy, posz)
    """

    # --- Vert Index --- #
    f.seek(mdn_VertIndexOffset)
    vertindexes = []
    for i in range (mdn_MeshCount):
        vertindex = VertIndex()
        vertindex.MeshGroupIndex = read_uint(f)
        vertindex.unknown = read_uint(f)
        vertindex.FaceSectionCount = read_uint(f)
        vertindex.FaceSectionStart = read_uint(f)
        vertindex.VertId = read_uint(f)
        vertindex.BonePalletId = read_uint(f)
        vertindex.VertCount = read_uint(f)
        vertindex.nullBytes = read_uint(f)
        vertindex.MaxX = read_float(f)
        vertindex.MaxY = read_float(f)
        vertindex.MaxZ = read_float(f)
        vertindex.MaxW = read_float(f)
        vertindex.MinX = read_float(f)
        vertindex.MinY = read_float(f)
        vertindex.MinZ = read_float(f)
        vertindex.MinW = read_float(f)
        vertindex.PosX = read_float(f)
        vertindex.PosY = read_float(f)
        vertindex.PosZ = read_float(f)
        vertindex.PosW = read_float(f)
        vertindexes.append(vertindex)
    
    
    # --- Vertex Def --- #
    f.seek(mdn_VertDefOffset)
    vertdefs = []
    for i in range (mdn_VertDefCount):
        vert = VertDef()
        vert.nullbytes = read_uint(f)
        vert.DefCount = read_uint(f)
        vert.Size = read_uint(f)
        vert.Start = read_uint(f)
        vert.Definition = bytearray()
        vert.Position = bytearray()
        
        for j in range (vert.DefCount):
            vert.Definition.append(read_byte(f))
        f.seek(16 - vert.DefCount, 1)
        
        for j in range (vert.DefCount):
            vert.Position.append(read_byte(f))
        f.seek(16 - vert.DefCount, 1)
        
        vertdefs.append(vert)
    
    
    # --- Vertex Buffer --- #
    meshes = []
    for s in range(mdn_MeshCount):
        f.seek(mdn_VertBufferOffset + vertdefs[s].Start)
        mesh = Mesh()
        verts = []
        uvs = []
        for i in range(vertindexes[s].VertCount):
            start = f.tell()
            for j in range (vertdefs[s].DefCount):
                f.seek (start + vertdefs[s].Position[j])
                if vertdefs[s].Definition[j] == 0x10: # Vert position
                    vert_PosX = -read_float(f) / 1000
                    vert_PosZ = read_float(f) / 1000
                    vert_PosY = read_float(f) / 1000
                    verts.append([vert_PosX,vert_PosY,vert_PosZ])
                elif vertdefs[s].Definition[j] == 0x78: # UV coords
                    u = read_half(f)
                    v = read_half(f)
                    uvs.append([u,v])
            f.seek (start + (vertdefs[s].Size))
        mesh.Verts = verts
        mesh.uvs = uvs
        meshes.append(mesh)
    
    
    # --- Face Index --- #
    f.seek(mdn_FaceIndexOffset)
    faceindexes = []
    for i in range (mdn_FaceIndexCount):
        face = FaceIndex()
        face.Type = read_short(f)
        face.Count = read_short(f)
        face.Offset = read_uint(f)
        face.MatGroup = read_uint(f)
        face.Start = read_short(f)
        face.Size = read_short(f)
        faceindexes.append(face)
    
    
    # --- Face Buffer --- #
    f.seek(mdn_FaceBufferOffset)
    for s in range(mdn_MeshCount):
        faces = []
        vindex = vertindexes[s]
        for j in range(vindex.FaceSectionStart, vindex.FaceSectionStart + vindex.FaceSectionCount):
            for k in range(faceindexes[j].Count // 3):
                faces.append([read_short(f),read_short(f),read_short(f)])
        meshes[s].Faces = faces
        

    # --- Output --- #
    new_collection = bpy.data.collections.new(mdn_filename)
    bpy.context.scene.collection.children.link(new_collection)
    for i in range(len(meshes)):
        mesh = bpy.data.meshes.new('mesh')
        mesh.from_pydata(meshes[i].Verts, [], meshes[i].Faces)
        mesh.update()
        object = bpy.data.objects.new('obj_' + str(i), mesh)
        new_collection.objects.link(object)
    f.close()


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportSomeData(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import_test.some_data"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Some Data"

    # ImportHelper mixin class uses this
    filename_ext = ".mdn"
    files = CollectionProperty(type=bpy.types.PropertyGroup)

    filter_glob: StringProperty(
        default="*.mdn",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        dirname = os.path.dirname(self.filepath)
        for f in self.files:
            path = os.path.join(dirname, f.name)
            read_some_data(context, path, self.use_setting)
        return {'FINISHED'}


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportSomeData.bl_idname, text="Metal Gear Solid 4 (.mdn)")


def register():
    bpy.utils.register_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportSomeData)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_test.some_data('INVOKE_DEFAULT')