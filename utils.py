import bpy
import bmesh
import mathutils
from mathutils import Vector
import os


# ------------------------
# GENERAL UTILS
# ------------------------

def ensure_object_mode():
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')


def bbox_world(obj):
    return [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]


def set_origin_at_location(obj, location):
    scene = bpy.context.scene
    cursor = scene.cursor
    cursor.location = location
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


def face_key(face):
    center = face.calc_center_median()
    normal = face.normal.normalized()
    return (
        tuple(round(v, 5) for v in center),
        tuple(round(v, 5) for v in normal),
        len(face.verts)
    )


def get_ngon_face_indices(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    ngons = [f.index for f in bm.faces if len(f.verts) > 4]
    bm.free()
    return ngons


# ------------------------
# GEOMETRY CHECKS
# ------------------------

THRESHOLD = 1e-5

def is_face_non_planar(face):
    if len(face.verts) <= 3:
        return False

    p0, p1, p2 = [v.co for v in face.verts[:3]]
    normal = (p1 - p0).cross(p2 - p0)

    if normal.length == 0:
        return False

    normal.normalize()

    for v in face.verts[3:]:
        if abs((v.co - p0).dot(normal)) > THRESHOLD:
            return True

    return False


def select_non_manifold(context):
    ensure_object_mode()
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold(
        use_wire=True,
        use_boundary=True,
        use_multi_face=True,
        use_non_contiguous=True,
        use_verts=True,
    )


# ------------------------
# UV CHECKER
# ------------------------

def get_active_mesh(context):
    obj = context.active_object
    return obj if obj and obj.type == 'MESH' else None


def create_checker_material(image_path, scale):
    img = bpy.data.images.load(image_path, check_existing=True)

    mat = bpy.data.materials.new("__UV_Checker_Temp__")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    tex = nodes.new("ShaderNodeTexImage")
    mapping = nodes.new("ShaderNodeMapping")
    uv = nodes.new("ShaderNodeTexCoord")

    tex.image = img
    tex.interpolation = 'Closest'
    mapping.inputs["Scale"].default_value = (scale, scale, scale)

    links.new(uv.outputs["UV"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    return mat


def get_lowest_slice_origin_position(obj, slices=5):
    # ---- FIRST BBOX (WORLD)
    bbox_world_coords = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    z_vals = [v.z for v in bbox_world_coords]

    z_min = min(z_vals)
    z_max = max(z_vals)
    z_step = (z_max - z_min) / slices
    z_limit = z_min + z_step

    # ---- SELECT LOWEST SLICE
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)

    for f in bm.faces:
        f.select = False

    for f in bm.faces:
        wc = obj.matrix_world @ f.calc_center_median()
        if wc.z <= z_limit:
            f.select = True

    bmesh.update_edit_mesh(obj.data)

    # ---- SECOND BBOX FROM SELECTION
    coords = []
    for f in bm.faces:
        if f.select:
            for v in f.verts:
                coords.append(obj.matrix_world @ v.co)

    if not coords:
        bpy.ops.object.mode_set(mode='OBJECT')
        return None

    bb_min = Vector((
        min(v.x for v in coords),
        min(v.y for v in coords),
        min(v.z for v in coords),
    ))

    bb_max = Vector((
        max(v.x for v in coords),
        max(v.y for v in coords),
        max(v.z for v in coords),
    ))

    bpy.ops.object.mode_set(mode='OBJECT')

    # -Z face center
    return Vector((
        (bb_min.x + bb_max.x) * 0.5,
        (bb_min.y + bb_max.y) * 0.5,
        bb_min.z
    ))


# ------------------------
# CHECK RESULT TRACKING
# ------------------------

class CheckResult(bpy.types.PropertyGroup):
    """Stores the result of a single validation check"""
    name: bpy.props.StringProperty(name="Check Name")
    status: bpy.props.EnumProperty(
        name="Status",
        items=[
            ('NONE', 'Not Run', 'Check has not been run'),
            ('PASS', 'Pass', 'Check passed successfully'),
            ('WARNING', 'Warning', 'Check found warnings'),
            ('ERROR', 'Error', 'Check found errors'),
        ],
        default='NONE'
    )
    message: bpy.props.StringProperty(name="Message")
    count: bpy.props.IntProperty(name="Issue Count", default=0)


class MeshCheckerProps(bpy.types.PropertyGroup):
    """Main property group for mesh checker"""
    
    # Check results
    ngon_check: bpy.props.PointerProperty(type=CheckResult)
    double_faces_check: bpy.props.PointerProperty(type=CheckResult)
    non_planar_check: bpy.props.PointerProperty(type=CheckResult)
    non_manifold_check: bpy.props.PointerProperty(type=CheckResult)
    face_orientation_check: bpy.props.PointerProperty(type=CheckResult)
    sharp_edges_check: bpy.props.PointerProperty(type=CheckResult)
    zero_geo_check: bpy.props.PointerProperty(type=CheckResult)
    open_edges_check: bpy.props.PointerProperty(type=CheckResult)
    uv_1001_check: bpy.props.PointerProperty(type=CheckResult)
    uv_padding_check: bpy.props.PointerProperty(type=CheckResult)
    
    # UI options
    show_passed_checks: bpy.props.BoolProperty(
        name="Show Passed Checks",
        description="Display checks that passed successfully",
        default=False
    )
    
    auto_select_errors: bpy.props.BoolProperty(
        name="Auto-Select Errors",
        description="Automatically select problematic geometry when clicking check buttons",
        default=True
    )


class UVCheckerProps(bpy.types.PropertyGroup):
    image_path: bpy.props.StringProperty(
        name="Checker Image",
        subtype='FILE_PATH'
    )
    uv_scale: bpy.props.FloatProperty(
        name="UV Scale",
        default=5.0,
        min=0.01
    )


# UV Padding check result property (added for UV padding integration)
# This is referenced in uv_padding.py


# FBX Export Settings
class FBXExportSettings(bpy.types.PropertyGroup):
    export_directory: bpy.props.StringProperty(
        name="Export Directory",
        description="Directory where FBX files will be saved",
        default="//exports/",
        subtype='DIR_PATH'
    )
class FBXExportSettings(bpy.types.PropertyGroup):
    export_path: bpy.props.StringProperty(
        name="Export Path",
        description="Path where FBX file will be saved",
        default="//",
        subtype='FILE_PATH'
    )
    
    apply_modifiers: bpy.props.BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before export",
        default=True
    )


# FBX Export Properties
class FBXExportProps(bpy.types.PropertyGroup):
    export_path: bpy.props.StringProperty(
        name="Export Path",
        description="Path where FBX will be exported",
        default="//",
        subtype='FILE_PATH'
    )
