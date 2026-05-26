bl_info = {
    "name": "MeshChecker",
    "author": "Suman Ghosh",
    "version": (2, 2, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N Panel > MeshChecker",
    "description": "Advanced checklist before export with error tracking, visual feedback, UV padding check, and Unreal FBX export",
    "category": "Mesh",
}

import bpy
from bpy.props import PointerProperty

from .operators import (
    MESH_OT_validate_ngons,
    MESH_OT_select_ngons,
    MESH_OT_triangulate_ngons,
    MESH_OT_check_double_faces,
    MESH_OT_check_all,
    OBJECT_OT_apply_all_modifiers,
    OBJECT_OT_apply_all_transforms,
    OBJECT_OT_OriginBBoxMinCorner,
    OBJECT_OT_MoveOriginToWorld,
    OBJECT_OT_OriginBBoxBottomCenter,
    OBJECT_OT_origin_to_bottom_line,
    OBJECT_OT_detect_non_planar,
    NM_OT_detect,
    UVCHK_OT_apply,
    UVCHK_OT_reset,
    UVCHK_OT_check_1001,
    CHK_OT_face_orientation,
    CHK_OT_show_sharp_edges,
    CHK_OT_zero_geo,
    CHK_OT_show_open_edges,
    BBOX_OT_origin_to_lowest_slice,
    EXPORT_OT_fbx_unreal,
    UV_OT_set_grid,
)

from .ui import (
    VIEW3D_PT_ngon_validator,
    VIEW3D_PT_error_summary,
    UVCHK_PT_panel,
)

from .utils import UVCheckerProps, MeshCheckerProps, CheckResult, FBXExportProps

from .uv_padding import (
    UVPaddingSettings,
    UV_OT_CheckPadding,
    UV_OT_ClearOverlay,
    cleanup_uv_padding,
)


classes = (
    CheckResult,
    MeshCheckerProps,
    UVCheckerProps,
    UVPaddingSettings,
    FBXExportProps,
    MESH_OT_validate_ngons,
    MESH_OT_select_ngons,
    MESH_OT_triangulate_ngons,
    MESH_OT_check_double_faces,
    MESH_OT_check_all,
    OBJECT_OT_apply_all_modifiers,
    OBJECT_OT_apply_all_transforms,
    OBJECT_OT_OriginBBoxMinCorner,
    OBJECT_OT_MoveOriginToWorld,
    OBJECT_OT_OriginBBoxBottomCenter,
    OBJECT_OT_origin_to_bottom_line,
    OBJECT_OT_detect_non_planar,
    NM_OT_detect,
    UVCHK_OT_apply,
    UVCHK_OT_reset,
    UVCHK_OT_check_1001,
    CHK_OT_face_orientation,
    CHK_OT_show_sharp_edges,
    CHK_OT_zero_geo,
    CHK_OT_show_open_edges,
    BBOX_OT_origin_to_lowest_slice,
    UV_OT_CheckPadding,
    UV_OT_ClearOverlay,
    EXPORT_OT_fbx_unreal,
    UV_OT_set_grid,
    VIEW3D_PT_ngon_validator,
    VIEW3D_PT_error_summary,
    UVCHK_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mesh_checker_props = PointerProperty(type=MeshCheckerProps)
    bpy.types.Scene.uv_checker_props = PointerProperty(type=UVCheckerProps)
    bpy.types.Scene.uv_padding_settings = PointerProperty(type=UVPaddingSettings)
    bpy.types.Scene.fbx_export_props = PointerProperty(type=FBXExportProps)


def unregister():
    # Clean up UV padding overlay
    cleanup_uv_padding()
    
    del bpy.types.Scene.mesh_checker_props
    del bpy.types.Scene.uv_checker_props
    del bpy.types.Scene.uv_padding_settings
    del bpy.types.Scene.fbx_export_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
