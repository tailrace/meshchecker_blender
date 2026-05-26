import bpy


def draw_check_status(layout, check, check_name, operator_id=None):
    """Draw a check result with color-coded status using Blender's native colored icons"""
    
    row = layout.row(align=True)
    
    # Determine icon based on status - these have native colors in Blender
    if check.status == 'ERROR':
        icon = 'CANCEL'  # Red X icon
        row.alert = True  # Makes the whole row red-tinted
    elif check.status == 'WARNING':
        icon = 'ERROR'  # Orange/yellow warning triangle
    elif check.status == 'PASS':
        icon = 'CHECKMARK'  # Green checkmark (this is naturally green in Blender)
    else:
        icon = 'RADIOBUT_OFF'  # Gray circle for not checked
    
    # Create operator button or label
    if operator_id:
        row.operator(operator_id, text=check_name, icon=icon, emboss=True, depress=False)
    else:
        row.label(text=check_name, icon=icon)
    
    # Show count badge for errors/warnings
    if check.status in {'ERROR', 'WARNING'} and check.count > 0:
        badge_row = row.row(align=True)
        if check.status == 'ERROR':
            badge_row.alert = True
        badge_row.label(text=f"[{check.count}]")
    
    # Show detailed message below
    if check.message and check.status in {'ERROR', 'WARNING'}:
        msg_row = layout.row()
        msg_row.scale_y = 0.7
        msg_row.alignment = 'LEFT'
        if check.status == 'ERROR':
            msg_row.alert = True
        msg_row.label(text=f"    {check.message}", icon='BLANK1')


class VIEW3D_PT_ngon_validator(bpy.types.Panel):
    bl_label = "Mesh Validator"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MeshChecker"

    def draw(self, context):
        layout = self.layout
        props = context.scene.mesh_checker_props
        obj = context.active_object
        
        # Header with object info
        box = layout.box()
        if obj and obj.type == 'MESH':
            box.label(text=f"Active: {obj.name}", icon='MESH_DATA')
        else:
            box.label(text="No mesh selected", icon='ERROR')
            if obj:
                return
        
        layout.separator()
        
        # ======================
        # MODIFIERS & TRANSFORMS - AT THE TOP
        # ======================
        col = layout.column(align=True)
        col.operator("object.apply_all_modifiers_safe", icon='MODIFIER')
        col.operator("object.apply_all_transforms_with_gizmo", icon='EMPTY_ARROWS')

        layout.separator()
        
        # CHECK ALL BUTTON - Prominent
        if obj and obj.type == 'MESH':
            box = layout.box()
            col = box.column(align=True)
            col.scale_y = 1.5
            col.operator("mesh.check_all", icon='CHECKMARK', text="RUN ALL CHECKS")
            
            row = box.row()
            row.prop(props, "show_passed_checks", toggle=True)
            
            layout.separator()

        # ======================
        # VALIDATION CHECKS
        # ======================
        if obj and obj.type == 'MESH':
            box = layout.box()
            box.label(text="Geometry Validation", icon='MESH_CUBE')
            
            col = box.column(align=False)
            
            # N-gons check
            if props.show_passed_checks or props.ngon_check.status != 'PASS':
                draw_check_status(col, props.ngon_check, "N-gons", "mesh.validate_ngons")
                if props.ngon_check.status == 'ERROR':
                    row = col.row(align=True)
                    row.scale_y = 0.9
                    row.operator("mesh.select_ngons", text="Select", icon='RESTRICT_SELECT_OFF')
                    row.operator("mesh.triangulate_ngons", text="Fix", icon='MOD_TRIANGULATE')
                col.separator(factor=0.3)
            
            # Double faces
            if props.show_passed_checks or props.double_faces_check.status != 'PASS':
                draw_check_status(col, props.double_faces_check, "Double Faces", "mesh.check_double_faces")
                col.separator(factor=0.3)
            
            # Non-planar
            if props.show_passed_checks or props.non_planar_check.status != 'PASS':
                draw_check_status(col, props.non_planar_check, "Non-Planar Faces", "object.detect_non_planar_faces")
                col.separator(factor=0.3)
            
            # Non-manifold
            if props.show_passed_checks or props.non_manifold_check.status != 'PASS':
                draw_check_status(col, props.non_manifold_check, "Non-Manifold", "mesh.detect_non_manifold")
                col.separator(factor=0.3)
            
            # Face orientation
            if props.show_passed_checks or props.face_orientation_check.status != 'PASS':
                draw_check_status(col, props.face_orientation_check, "Face Orientation", "uvchk.face_orientation")
                col.separator(factor=0.3)
            
            # Sharp edges
            if props.show_passed_checks or props.sharp_edges_check.status != 'PASS':
                draw_check_status(col, props.sharp_edges_check, "Sharp Edges", "chk.show_sharp_edges")
                col.separator(factor=0.3)
            
            # Zero geometry
            if props.show_passed_checks or props.zero_geo_check.status != 'PASS':
                draw_check_status(col, props.zero_geo_check, "Zero Area Faces", "chk.zero_geo")
                col.separator(factor=0.3)
            
            # Open edges
            if props.show_passed_checks or props.open_edges_check.status != 'PASS':
                draw_check_status(col, props.open_edges_check, "Open Edges", "chk.show_open_edges")
                col.separator(factor=0.3)
            
            # UV Padding check
            if props.show_passed_checks or props.uv_padding_check.status != 'PASS':
                draw_check_status(col, props.uv_padding_check, "UV Padding", "uv.check_padding")
            
            layout.separator()

        # ======================
        # ORIGIN TOOLS - UPDATED LAYOUT
        # ======================
        col = layout.column(align=True)
        
        # Row 1: Pivot1 and Pivot2
        row = col.row(align=True)
        row.operator("object.origin_bbox_bottom_center", text="Pivot1", icon='PIVOT_CURSOR')
        row.operator("bbox.origin_to_lowest_slice", text="Pivot2", icon='PIVOT_CURSOR')

        # Row 2: ModularCorner and ModularEdgeCenter
        row = col.row(align=True)
        row.operator("object.origin_bbox_min_corner", text="ModularCorner", icon='PIVOT_CURSOR')
        row.operator("object.origin_to_bottom_line", text="ModularEdgeCenter", icon='PIVOT_CURSOR')

        # Row 3: Centrify
        col.operator("object.move_origin_to_world", icon='WORLD')

        layout.separator()
        
        # ======================
        # ADDITIONAL CHECKS - Keeping original position
        # ======================
        if obj and obj.type == 'MESH':
            col = layout.column(align=True)
            col.operator("object.detect_non_planar_faces", icon='MESH_GRID')

            col = layout.column(align=True)
            col.operator("mesh.detect_non_manifold", icon='MESH_CUBE')

            layout.separator()
            col = layout.column(align=True)
            col.operator("uvchk.face_orientation", icon='MESH_CUBE')

            layout.separator()

            col = layout.column(align=True)
            col.operator("chk.show_sharp_edges", icon='MOD_DISPLACE')
            col.operator("chk.zero_geo", icon='MOD_CAST')
            col.operator("chk.show_open_edges", icon='MOD_EDGESPLIT')
        
        layout.separator()
        layout.separator()
        
        # ======================
        # FBX EXPORT FOR UNREAL - AT BOTTOM
        # ======================
        box = layout.box()
        box.label(text="Export", icon='EXPORT')
        
        export_props = context.scene.fbx_export_props
        
        col = box.column(align=True)
        col.prop(export_props, "export_path", text="")
        col.operator("export.fbx_unreal", icon='FILE_TICK', text="Export FBX for Unreal")
        
        # Export settings info
        col = box.column(align=True)
        col.scale_y = 0.7
        col.label(text="Unreal Engine Settings:", icon='INFO')
        col.label(text="  • Scale: 1.0")
        col.label(text="  • Forward: -Z, Up: Y")
        col.label(text="  • Add Leaf Bones: Yes")
        col.label(text="  • Bake Animation: Yes")


