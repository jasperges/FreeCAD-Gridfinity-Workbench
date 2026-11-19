"""A module for making cable organizers.

A cable organizer is a bin with an open (lattice) bottom and cross dividers. The end walls and the
dividers have a notch in the middle, which forms a cradle to put cables in.

The design is based on "Gridfinity Cable Organizing Boxes" by Dead_Pixel
(https://www.thingiverse.com/thing:6748502), licensed under Creative Commons
Attribution-NonCommercial-ShareAlike (CC BY-NC-SA).

Shapes are made in the same coordinate system as the other bins: the top of the bin is at z = 0,
the bottom at z = -TotalHeight.
"""

from __future__ import annotations

import math

import FreeCAD as fc  # noqa: N813
import Part

from . import const, utils
from . import feature_construction as feat
from . import magnet_hole as magnet_hole_module

GridfinityLayout = list[list[bool]]


def add_properties(obj: fc.DocumentObject) -> None:
    """Add cable organizer properties to an object."""
    ## Gridfinity Parameters
    obj.addProperty(
        "App::PropertyInteger",
        "SlotsPerGridUnit",
        "Gridfinity",
        "Number of cable slots per grid unit in the x direction <br> <br> default = 2",
    ).SlotsPerGridUnit = const.CABLE_SLOTS_PER_GRID_UNIT

    obj.addProperty(
        "App::PropertyBool",
        "DividerLattice",
        "Gridfinity",
        "Toggle the diamond shaped openings in the dividers on or off",
    ).DividerLattice = const.CABLE_DIVIDER_LATTICE

    obj.addProperty(
        "App::PropertyBool",
        "BottomLattice",
        "Gridfinity",
        "Toggle the lattice in the open bottom of the bin on or off",
    ).BottomLattice = const.CABLE_BOTTOM_LATTICE

    ## Gridfinity Non Standard Parameters
    obj.addProperty(
        "App::PropertyLength",
        "CableDividerThickness",
        "GridfinityNonStandard",
        f"Thickness of the dividers <br> <br> default = {const.CABLE_DIVIDER_THICKNESS} mm",
    ).CableDividerThickness = const.CABLE_DIVIDER_THICKNESS

    obj.addProperty(
        "App::PropertyLength",
        "NotchDepth",
        "GridfinityNonStandard",
        f"Depth of the cable notch <br> <br> default = {const.CABLE_NOTCH_DEPTH} mm",
    ).NotchDepth = const.CABLE_NOTCH_DEPTH

    obj.addProperty(
        "App::PropertyLength",
        "NotchBottomWidth",
        "GridfinityNonStandard",
        (
            "Width of the bottom of the cable notch, measured without the rounding"
            f" <br> <br> default = {const.CABLE_NOTCH_BOTTOM_WIDTH} mm"
        ),
    ).NotchBottomWidth = const.CABLE_NOTCH_BOTTOM_WIDTH

    obj.addProperty(
        "App::PropertyAngle",
        "NotchAngle",
        "GridfinityNonStandard",
        (
            "Angle of the sides of the cable notch, measured from horizontal"
            f" <br> <br> default = {const.CABLE_NOTCH_ANGLE}°"
        ),
    ).NotchAngle = const.CABLE_NOTCH_ANGLE

    obj.addProperty(
        "App::PropertyLength",
        "NotchRadius",
        "GridfinityNonStandard",
        f"Rounding of the cable notch <br> <br> default = {const.CABLE_NOTCH_RADIUS} mm",
    ).NotchRadius = const.CABLE_NOTCH_RADIUS

    obj.addProperty(
        "App::PropertyLength",
        "DividerLatticeBarWidth",
        "GridfinityNonStandard",
        (
            "Width of the bars of the divider lattice"
            f" <br> <br> default = {const.CABLE_DIVIDER_LATTICE_BAR_WIDTH} mm"
        ),
    ).DividerLatticeBarWidth = const.CABLE_DIVIDER_LATTICE_BAR_WIDTH

    obj.addProperty(
        "App::PropertyLength",
        "DividerLatticeBorder",
        "GridfinityNonStandard",
        (
            "Width of the solid border around the openings in the dividers, measured from the"
            " outside and the top of the bin and from the notch"
            f" <br> <br> default = {const.CABLE_DIVIDER_LATTICE_BORDER} mm"
        ),
    ).DividerLatticeBorder = const.CABLE_DIVIDER_LATTICE_BORDER

    obj.addProperty(
        "App::PropertyLength",
        "BottomLatticeBarWidth",
        "GridfinityNonStandard",
        (
            "Width of the bars of the bottom lattice"
            f" <br> <br> default = {const.CABLE_BOTTOM_LATTICE_BAR_WIDTH} mm"
        ),
    ).BottomLatticeBarWidth = const.CABLE_BOTTOM_LATTICE_BAR_WIDTH

    obj.addProperty(
        "App::PropertyLength",
        "BottomLatticeThickness",
        "GridfinityNonStandard",
        (
            "Thickness of the bottom lattice"
            f" <br> <br> default = {const.CABLE_BOTTOM_LATTICE_THICKNESS} mm"
        ),
    ).BottomLatticeThickness = const.CABLE_BOTTOM_LATTICE_THICKNESS

    obj.addProperty(
        "App::PropertyLength",
        "TopCoverWidth",
        "GridfinityNonStandard",
        (
            "Width of the closed top at both long sides of the bin, measured from the outside."
            f" 0 mm = no closed top <br> <br> default = {const.CABLE_TOP_COVER_WIDTH} mm"
        ),
    ).TopCoverWidth = const.CABLE_TOP_COVER_WIDTH

    obj.addProperty(
        "App::PropertyLength",
        "TopCoverThickness",
        "GridfinityNonStandard",
        (
            "Thickness of the closed top at both long sides of the bin"
            f" <br> <br> default = {const.CABLE_TOP_COVER_THICKNESS} mm"
        ),
    ).TopCoverThickness = const.CABLE_TOP_COVER_THICKNESS

    ## Expert Only Parameters
    obj.addProperty(
        "App::PropertyLength",
        "DividerLatticeSpacing",
        "zzExpertOnly",
        (
            "Horizontal distance between the parallel bars of the divider lattice"
            f" <br> <br> default = {const.CABLE_DIVIDER_LATTICE_SPACING} mm"
        ),
    ).DividerLatticeSpacing = const.CABLE_DIVIDER_LATTICE_SPACING

    obj.addProperty(
        "App::PropertyLength",
        "BottomLatticeSpacing",
        "zzExpertOnly",
        (
            "Distance in x direction between the parallel bars of the bottom lattice"
            f" <br> <br> default = {const.CABLE_BOTTOM_LATTICE_SPACING} mm"
        ),
    ).BottomLatticeSpacing = const.CABLE_BOTTOM_LATTICE_SPACING


