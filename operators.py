import bpy
import bmesh
import mathutils
from .utils import bbox_world,set_origin_at_location,ensure_object_mode,face_key,get_ngon_face_indices,is_face_non_planar,get_active_mesh,create_checker_material,UVCheckerProps,get_lowest_slice_origin_position




class MESH_OT_validate_ngons(bpy.types.Operator):
    bl_idname = "mesh.validate_ngons"
    bl_label = "Validate N-Gons"

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.object

        if not obj or obj.type != 'MESH':
            props.ngon_check.status = 'ERROR'
            props.ngon_check.message = "No mesh selected"
            self.report({'ERROR'}, "No mesh selected")
            return {'CANCELLED'}

        ngons = get_ngon_face_indices(obj)
        props.ngon_check.count = len(ngons)

        if ngons:
            props.ngon_check.status = 'ERROR'
            props.ngon_check.message = f"Found {len(ngons)} N-gon faces"
            self.report({'ERROR'}, f"N-Gons found: {len(ngons)}")
        else:
            props.ngon_check.status = 'PASS'
            props.ngon_check.message = ""
            self.report({'INFO'}, "Mesh clean (no N-Gons)")

        return {'FINISHED'}


class MESH_OT_select_ngons(bpy.types.Operator):
    bl_idname = "mesh.select_ngons"
    bl_label = "Select"

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='FACE')

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        count = 0
        for f in bm.faces:
            if len(f.verts) > 4:
                f.select = True
                count += 1

        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {count} N-Gons")
        return {'FINISHED'}


class MESH_OT_triangulate_ngons(bpy.types.Operator):
    bl_idname = "mesh.triangulate_ngons"
    bl_label = "Triangulate"

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.object
        if not obj or obj.type != 'MESH':
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='FACE')

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        faces = [f for f in bm.faces if len(f.verts) > 4]

        if not faces:
            self.report({'INFO'}, "No N-Gons to triangulate")
            return {'FINISHED'}

        bmesh.ops.triangulate(
            bm,
            faces=faces,
            quad_method='BEAUTY',
            ngon_method='BEAUTY'
        )

        bmesh.update_edit_mesh(obj.data)
        
        # Update status after fix
        props.ngon_check.status = 'PASS'
        props.ngon_check.count = 0
        props.ngon_check.message = ""
        
        self.report({'INFO'}, f"Triangulated {len(faces)} N-Gons")
        return {'FINISHED'}


class MESH_OT_check_double_faces(bpy.types.Operator):


    bl_idname = "mesh.check_double_faces"
    bl_label = "Check Double Faces?"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            props.double_faces_check.status = 'ERROR'
            props.double_faces_check.message = "No mesh selected"
            self.report({'ERROR'}, "No mesh selected")
            return {'CANCELLED'}

        ensure_object_mode()
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        face_dict = {}
        double_indices = []

        for f in bm.faces:
            key = face_key(f)
            if key in face_dict:
                double_indices.append(f.index)
            else:
                face_dict[key] = f.index

        bm.free()

        props.double_faces_check.count = len(double_indices)

        if len(double_indices) == 0:
            props.double_faces_check.status = 'PASS'
            props.double_faces_check.message = ""
            self.report({'INFO'}, "No double faces found")
        else:
            props.double_faces_check.status = 'ERROR'
            props.double_faces_check.message = f"Found {len(double_indices)} overlapping faces"
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            for idx in double_indices:
                obj.data.polygons[idx].select = True
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'WARNING'}, f"Found {len(double_indices)} double faces (selected)")

        return {'FINISHED'}


class OBJECT_OT_apply_all_modifiers(bpy.types.Operator):
    bl_idname = "object.apply_all_modifiers_safe"
    bl_label = "Apply All Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj:
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}

        ensure_object_mode()

        modifier_count = len(obj.modifiers)

        while obj.modifiers:
            m = obj.modifiers[0]
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except:
                self.report({'WARNING'}, f"Could not apply modifier: {m.name}")
                obj.modifiers.remove(m)

        self.report({'INFO'}, f"Applied {modifier_count} modifiers")
        return {'FINISHED'}


class OBJECT_OT_apply_all_transforms(bpy.types.Operator):
    bl_idname = "object.apply_all_transforms_with_gizmo"
    bl_label = "Apply All Transforms"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj:
            self.report({'ERROR'}, "No object selected")
            return {'CANCELLED'}

        ensure_object_mode()

        # Apply transforms
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        self.report({'INFO'}, "Transforms applied")
        return {'FINISHED'}


