links:
artstation: https://www.artstation.com/sumanhere
instagram: https://www.instagram.com/sumanghost/
mail: rrip1suman@gmail.com


# MeshChecker v2.0 - Advanced Mesh Validation for Blender

An enhanced Blender addon for comprehensive mesh validation before export, featuring error tracking, visual feedback, and batch checking.

## Features

### ✅ Validation Checks
- **N-gons Detection** - Find faces with more than 4 vertices
- **Double Faces** - Detect overlapping/duplicate faces
- **Non-Planar Faces** - Check for non-flat faces
- **Non-Manifold Geometry** - Find problematic mesh topology
- **Zero Area Faces** - Detect degenerate geometry
- **Open Edges** - Find boundary edges
- **Face Orientation** - Visual overlay for normal direction
- **Sharp Edges** - Display sharp edge overlay
- **UV UDIM Check** - Verify UVs are within 0-1 range

### 🎨 Enhanced UI
- **Color-Coded Status** - Red for errors, green for pass, yellow for warnings
- **Error Counts** - See number of issues at a glance
- **Check All Button** - Run all validations with one click
- **Error Summary Panel** - Collapsible overview of all issues
- **Show/Hide Passed Checks** - Toggle to hide successful validations
- **Quick Fix Buttons** - Select and fix problematic geometry

### 🔧 Tools
- Apply all modifiers
- Apply all transforms
- Multiple origin presets (bottom center, min corner, world origin, etc.)
- UV checker material system

## Installation

1. Download the `MeshChecker` folder
2. Open Blender
3. Go to `Edit > Preferences > Add-ons`
4. Click `Install...`
5. Navigate to the `MeshChecker` folder and select it (or zip it first)
6. Enable the addon by checking the box next to "Mesh: MeshChecker"

## Usage

### Location
Find the panel in the 3D Viewport:
- Press `N` to open the sidebar
- Navigate to the `Meshchecker` tab

### Quick Start
1. Select your mesh object
2. Click **"RUN ALL CHECKS"** to validate everything at once
3. Review the color-coded results:
   - ✓ Green = Passed
   - ✗ Red = Errors found
   - ⚠ Yellow = Warnings
4. Click individual check buttons for more details
5. Use "Select" and "Fix" buttons to resolve issues

### Individual Checks
Each validation can be run independently:
- Click any check button to run just that validation
- Errors will be automatically selected in the viewport
- Error counts appear next to failed checks
- Expand messages for more details

### UV Checker
Available in the UV/Image Editor:
1. Switch to UV Editor workspace
2. Open the sidebar (`N` key)
3. Navigate to `UV Checker` tab
4. Select a checker image
5. Adjust UV scale
6. Apply checker material
7. Run UDIM 1001 check

## Keyboard Shortcuts
- `N` - Toggle sidebar (where the addon panel is located)

## Requirements
- Blender 5.0 or higher

## Version History

### v2.0.0
- Complete UI redesign with error tracking
- Added "Check All" functionality
- Color-coded status indicators
- Error summary panel
- Individual error counts
- Improved visual feedback
- Better error messages

### v1.0.0
- Initial release
- Basic validation checks
- Origin tools
- UV checker system

## Tips
- Run "Check All" before every export
- Enable "Show Passed Checks" to see all validations
- Use the Error Summary panel for quick overview
- Save your work before applying modifiers/transforms
- The addon works best in Object Mode

## Troubleshooting

**Panel not visible?**
- Make sure you're in the 3D Viewport
- Press `N` to open the sidebar
- Look for the "MeshChecker" tab

**Checks not running?**
- Ensure a mesh object is selected
- Switch to Object Mode if in Edit Mode
- Check the console for error messages

**No errors showing despite issues?**
- Make sure "Show Passed Checks" is toggled if needed
- Try running individual checks
- Verify your mesh is selected

## Credits
- Author: Suman Ghosh
- Enhanced Version: v2.0.0

## License
Free to use and modify

---

For bug reports or feature requests, please contact the author.