def _to_yz_plane(shape: Part.Shape) -> Part.Shape:
    """Rotate a shape made in the XY plane to the YZ plane, so (x, y, z) becomes (z, x, y)."""
    return shape.rotated(fc.Vector(0, 0, 0), fc.Vector(1, 1, 1), 120)


def _diagonal_bars(spacing: float, width: float, extent: float) -> Part.Shape:
    """Make a face of bars at +45 and -45 degrees in the XY plane, crossing at the origin.

    Args:
        spacing (float): Distance in x direction between parallel bars.
        width (float): Width of the bars.
        extent (float): Half the size of the square area that should be covered by bars.

    """
    count = math.ceil(2 * extent / spacing)
    length = 4 * extent
    bar = Part.makePlane(length, width, fc.Vector(-length / 2, -width / 2))
    bars = [
        bar.rotated(fc.Vector(0, 0, 0), fc.Vector(0, 0, 1), angle).translate(
            fc.Vector(i * spacing, 0),
        )
        for angle in (45, -45)
        for i in range(-count, count + 1)
    ]
    return utils.multi_fuse(bars).removeSplitter()


def _notch_dimensions(obj: fc.DocumentObject) -> tuple[float, float, float, float, float]:
    """Get the center, depth, half bottom width, half top width and flange size of the notch."""
    center = obj.yTotalWidth.Value / 2 + obj.Clearance.Value - obj.yLocationOffset.Value
    depth = obj.NotchDepth.Value
    if depth <= 0:
        raise ValueError("Notch depth must be larger than 0 mm")
    bottom = obj.NotchBottomWidth.Value / 2
    top = bottom + depth / math.tan(math.radians(obj.NotchAngle.Value))
    big = obj.yTotalWidth.Value + obj.TotalHeight.Value + 2 * obj.NotchRadius.Value
    return center, depth, bottom, top, big