class OBJECT_OT_OriginBBoxBottomCenter(bpy.types.Operator):
    bl_idname = "object.origin_bbox_bottom_center"
    bl_label = "Pivot1"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        ensure_object_mode()
        bbox = bbox_world(obj)

        bottom_center = mathutils.Vector((
            sum(v.x for v in bbox) / 8,
            sum(v.y for v in bbox) / 8,
            min(v.z for v in bbox)
        ))

        set_origin_at_location(obj, bottom_center)
        return {'FINISHED'}


class OBJECT_OT_OriginBBoxMinCorner(bpy.types.Operator):
    bl_idname = "object.origin_bbox_min_corner"
    bl_label = "ModularCorner"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        ensure_object_mode()
        bbox = bbox_world(obj)

        min_corner = mathutils.Vector((
            min(v.x for v in bbox),
            min(v.y for v in bbox),
            min(v.z for v in bbox)
        ))

        set_origin_at_location(obj, min_corner)
        return {'FINISHED'}


class OBJECT_OT_MoveOriginToWorld(bpy.types.Operator):
    bl_idname = "object.move_origin_to_world"
    bl_label = "Centrify"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        world_origin = mathutils.Vector((0.0, 0.0, 0.0))

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue

            offset = world_origin - obj.matrix_world.translation
            obj.location += offset

        context.scene.cursor.location = world_origin
        return {'FINISHED'}

class OBJECT_OT_origin_to_bottom_line(bpy.types.Operator):
    bl_idname = "object.origin_to_bottom_line"
    bl_label = "ModularEdgeCenter"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        # Bounding box in local space
        bbox = [mathutils.Vector(v) for v in obj.bound_box]

        min_y = min(v.y for v in bbox)
        min_z = min(v.z for v in bbox)

        # average x
        avg_x = sum(v.x for v in bbox) / len(bbox)

        new_origin_local = mathutils.Vector((avg_x, min_y, min_z))
        new_origin_world = obj.matrix_world @ new_origin_local

        set_origin_at_location(obj, new_origin_world)
        return {'FINISHED'}



class OBJECT_OT_detect_non_planar(bpy.types.Operator):
    bl_idname = "object.detect_non_planar_faces"
    bl_label = "Detect Non-Planar Faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            props.non_planar_check.status = 'ERROR'
            props.non_planar_check.message = "No mesh selected"
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        ensure_object_mode()
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        non_planar = [f for f in bm.faces if is_face_non_planar(f)]
        
        props.non_planar_check.count = len(non_planar)

        if len(non_planar) == 0:
            props.non_planar_check.status = 'PASS'
            props.non_planar_check.message = ""
            bm.free()
            self.report({'INFO'}, "No non-planar faces found")
        else:
            props.non_planar_check.status = 'ERROR'
            props.non_planar_check.message = f"Found {len(non_planar)} non-planar faces"
            
            for f in bm.faces:
                f.select = False
            for f in non_planar:
                f.select = True

            bm.to_mesh(obj.data)
            bm.free()
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'WARNING'}, f"Found {len(non_planar)} non-planar faces (selected)")

        return {'FINISHED'}


class NM_OT_detect(bpy.types.Operator):
    bl_idname = "mesh.detect_non_manifold"
    bl_label = "Detect Non-Manifold"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            props.non_manifold_check.status = 'ERROR'
            props.non_manifold_check.message = "No mesh selected"
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        # Use bpy.ops for the individual button (this works fine when called directly)
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

        bm = bmesh.from_edit_mesh(obj.data)
        selected_count = sum(1 for v in bm.verts if v.select)
        
        props.non_manifold_check.count = selected_count

        if selected_count == 0:
            props.non_manifold_check.status = 'PASS'
            props.non_manifold_check.message = ""
            self.report({'INFO'}, "No non-manifold geometry found")
        else:
            props.non_manifold_check.status = 'ERROR'
            props.non_manifold_check.message = f"Found {selected_count} non-manifold vertices"
            self.report({'WARNING'}, f"Found {selected_count} non-manifold vertices (selected)")

        return {'FINISHED'}


