"""
UV Padding Checker - Integrated into MeshChecker
"""
import bpy
import bmesh
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from collections import defaultdict
import numpy as np
from math import inf, floor

# ----------------------------
# GLOBAL SETTINGS
# ----------------------------
class UVPaddingSettings(bpy.types.PropertyGroup):
    texture_resolution: bpy.props.IntProperty(
        name="Texture Resolution",
        description="Target texture resolution in pixels",
        default=2048,
        min=512,
        max=8192
    )
    
    required_padding_px: bpy.props.IntProperty(
        name="Required Padding",
        description="Minimum padding between UV islands in pixels",
        default=8,
        min=1,
        max=64
    )
    
    # Internal settings (not exposed in simplified UI)
    point_size: bpy.props.IntProperty(default=10, min=3, max=20)
    line_width: bpy.props.IntProperty(default=3, min=1, max=10)
    grid_resolution: bpy.props.IntProperty(default=20, min=5, max=100)
    show_edges: bpy.props.BoolProperty(default=True)
    show_points: bpy.props.BoolProperty(default=True)


# ----------------------------
# GLOBAL STATE
# ----------------------------
class GlobalState:
    handle = None
    conflict_edges = []
    conflict_points = []
    is_active = False
    last_check_time = 0.0
    num_violations = 0


# ----------------------------
# CONSTANTS
# ----------------------------
UV_TOLERANCE = 1e-5
CONFLICT_COLOR = (1.0, 0.0, 0.0, 1.0)  # Red
WARNING_COLOR = (1.0, 0.5, 0.0, 1.0)   # Orange


# ----------------------------
# NUMPY-OPTIMIZED DISTANCE FUNCTIONS
# ----------------------------
def segment_to_segment_distance_numpy(edges1, edges2):
    """Vectorized segment-to-segment distance calculation."""
    n = edges1.shape[0]
    m = edges2.shape[0]
    
    a1_x, a1_y, a2_x, a2_y = edges1[:, 0], edges1[:, 1], edges1[:, 2], edges1[:, 3]
    b1_x, b1_y, b2_x, b2_y = edges2[:, 0], edges2[:, 1], edges2[:, 2], edges2[:, 3]
    
    a1_x, a1_y = a1_x[:, None], a1_y[:, None]
    a2_x, a2_y = a2_x[:, None], a2_y[:, None]
    b1_x, b1_y = b1_x[None, :], b1_y[None, :]
    b2_x, b2_y = b2_x[None, :], b2_y[None, :]
    
    # Distance from a1 to segment b
    ab_x, ab_y = b2_x - b1_x, b2_y - b1_y
    ab_len_sq = np.maximum(ab_x**2 + ab_y**2, 1e-10)
    
    ap_x, ap_y = a1_x - b1_x, a1_y - b1_y
    t1 = np.clip((ap_x * ab_x + ap_y * ab_y) / ab_len_sq, 0, 1)
    proj1_x, proj1_y = b1_x + t1 * ab_x, b1_y + t1 * ab_y
    dist1 = np.sqrt((a1_x - proj1_x)**2 + (a1_y - proj1_y)**2)
    
    # Distance from a2 to segment b
    ap_x, ap_y = a2_x - b1_x, a2_y - b1_y
    t2 = np.clip((ap_x * ab_x + ap_y * ab_y) / ab_len_sq, 0, 1)
    proj2_x, proj2_y = b1_x + t2 * ab_x, b1_y + t2 * ab_y
    dist2 = np.sqrt((a2_x - proj2_x)**2 + (a2_y - proj2_y)**2)
    
    # Distance from b1 to segment a
    ab_x, ab_y = a2_x - a1_x, a2_y - a1_y
    ab_len_sq = np.maximum(ab_x**2 + ab_y**2, 1e-10)
    
    ap_x, ap_y = b1_x - a1_x, b1_y - a1_y
    t3 = np.clip((ap_x * ab_x + ap_y * ab_y) / ab_len_sq, 0, 1)
    proj3_x, proj3_y = a1_x + t3 * ab_x, a1_y + t3 * ab_y
    dist3 = np.sqrt((b1_x - proj3_x)**2 + (b1_y - proj3_y)**2)
    
    # Distance from b2 to segment a
    ap_x, ap_y = b2_x - a1_x, b2_y - a1_y
    t4 = np.clip((ap_x * ab_x + ap_y * ab_y) / ab_len_sq, 0, 1)
    proj4_x, proj4_y = a1_x + t4 * ab_x, a1_y + t4 * ab_y
    dist4 = np.sqrt((b2_x - proj4_x)**2 + (b2_y - proj4_y)**2)
    
    return np.minimum(np.minimum(dist1, dist2), np.minimum(dist3, dist4))