def _notch_outline(obj: fc.DocumentObject) -> Part.Face:
    """Make the notch profile without rounding, with a wide flange above the top of the bin.

    The profile is in the XY plane, x is the y coordinate of the bin, y the z coordinate.
    """
    center, depth, bottom, top, big = _notch_dimensions(obj)
    return utils.curve_to_face(
        utils.loop(
            [
                fc.Vector(center - top - big, 0),
                fc.Vector(center - top, 0),
                fc.Vector(center - bottom, -depth),
                fc.Vector(center + bottom, -depth),
                fc.Vector(center + top, 0),
                fc.Vector(center + top + big, 0),
                fc.Vector(center + top + big, big),
                fc.Vector(center - top - big, big),
            ],
        ),
    )


def _notch_face(obj: fc.DocumentObject) -> Part.Face:
    """Make the notch profile in the XY plane, x is the y coordinate of the bin, y the z coordinate.

    The bottom of the notch and the edges at the top of the bin are rounded with `NotchRadius`.
    Above the top of the bin the notch continues, so it also cuts through a stacking lip.
    """
    center, _, _, top, big = _notch_dimensions(obj)
    radius = obj.NotchRadius.Value

    # The flange above the top of the bin makes sure the top edges get rounded as well
    notch = _notch_outline(obj)
    if radius > 0:
        notch = notch.makeOffset2D(-radius).makeOffset2D(radius)
        notch = notch.makeOffset2D(radius).makeOffset2D(-radius)

    # Remove the flange above the top of the bin, the sides of the notch continue upwards
    run = big / math.tan(math.radians(obj.NotchAngle.Value))
    far = top + big + run
    for side in (-1, 1):
        flange = utils.curve_to_face(
            utils.loop(
                [
                    fc.Vector(center + side * top, 0),
                    fc.Vector(center + side * far, 0),
                    fc.Vector(center + side * far, big),
                    fc.Vector(center + side * (top + run), big),
                ],
            ),
        )
        notch = notch.cut(flange)
    notch = notch.removeSplitter()
    if len(notch.Faces) != 1:
        raise ValueError("Cable notch is invalid, try a smaller notch radius")
    return notch.Faces[0]


def make_notch(obj: fc.DocumentObject) -> Part.Shape:
    """Make the cable notch, cutting through the end walls and dividers of the bin."""
    x_start = obj.Clearance.Value - obj.xLocationOffset.Value - 1
    length = obj.xTotalWidth.Value + 2
    notch = _notch_face(obj).extrude(fc.Vector(0, 0, length))
    return _to_yz_plane(notch).translate(fc.Vector(x_start, 0, 0))


def make_dividers(obj: fc.DocumentObject) -> Part.Shape | None:
    """Make the dividers between the cable slots, optionally with diamond shaped openings.

    Returns `None` when there are no dividers.
    """
    slots = obj.SlotsPerGridUnit
    if slots < 1:
        raise ValueError("Slots per grid unit must be at least 1")
    thickness = obj.CableDividerThickness.Value
    wall = obj.WallThickness.Value
    x_grid_units = int(obj.xGridUnits + 1e-6)
    pitch = obj.xGridSize.Value / slots
    y_start = obj.Clearance.Value - obj.yLocationOffset.Value
    y_width = obj.yTotalWidth.Value
    height = obj.TotalHeight.Value

    dividers: list[Part.Shape] = [
        Part.makeBox(
            thickness,
            y_width - wall,
            height,
            fc.Vector(
                i * pitch - obj.xLocationOffset.Value - thickness / 2,
                y_start + wall / 2,
                -height,
            ),
        )
        for i in range(1, x_grid_units * slots)
    ]
    if not dividers:
        return None
    shape = utils.multi_fuse(dividers)

    if obj.DividerLattice:
        shape = shape.cut(_divider_openings(obj))

    return shape


def _divider_openings(obj: fc.DocumentObject) -> Part.Shape:
    """Make the diamond shaped openings in the dividers.

    The rim along the notch is not rounded: it is flat below the bottom of the notch and follows
    the sides of the notch, so it can be printed without supports. The lattice is aligned with the
    notch, so the flat part ends at the bars.
    """
    bar_width = obj.DividerLatticeBarWidth.Value
    wall = obj.WallThickness.Value
    border = max(obj.DividerLatticeBorder.Value, wall)
    y_start = obj.Clearance.Value - obj.yLocationOffset.Value + border
    y_end = y_start + obj.yTotalWidth.Value - 2 * border
    # The lower part of the base stays solid
    z_start = (
        -obj.TotalHeight.Value
        + obj.BaseProfileBottomChamfer.Value
        + obj.BaseProfileVerticalSection.Value
    )
    z_end = -border

    frame = Part.makePlane(y_end - y_start, z_end - z_start, fc.Vector(y_start, z_start))
    # Join type 2 (intersection) keeps the corners of the offset sharp
    frame = frame.cut(_notch_outline(obj).makeOffset2D(border, join=2))

    # Align the lattice with the notch: the bars of the opening below the notch go through the
    # corners of the flat part of the rim, so the flat part connects directly to the bars
    center, depth, bottom, _, _ = _notch_dimensions(obj)
    half_flat = bottom + border * math.tan(math.radians(obj.NotchAngle.Value) / 2)
    z_crossing = -depth - border + half_flat + bar_width / math.sqrt(2)

    extent = max(y_end - y_start, z_crossing - z_start)
    bars = _diagonal_bars(obj.DividerLatticeSpacing.Value, bar_width, extent)
    bars.translate(fc.Vector(center, z_crossing))
    openings = frame.cut(bars)

    x_start = obj.Clearance.Value - obj.xLocationOffset.Value + wall
    length = obj.xTotalWidth.Value - 2 * wall
    openings = openings.extrude(fc.Vector(0, 0, length))
    return _to_yz_plane(openings).translate(fc.Vector(x_start, 0, 0))