class UVCHK_OT_apply(bpy.types.Operator):
    bl_idname = "uvchk.apply_checker"
    bl_label = "Apply Checker Material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.uv_checker_props

        if not props.image_path:
            self.report({'ERROR'}, "No checker image path specified")
            return {'CANCELLED'}

        obj = get_active_mesh(context)

        if not obj:
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}

        try:
            mat = create_checker_material(props.image_path, props.uv_scale)

            if len(obj.data.materials) == 0:
                obj.data.materials.append(mat)
            else:
                obj.data.materials[0] = mat

            self.report({'INFO'}, "UV checker material applied")
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}

        return {'FINISHED'}


class UVCHK_OT_reset(bpy.types.Operator):
    bl_idname = "uvchk.reset_material"
    bl_label = "Reset Material"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = get_active_mesh(context)

        if not obj:
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}

        for mat in obj.data.materials:
            if mat and mat.name == "__UV_Checker_Temp__":
                obj.data.materials.clear()
                bpy.data.materials.remove(mat)
                break

        self.report({'INFO'}, "UV checker material removed")
        return {'FINISHED'}


class UVCHK_OT_check_1001(bpy.types.Operator):
    bl_idname = "uvchk.check_1001"
    bl_label = "Check UDIM 1001"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = get_active_mesh(context)

        if not obj:
            props.uv_1001_check.status = 'ERROR'
            props.uv_1001_check.message = "No mesh selected"
            self.report({'ERROR'}, "No active mesh object")
            return {'CANCELLED'}

        if not obj.data.uv_layers:
            props.uv_1001_check.status = 'ERROR'
            props.uv_1001_check.message = "No UV map found"
            self.report({'ERROR'}, "Object has no UV map")
            return {'CANCELLED'}

        uv_layer = obj.data.uv_layers.active.data
        outside_count = 0

        for uv in uv_layer:
            if uv.uv.x < 0 or uv.uv.x > 1 or uv.uv.y < 0 or uv.uv.y > 1:
                outside_count += 1

        props.uv_1001_check.count = outside_count

        if outside_count == 0:
            props.uv_1001_check.status = 'PASS'
            props.uv_1001_check.message = ""
            self.report({'INFO'}, "All UVs within UDIM 1001")
        else:
            props.uv_1001_check.status = 'WARNING'
            props.uv_1001_check.message = f"{outside_count} UVs outside 0-1 range"
            self.report({'WARNING'}, f"{outside_count} UVs outside UDIM 1001")

        return {'FINISHED'}


class CHK_OT_face_orientation(bpy.types.Operator):
    bl_idname = "uvchk.face_orientation"
    bl_label = "Face Orientation"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_face_orientation = not space.overlay.show_face_orientation
                        
                        if space.overlay.show_face_orientation:
                            props.face_orientation_check.status = 'WARNING'
                            props.face_orientation_check.message = "Overlay enabled - check manually"
                            self.report({'INFO'}, "Face orientation overlay enabled")
                        else:
                            props.face_orientation_check.status = 'NONE'
                            props.face_orientation_check.message = ""
                            self.report({'INFO'}, "Face orientation overlay disabled")
                        
                        return {'FINISHED'}

        return {'FINISHED'}


class CHK_OT_show_sharp_edges(bpy.types.Operator):
    bl_idname = "chk.show_sharp_edges"
    bl_label = "Show Sharp Edges"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.overlay.show_edge_sharp = not space.overlay.show_edge_sharp
                        
                        if space.overlay.show_edge_sharp:
                            props.sharp_edges_check.status = 'WARNING'
                            props.sharp_edges_check.message = "Overlay enabled - check manually"
                            self.report({'INFO'}, "Sharp edges overlay enabled")
                        else:
                            props.sharp_edges_check.status = 'NONE'
                            props.sharp_edges_check.message = ""
                            self.report({'INFO'}, "Sharp edges overlay disabled")
                        
                        return {'FINISHED'}

        return {'FINISHED'}


class CHK_OT_zero_geo(bpy.types.Operator):
    bl_idname = "chk.zero_geo"
    bl_label = "Check Zero Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            props.zero_geo_check.status = 'ERROR'
            props.zero_geo_check.message = "No mesh selected"
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        ensure_object_mode()
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        zero_faces = [f for f in bm.faces if f.calc_area() < 0.0001]
        
        props.zero_geo_check.count = len(zero_faces)

        if len(zero_faces) == 0:
            props.zero_geo_check.status = 'PASS'
            props.zero_geo_check.message = ""
            bm.free()
            self.report({'INFO'}, "No zero area faces found")
        else:
            props.zero_geo_check.status = 'ERROR'
            props.zero_geo_check.message = f"Found {len(zero_faces)} degenerate faces"
            
            for f in bm.faces:
                f.select = False
            for f in zero_faces:
                f.select = True

            bm.to_mesh(obj.data)
            bm.free()
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'WARNING'}, f"Found {len(zero_faces)} zero area faces (selected)")

        return {'FINISHED'}