# ----------------------------
# SPATIAL HASHING
# ----------------------------
class SpatialHashGrid:
    """Spatial hash grid for fast proximity queries."""
    
    def __init__(self, resolution, required_padding):
        self.resolution = resolution
        self.required_padding = required_padding
        self.grid = defaultdict(list)
    
    def _hash(self, x, y):
        return (int(floor(x * self.resolution)), int(floor(y * self.resolution)))
    
    def insert_edge(self, edge_data, island_id):
        uv1, uv2 = edge_data[0], edge_data[1]
        
        min_x = min(uv1.x, uv2.x) - self.required_padding
        max_x = max(uv1.x, uv2.x) + self.required_padding
        min_y = min(uv1.y, uv2.y) - self.required_padding
        max_y = max(uv1.y, uv2.y) + self.required_padding
        
        gx_min = int(floor(min_x * self.resolution))
        gx_max = int(floor(max_x * self.resolution))
        gy_min = int(floor(min_y * self.resolution))
        gy_max = int(floor(max_y * self.resolution))
        
        cells = set()
        for gx in range(gx_min, gx_max + 1):
            for gy in range(gy_min, gy_max + 1):
                cells.add((gx, gy))
        
        for cell in cells:
            self.grid[cell].append((edge_data, island_id))
    
    def get_candidates(self, edge_data, island_id):
        uv1, uv2 = edge_data[0], edge_data[1]
        
        min_x = min(uv1.x, uv2.x) - self.required_padding
        max_x = max(uv1.x, uv2.x) + self.required_padding
        min_y = min(uv1.y, uv2.y) - self.required_padding
        max_y = max(uv1.y, uv2.y) + self.required_padding
        
        gx_min = int(floor(min_x * self.resolution))
        gx_max = int(floor(max_x * self.resolution))
        gy_min = int(floor(min_y * self.resolution))
        gy_max = int(floor(max_y * self.resolution))
        
        candidates = []
        seen = set()
        
        for gx in range(gx_min, gx_max + 1):
            for gy in range(gy_min, gy_max + 1):
                cell = (gx, gy)
                if cell in self.grid:
                    for other_edge, other_id in self.grid[cell]:
                        if other_id != island_id:
                            edge_key = id(other_edge)
                            if edge_key not in seen:
                                seen.add(edge_key)
                                candidates.append(other_edge)
        
        return candidates


# ----------------------------
# UV ISLAND DETECTION
# ----------------------------
def build_uv_islands_fast(bm, uv_layer):
    """Fast UV island detection."""
    visited = set()
    islands = []
    
    for face in bm.faces:
        if face in visited:
            continue
        
        queue = [face]
        island = []
        visited.add(face)
        head = 0
        
        while head < len(queue):
            current_face = queue[head]
            head += 1
            island.append(current_face)
            
            for loop in current_face.loops:
                uv_coord = loop[uv_layer].uv
                
                for linked_face in loop.vert.link_faces:
                    if linked_face in visited:
                        continue
                    
                    for linked_loop in linked_face.loops:
                        if linked_loop.vert == loop.vert:
                            linked_uv = linked_loop[uv_layer].uv
                            if (linked_uv - uv_coord).length < UV_TOLERANCE:
                                visited.add(linked_face)
                                queue.append(linked_face)
                                break
        
        islands.append(island)
    
    return islands