def make_open_bottom_cavity(obj: fc.DocumentObject, layout: GridfinityLayout) -> Part.Shape:
    """Make the inside of the bin, open at the bottom.

    The base of every grid cell becomes a shell with a thickness of `WallThickness`. Above the base
    a layer of `WallThickness` connects the grid cells.
    """
    wall = obj.WallThickness.Value
    clearance = obj.Clearance.Value
    bottom_chamfer = obj.BaseProfileBottomChamfer.Value
    vertical_section = obj.BaseProfileVerticalSection.Value
    top_chamfer = obj.BaseProfileTopChamfer.Value
    bottom_radius = obj.BinBottomRadius.Value
    vertical_radius = obj.BinVerticalRadius.Value
    z_bottom = -obj.TotalHeight.Value

    def widths(grid_size: float) -> tuple[float, float, float]:
        top = grid_size - 2 * clearance - 2 * wall
        vertical = top - 2 * top_chamfer
        return vertical - 2 * bottom_chamfer, vertical, top

    x_bottom, x_vertical, x_top = widths(obj.xGridSize.Value)
    y_bottom, y_vertical, y_top = widths(obj.yGridSize.Value)
    z_vertical = z_bottom + bottom_chamfer
    z_top_chamfer = z_vertical + vertical_section
    z_top = z_top_chamfer + top_chamfer

    cell = utils.multi_fuse(
        [
            utils.rounded_rectangle_extrude(x_bottom, y_bottom, z_bottom - 1, 1, bottom_radius),
            utils.rounded_rectangle_chamfer(
                x_bottom,
                y_bottom,
                z_bottom,
                bottom_chamfer,
                bottom_radius,
            ),
            utils.rounded_rectangle_extrude(
                x_vertical,
                y_vertical,
                z_vertical,
                vertical_section,
                vertical_radius,
            ),
            utils.rounded_rectangle_chamfer(
                x_vertical,
                y_vertical,
                z_top_chamfer,
                top_chamfer,
                vertical_radius,
            ),
            utils.rounded_rectangle_extrude(
                x_top,
                y_top,
                z_top,
                wall + 1,
                vertical_radius + top_chamfer,
            ),
        ],
    )
    cells = utils.copy_in_layout(cell, layout, obj.xGridSize, obj.yGridSize)
    cells.translate(
        fc.Vector(
            obj.xGridSize.Value / 2 - obj.xLocationOffset.Value,
            obj.yGridSize.Value / 2 - obj.yLocationOffset.Value,
        ),
    )

    z_inside = z_top + wall
    inside = utils.rounded_rectangle_extrude(
        obj.xTotalWidth.Value - 2 * wall,
        obj.yTotalWidth.Value - 2 * wall,
        z_inside,
        -z_inside + 1,
        max(obj.BinOuterRadius.Value - wall, 0.5),
    )
    inside.translate(
        fc.Vector(
            obj.xTotalWidth.Value / 2 + clearance - obj.xLocationOffset.Value,
            obj.yTotalWidth.Value / 2 + clearance - obj.yLocationOffset.Value,
        ),
    )

    return cells.fuse(inside)