class CHK_OT_show_open_edges(bpy.types.Operator):
    bl_idname = "chk.show_open_edges"
    bl_label = "Show Open Edges"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            props.open_edges_check.status = 'ERROR'
            props.open_edges_check.message = "No mesh selected"
            self.report({'ERROR'}, "No mesh object selected")
            return {'CANCELLED'}

        ensure_object_mode()
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        open_edges = [e for e in bm.edges if e.is_boundary]
        
        props.open_edges_check.count = len(open_edges)

        if len(open_edges) == 0:
            props.open_edges_check.status = 'PASS'
            props.open_edges_check.message = ""
            bm.free()
            self.report({'INFO'}, "No open edges found")
        else:
            props.open_edges_check.status = 'WARNING'
            props.open_edges_check.message = f"Found {len(open_edges)} boundary edges"
            
            for e in bm.edges:
                e.select = False
            for e in open_edges:
                e.select = True

            bm.to_mesh(obj.data)
            bm.free()
            bpy.ops.object.mode_set(mode='EDIT')
            self.report({'INFO'}, f"Found {len(open_edges)} open edges (selected)")

        return {'FINISHED'}


class BBOX_OT_origin_to_lowest_slice(bpy.types.Operator):
    bl_idname = "bbox.origin_to_lowest_slice"
    bl_label = "Pivot2"
    bl_options = {'REGISTER', 'UNDO'}

    slices: bpy.props.IntProperty(name="Slices", default=5, min=2, max=20)

    def execute(self, context):
        obj = context.active_object

        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object")
            return {'CANCELLED'}

        origin_pos = get_lowest_slice_origin_position(obj, self.slices)

        if origin_pos is None:
            self.report({'WARNING'}, "Could not compute lowest slice origin")
            return {'CANCELLED'}

        set_origin_at_location(obj, origin_pos)
        self.report({'INFO'}, f"Origin set to lowest slice ({self.slices} slices)")
        return {'FINISHED'}