# ----------------------------
# BOUNDARY EDGE EXTRACTION
# ----------------------------
def get_boundary_edges_fast(island, uv_layer):
    """Fast boundary edge extraction."""
    edge_usage = defaultdict(int)
    edge_data = {}
    
    for face in island:
        loops = face.loops
        num_loops = len(loops)
        
        for i in range(num_loops):
            l1 = loops[i]
            l2 = loops[(i + 1) % num_loops]
            
            uv1 = l1[uv_layer].uv
            uv2 = l2[uv_layer].uv
            
            edge_key = (
                round(uv1.x * 1000000),
                round(uv1.y * 1000000),
                round(uv2.x * 1000000),
                round(uv2.y * 1000000)
            )
            if edge_key[0] > edge_key[2] or (edge_key[0] == edge_key[2] and edge_key[1] > edge_key[3]):
                edge_key = (edge_key[2], edge_key[3], edge_key[0], edge_key[1])
            
            edge_usage[edge_key] += 1
            if edge_key not in edge_data:
                edge_data[edge_key] = (uv1.copy(), uv2.copy(), l1, l2)
    
    return [edge_data[k] for k, count in edge_usage.items() if count == 1]


# ----------------------------
# CONFLICT DETECTION
# ----------------------------
def get_padding_conflicts_fast(settings):
    """Find UV padding conflicts."""
    obj = bpy.context.edit_object
    if not obj or obj.type != 'MESH':
        return [], [], "No mesh object selected"
    
    bm = bmesh.from_edit_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    
    if not uv_layer:
        return [], [], "No active UV layer found"
    
    required_padding = settings.required_padding_px / settings.texture_resolution
    
    islands = build_uv_islands_fast(bm, uv_layer)
    
    if len(islands) <= 1:
        return [], [], f"Only {len(islands)} island found - no conflicts possible"
    
    grid = SpatialHashGrid(settings.grid_resolution, required_padding)
    island_edges = []
    total_edges = 0
    
    for island_id, island in enumerate(islands):
        edges = get_boundary_edges_fast(island, uv_layer)
        island_edges.append(edges)
        total_edges += len(edges)
        
        for edge in edges:
            grid.insert_edge(edge, island_id)
    
    violating_edges = []
    violating_points = set()
    checks_performed = 0
    
    for island_id, edges in enumerate(island_edges):
        for edge in edges:
            candidates = grid.get_candidates(edge, island_id)
            
            if not candidates:
                continue
            
            edge_array = np.array([[edge[0].x, edge[0].y, edge[1].x, edge[1].y]])
            candidate_array = np.array([
                [c[0].x, c[0].y, c[1].x, c[1].y] for c in candidates
            ])
            
            distances = segment_to_segment_distance_numpy(edge_array, candidate_array)
            checks_performed += len(candidates)
            
            violations = np.where(distances[0] < required_padding)[0]
            
            for idx in violations:
                candidate = candidates[idx]
                violating_edges.append((edge[0], edge[1], candidate[0], candidate[1]))
                
                violating_points.add((edge[0].x, edge[0].y))
                violating_points.add((edge[1].x, edge[1].y))
                violating_points.add((candidate[0].x, candidate[0].y))
                violating_points.add((candidate[1].x, candidate[1].y))
    
    status = f"Found {len(islands)} islands, {total_edges} boundary edges, {checks_performed:,} checks performed"
    
    return list(violating_edges), [Vector((p[0], p[1])) for p in violating_points], status