def make_bottom_lattice(obj: fc.DocumentObject, layout: GridfinityLayout) -> Part.Shape:
    """Make the lattice in the bottom of every grid cell.

    The lattice is not trimmed to the shape of the bin.
    """
    x_grid_size = obj.xGridSize.Value
    y_grid_size = obj.yGridSize.Value
    bars = _diagonal_bars(
        obj.BottomLatticeSpacing.Value,
        obj.BottomLatticeBarWidth.Value,
        max(x_grid_size, y_grid_size) / 2,
    )
    cell = Part.makePlane(x_grid_size, y_grid_size, fc.Vector(-x_grid_size / 2, -y_grid_size / 2))
    lattice = bars.common(cell).extrude(fc.Vector(0, 0, obj.BottomLatticeThickness.Value))
    lattice.translate(fc.Vector(0, 0, -obj.TotalHeight.Value))

    lattice = utils.copy_in_layout(lattice, layout, obj.xGridSize, obj.yGridSize)
    return lattice.translate(
        fc.Vector(obj.xGridSize / 2 - obj.xLocationOffset, obj.yGridSize / 2 - obj.yLocationOffset),
    )


def make_top_covers(obj: fc.DocumentObject) -> Part.Shape | None:
    """Make the closed top at both long sides of the bin.

    The covers are not trimmed to the shape of the bin. Returns `None` when there are no covers.
    """
    width = obj.TopCoverWidth.Value
    thickness = obj.TopCoverThickness.Value
    if width <= 0 or thickness <= 0:
        return None

    x_start = obj.Clearance.Value - obj.xLocationOffset.Value
    y_start = obj.Clearance.Value - obj.yLocationOffset.Value
    length = obj.xTotalWidth.Value
    return utils.multi_fuse(
        [
            Part.makeBox(length, width, thickness, fc.Vector(x_start, y, -thickness))
            for y in (y_start, y_start + obj.yTotalWidth.Value - width)
        ],
    )


def _hole_pad(
    x_hole: float,
    y_hole: float,
    radius: float,
    height: float,
    corner: fc.Vector,
) -> Part.Shape:
    """Make a pad from a corner of a grid cell to around a hole.

    The pad is rounded around the hole on the side facing the center of the grid cell, and the top
    edges are rounded.
    """
    sx = 1 if corner.x > x_hole else -1
    sy = 1 if corner.y > y_hole else -1
    hole = fc.Vector(x_hole, y_hole, corner.z)

    def box(x1: float, x2: float, y1: float, y2: float) -> Part.Shape:
        return Part.makeBox(
            abs(x2 - x1),
            abs(y2 - y1),
            height,
            fc.Vector(min(x1, x2), min(y1, y2), corner.z),
        )

    pad = utils.multi_fuse(
        [
            box(x_hole - sx * radius, corner.x, y_hole, corner.y),
            box(x_hole, corner.x, y_hole - sy * radius, corner.y),
            Part.makeCylinder(radius, height, hole),
        ],
    ).removeSplitter()

    top = corner.z + height
    top_edges = [
        edge
        for edge in pad.Edges
        if math.isclose(edge.BoundBox.ZMin, top, abs_tol=1e-6)
        and math.isclose(edge.BoundBox.ZMax, top, abs_tol=1e-6)
    ]
    fillet = min(const.CABLE_HOLE_PAD_TOP_RADIUS, height / 2)
    return pad.makeFillet(fillet, top_edges)


def make_hole_pads(obj: fc.DocumentObject, layout: GridfinityLayout) -> Part.Shape | None:
    """Make solid blocks in the corners of the grid cells, to put the magnet and screw holes in.

    The pads are placed at the same positions as the holes, see
    `feature_construction.make_bin_bottom_holes`. They are not trimmed to the shape of the bin.
    Returns `None` when there are no holes.
    """
    radii = []
    heights = []
    if obj.MagnetHoles:
        radii.append(obj.MagnetHoleDiameter.Value / 2)
        heights.append(magnet_hole_module.depth_from_bottom(obj).Value)
    if obj.ScrewHoles:
        radii.append(obj.ScrewHoleDiameter.Value / 2)
        heights.append(obj.ScrewHoleDepth.Value)
    if not radii:
        return None

    wall = obj.WallThickness.Value
    height = max(heights) + wall
    x_half = obj.xGridSize.Value / 2
    y_half = obj.yGridSize.Value / 2
    x_hole = x_half - obj.MagnetHoleDistanceFromEdge.Value
    y_hole = y_half - obj.MagnetHoleDistanceFromEdge.Value

    pads = utils.multi_fuse(
        [
            _hole_pad(
                sx * x_hole,
                sy * y_hole,
                max(radii) + wall,
                height,
                fc.Vector(sx * x_half, sy * y_half, -obj.TotalHeight.Value),
            )
            for sx in (-1, 1)
            for sy in (-1, 1)
        ],
    )
    return feat.place_at_hole_positions(obj, pads, layout)