# NEW: Check All Operator - FIXED to avoid nested operator calls
class MESH_OT_check_all(bpy.types.Operator):
    bl_idname = "mesh.check_all"
    bl_label = "Run All Checks"
    bl_description = "Run all validation checks at once"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        props = context.scene.mesh_checker_props
        obj = context.active_object
        
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected")
            return {'CANCELLED'}
        
        # Ensure object mode
        ensure_object_mode()
        
        # Run all checks by directly executing check logic
        total_errors = 0
        
        # 1. Check N-gons
        ngons = get_ngon_face_indices(obj)
        props.ngon_check.count = len(ngons)
        if ngons:
            props.ngon_check.status = 'ERROR'
            props.ngon_check.message = f"Found {len(ngons)} N-gon faces"
            total_errors += len(ngons)
        else:
            props.ngon_check.status = 'PASS'
            props.ngon_check.message = ""
        
        # 2. Check Double Faces
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        face_dict = {}
        double_indices = []
        for f in bm.faces:
            key = face_key(f)
            if key in face_dict:
                double_indices.append(f.index)
            else:
                face_dict[key] = f.index
        bm.free()
        
        props.double_faces_check.count = len(double_indices)
        if len(double_indices) == 0:
            props.double_faces_check.status = 'PASS'
            props.double_faces_check.message = ""
        else:
            props.double_faces_check.status = 'ERROR'
            props.double_faces_check.message = f"Found {len(double_indices)} overlapping faces"
            total_errors += len(double_indices)
        
        # 3. Check Non-Planar Faces
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        non_planar = [f for f in bm.faces if is_face_non_planar(f)]
        bm.free()
        
        props.non_planar_check.count = len(non_planar)
        if len(non_planar) == 0:
            props.non_planar_check.status = 'PASS'
            props.non_planar_check.message = ""
        else:
            props.non_planar_check.status = 'ERROR'
            props.non_planar_check.message = f"Found {len(non_planar)} non-planar faces"
            total_errors += len(non_planar)
        
        # 4. Check Non-Manifold - FIXED: Use bmesh directly instead of bpy.ops
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        # Find non-manifold vertices using bmesh
        non_manifold_verts = []
        for v in bm.verts:
            # A vertex is non-manifold if:
            # - It has no edges (isolated vertex)
            # - It has only one edge (wire edge endpoint)
            # - It belongs to edges that don't form a proper fan
            if not v.is_manifold:
                non_manifold_verts.append(v)
        
        # Find non-manifold edges
        non_manifold_edges = []
        for e in bm.edges:
            if not e.is_manifold:
                non_manifold_edges.append(e)
        
        bm.free()
        
        selected_count = len(non_manifold_verts) + len(non_manifold_edges)
        
        props.non_manifold_check.count = selected_count
        if selected_count == 0:
            props.non_manifold_check.status = 'PASS'
            props.non_manifold_check.message = ""
        else:
            props.non_manifold_check.status = 'ERROR'
            props.non_manifold_check.message = f"Found {selected_count} non-manifold elements"
            total_errors += selected_count
        
        # 5. Check Zero Area Faces
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        zero_faces = [f for f in bm.faces if f.calc_area() < 0.0001]
        bm.free()
        
        props.zero_geo_check.count = len(zero_faces)
        if len(zero_faces) == 0:
            props.zero_geo_check.status = 'PASS'
            props.zero_geo_check.message = ""
        else:
            props.zero_geo_check.status = 'ERROR'
            props.zero_geo_check.message = f"Found {len(zero_faces)} degenerate faces"
            total_errors += len(zero_faces)
        
        # 6. Check Open Edges
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        open_edges = [e for e in bm.edges if e.is_boundary]
        bm.free()
        
        props.open_edges_check.count = len(open_edges)
        if len(open_edges) == 0:
            props.open_edges_check.status = 'PASS'
            props.open_edges_check.message = ""
        else:
            props.open_edges_check.status = 'WARNING'
            props.open_edges_check.message = f"Found {len(open_edges)} boundary edges"
        
        # Report results
        if total_errors == 0:
            self.report({'INFO'}, "✓ All checks passed!")
        else:
            self.report({'WARNING'}, f"✗ Found {total_errors} total issues")
        
        return {'FINISHED'}




# ====================================
# FBX EXPORT OPERATOR
# ====================================
class EXPORT_OT_fbx_unreal(bpy.types.Operator):
    bl_idname = "export.fbx_unreal"
    bl_label = "Export to Unreal"
    bl_description = "Export selected objects as FBX with Unreal Engine optimized settings"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        import os
        settings = context.scene.fbx_export_settings
        
        # Validate export directory
        if not settings.export_directory:
            self.report({'ERROR'}, "Please set an export directory")
            return {'CANCELLED'}
        
        # Get selected objects
        selected = context.selected_objects
        if not selected:
            self.report({'ERROR'}, "No objects selected for export")
            return {'CANCELLED'}
        
        # Get active object name for filename
        if context.active_object:
            filename = context.active_object.name
        else:
            filename = selected[0].name
        
        # Clean filename
        filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).strip()
        if not filename:
            filename = "export"
        
        # Build full path
        export_dir = bpy.path.abspath(settings.export_directory)
        
        # Create directory if it doesn't exist
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except:
                self.report({'ERROR'}, f"Could not create directory: {export_dir}")
                return {'CANCELLED'}
        
        # Build filepath
        export_path = os.path.join(export_dir, filename + ".fbx")
        
        try:
            # Export with Unreal Engine optimized settings
            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,  # Only selected objects
                
                # Transform settings
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',
                
                # Axis conversion for Unreal (Z-up, Y-forward)
                axis_forward='-Z',
                axis_up='Y',
                
                # Mesh settings
                use_mesh_modifiers=True,  # Always apply modifiers
                mesh_smooth_type='FACE',
                use_mesh_edges=False,
                use_tspace=True,  # Tangent space for normal maps
                
                # Animation settings
                bake_anim=False,
                
                # Armature settings
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                armature_nodetype='NULL',
                
                # Additional settings
                use_custom_props=False,
                add_leaf_bones=False,
                bake_space_transform=False,
                object_types={'MESH', 'ARMATURE', 'EMPTY'},
                
                # Compatibility
                path_mode='AUTO',
                embed_textures=False,
                batch_mode='OFF',
            )
            
            self.report({'INFO'}, f"✓ Exported: {filename}.fbx")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}