# ----------------------------
# GPU DRAWING
# ----------------------------
def draw_callback():
    """Draw conflict visualization."""
    settings = bpy.context.scene.uv_padding_settings
    
    if not GlobalState.conflict_edges and not GlobalState.conflict_points:
        return
    
    region = bpy.context.region
    rv2d = region.view2d
    
    # Draw edges
    if settings.show_edges and GlobalState.conflict_edges:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.line_width_set(settings.line_width)
        
        edge_coords = []
        for edge_data in GlobalState.conflict_edges:
            uv1_a, uv1_b, uv2_a, uv2_b = edge_data
            
            x1, y1 = rv2d.view_to_region(uv1_a.x, uv1_a.y, clip=False)
            x2, y2 = rv2d.view_to_region(uv1_b.x, uv1_b.y, clip=False)
            x3, y3 = rv2d.view_to_region(uv2_a.x, uv2_a.y, clip=False)
            x4, y4 = rv2d.view_to_region(uv2_b.x, uv2_b.y, clip=False)
            
            edge_coords.extend([
                (x1, y1), (x2, y2),
                (x3, y3), (x4, y4)
            ])
        
        if edge_coords:
            batch = batch_for_shader(shader, 'LINES', {"pos": edge_coords})
            shader.bind()
            shader.uniform_float("color", WARNING_COLOR)
            batch.draw(shader)
    
    # Draw points
    if settings.show_points and GlobalState.conflict_points:
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        gpu.state.point_size_set(settings.point_size)
        
        point_coords = []
        for uv in GlobalState.conflict_points:
            x, y = rv2d.view_to_region(uv.x, uv.y, clip=False)
            point_coords.append((x, y))
        
        if point_coords:
            batch = batch_for_shader(shader, 'POINTS', {"pos": point_coords})
            shader.bind()
            shader.uniform_float("color", CONFLICT_COLOR)
            batch.draw(shader)
    
    gpu.state.line_width_set(1.0)


# ----------------------------
# OPERATORS
# ----------------------------
class UV_OT_CheckPadding(bpy.types.Operator):
    """Check UV padding and visualize conflicts"""
    bl_idname = "uv.check_padding"
    bl_label = "Check UV Padding"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        settings = context.scene.uv_padding_settings
        mesh_props = context.scene.mesh_checker_props
        
        import time
        start_time = time.time()
        
        # Get conflicts
        conflict_edges, conflict_points, status = get_padding_conflicts_fast(settings)
        
        elapsed = time.time() - start_time
        GlobalState.last_check_time = elapsed
        
        # Store results
        GlobalState.conflict_edges = conflict_edges
        GlobalState.conflict_points = conflict_points
        GlobalState.num_violations = len(conflict_edges)
        
        # Update mesh checker status
        mesh_props.uv_padding_check.count = len(conflict_edges)
        if conflict_edges:
            mesh_props.uv_padding_check.status = 'ERROR'
            mesh_props.uv_padding_check.message = f"Found {len(conflict_edges)} padding violations"
        else:
            mesh_props.uv_padding_check.status = 'PASS'
            mesh_props.uv_padding_check.message = ""
        
        # Enable drawing if not already active
        if GlobalState.handle is None and (conflict_edges or conflict_points):
            GlobalState.handle = bpy.types.SpaceImageEditor.draw_handler_add(
                draw_callback, (), 'WINDOW', 'POST_PIXEL'
            )
            GlobalState.is_active = True
        
        # Redraw UV editor
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.tag_redraw()
        
        # Report results
        if conflict_edges:
            self.report({'WARNING'}, 
                f"Found {len(conflict_edges)} violations in {elapsed:.2f}s")
        else:
            self.report({'INFO'}, 
                f"✓ No padding violations found! ({elapsed:.2f}s)")
        
        return {'FINISHED'}


class UV_OT_ClearOverlay(bpy.types.Operator):
    """Clear the UV padding overlay"""
    bl_idname = "uv.clear_padding_overlay"
    bl_label = "Clear UV Overlay"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        if GlobalState.handle is not None:
            bpy.types.SpaceImageEditor.draw_handler_remove(GlobalState.handle, 'WINDOW')
            GlobalState.handle = None
            GlobalState.is_active = False
        
        GlobalState.conflict_edges = []
        GlobalState.conflict_points = []
        GlobalState.num_violations = 0
        
        # Redraw UV editor
        for area in context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                area.tag_redraw()
        
        self.report({'INFO'}, "UV overlay cleared")
        return {'FINISHED'}


# Cleanup function for unregister
def cleanup_uv_padding():
    """Clean up UV padding overlay on addon unload."""
    if GlobalState.handle is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(GlobalState.handle, 'WINDOW')
        GlobalState.handle = None
        GlobalState.is_active = False