class VIEW3D_PT_error_summary(bpy.types.Panel):
    """Summary panel showing all errors"""
    bl_label = "Error Summary"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "MeshChecker"
    bl_parent_id = "VIEW3D_PT_ngon_validator"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.mesh_checker_props
        
        checks = [
            ("N-gons", props.ngon_check),
            ("Double Faces", props.double_faces_check),
            ("Non-Planar", props.non_planar_check),
            ("Non-Manifold", props.non_manifold_check),
            ("Face Orientation", props.face_orientation_check),
            ("Sharp Edges", props.sharp_edges_check),
            ("Zero Geometry", props.zero_geo_check),
            ("Open Edges", props.open_edges_check),
            ("UV Padding", props.uv_padding_check),
        ]
        
        error_count = 0
        warning_count = 0
        
        for name, check in checks:
            if check.status == 'ERROR':
                error_count += 1
                row = layout.row()
                row.alert = True
                row.label(text=f"{name}: {check.count} issues", icon='CANCEL')
            elif check.status == 'WARNING':
                warning_count += 1
                row = layout.row()
                row.label(text=f"{name}: {check.count} warnings", icon='ERROR')
        
        if error_count == 0 and warning_count == 0:
            layout.label(text="All checks passed!", icon='CHECKMARK')


class UVCHK_PT_panel(bpy.types.Panel):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'UV Checker'
    bl_label = 'UV Checker'

    def draw(self, context):
        layout = self.layout
        props = context.scene.uv_checker_props
        mesh_props = context.scene.mesh_checker_props
        
        # ======================
        # UV GRID SETTER - AT TOP
        # ======================
        box = layout.box()
        box.label(text="UV Grid Setup", icon='GRID')
        col = box.column(align=True)
        col.operator("uv.set_grid_spacing", icon='SNAP_GRID', text="Set Grid (2 units apart)")
        row = col.row()
        row.scale_y = 0.7
        row.label(text="Sets 256x256 grid to keep islands 2 units apart", icon='INFO')
        
        layout.separator()
        layout.separator()
        
        # ======================
        # UV CHECKER - ORIGINAL
        # ======================
        layout.prop(props, "image_path")
        layout.prop(props, "uv_scale")

        layout.operator("uvchk.apply_checker")
        layout.operator("uvchk.reset_material")

        layout.separator()
        
        # UV 1001 Check with status
        if mesh_props.uv_1001_check.status != 'PASS' or mesh_props.show_passed_checks:
            draw_check_status(layout, mesh_props.uv_1001_check, "Check UDIM 1001", "uvchk.check_1001")
        
        layout.separator()
        layout.separator()
        
        # ======================
        # UV PADDING CHECKER
        # ======================
        box = layout.box()
        box.label(text="UV Padding Checker", icon='MESH_GRID')
        
        # Check if properties exist
        if hasattr(context.scene, 'uv_padding_settings'):
            uv_padding_settings = context.scene.uv_padding_settings
            
            col = box.column(align=True)
            col.prop(uv_padding_settings, "texture_resolution")
            col.prop(uv_padding_settings, "required_padding_px")
            
            layout.separator()
            
            col = box.column(align=True)
            col.scale_y = 1.3
            col.operator("uv.check_padding", icon='VIEWZOOM', text="Check UV Padding")
            col.operator("uv.clear_padding_overlay", icon='X', text="Clear Overlay")
        else:
            box.label(text="UV Padding settings not loaded", icon='ERROR')