class EXPORT_OT_browse_directory(bpy.types.Operator):
    bl_idname = "export.browse_fbx_directory"
    bl_label = "Browse"
    bl_description = "Browse for export directory"
    
    directory: bpy.props.StringProperty(subtype="DIR_PATH")
    
    def execute(self, context):
        settings = context.scene.fbx_export_settings
        settings.export_directory = self.directory
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ====================================
# UV GRID SETUP OPERATOR
# ====================================
class UV_OT_set_grid(bpy.types.Operator):
    bl_idname = "uv.set_custom_grid"
    bl_label = "Set Grid"
    bl_description = "Set UV grid to fixed mode with 256x256 subdivisions (keep islands 2 units apart)"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Check if we're in the UV editor
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                for space in area.spaces:
                    if space.type == 'IMAGE_EDITOR':
                        # Set grid to fixed mode
                        space.uv_editor.grid_shape_source = 'FIXED'
                        
                        # Set custom grid subdivisions
                        space.uv_editor.custom_grid_subdivisions[0] = 256
                        space.uv_editor.custom_grid_subdivisions[1] = 256
                        
                        # Redraw the area
                        area.tag_redraw()
                        
                        self.report({'INFO'}, "UV grid set to 256x256 (2 units apart)")
                        return {'FINISHED'}
        
        self.report({'WARNING'}, "Please run this from UV Editor")
        return {'CANCELLED'}


# ====================================
# FBX EXPORT OPERATOR
# ====================================
class EXPORT_OT_fbx_unreal(bpy.types.Operator):
    """Export FBX with Unreal Engine settings"""
    bl_idname = "export.fbx_unreal"
    bl_label = "Export FBX for Unreal"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        export_props = context.scene.fbx_export_props
        
        if not export_props.export_path:
            self.report({'ERROR'}, "Please set an export path first")
            return {'CANCELLED'}
        
        # Get selected objects
        selected = context.selected_objects
        if not selected:
            self.report({'ERROR'}, "No objects selected")
            return {'CANCELLED'}
        
        # Construct full path
        import os
        export_path = bpy.path.abspath(export_props.export_path)
        
        # Add .fbx extension if not present
        if not export_path.lower().endswith('.fbx'):
            export_path += '.fbx'
        
        # Create directory if it doesn't exist
        directory = os.path.dirname(export_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        try:
            # Export with Unreal Engine settings
            bpy.ops.export_scene.fbx(
                filepath=export_path,
                use_selection=True,
                global_scale=1.0,
                apply_unit_scale=True,
                apply_scale_options='FBX_SCALE_NONE',
                bake_space_transform=False,
                object_types={'MESH', 'ARMATURE', 'EMPTY'},
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='FACE',
                use_mesh_edges=False,
                use_tspace=False,
                use_custom_props=False,
                add_leaf_bones=True,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_armature_deform_only=True,
                armature_nodetype='NULL',
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=True,
                bake_anim_use_all_actions=True,
                bake_anim_force_startend_keying=True,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=1.0,
                path_mode='AUTO',
                embed_textures=False,
                batch_mode='OFF',
                use_batch_own_dir=True,
                axis_forward='-Z',
                axis_up='Y'
            )
            
            self.report({'INFO'}, f"✓ Exported to: {export_path}")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}


# ====================================
# UV GRID SETTER OPERATOR
# ====================================
class UV_OT_set_grid(bpy.types.Operator):
    """Set UV grid to keep islands 2 units apart (256x256 subdivisions)"""
    bl_idname = "uv.set_grid_spacing"
    bl_label = "Set Grid (2 units apart)"
    bl_description = "Set UV grid subdivisions to help keep islands 2 units apart"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Find UV editor
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                space = area.spaces.active
                if space.type == 'IMAGE_EDITOR':
                    # Set grid to fixed with custom subdivisions
                    space.uv_editor.grid_shape_source = 'FIXED'
                    space.uv_editor.custom_grid_subdivisions[0] = 256
                    space.uv_editor.custom_grid_subdivisions[1] = 256
                    
                    self.report({'INFO'}, "✓ UV grid set to 256x256 (2 units apart)")
                    return {'FINISHED'}
        
        self.report({'WARNING'}, "UV Editor not found - open UV Editor and try again")
        return {'CANCELLED'}
