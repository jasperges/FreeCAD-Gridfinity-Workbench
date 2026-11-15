"""A module for making magnet holes."""

from __future__ import annotations

import math

import FreeCAD as fc  # noqa: N813
import Part

from . import const, utils

unitmm = fc.Units.Quantity("1 mm")

# Tooltips of the magnet hole size properties, per type of magnet hole, see `on_changed`
_HOLE_SIZE_TOOLTIPS = {
    "Standard": {
        "MagnetHoleDepth": "Depth of Magnet Holes <br> <br> default = 2.4 mm",
        "MagnetHoleDiameter": (
            "Diameter of Magnet Holes. Press fit by default, increase to 6.5 mm if using glue."
            "For crush ribs, 5.7mm is recommended. <br> <br> default = 6.2 mm"
        ),
    },
    "Refined": {
        "MagnetHoleDepth": (
            "Height of the refined magnet slot. The slot starts"
            f" {const.LAYER_HEIGHT * const.REFINED_HOLE_BOTTOM_LAYERS:.1f} mm above the bottom."
            f" <br> <br> default = {const.REFINED_HOLE_DEPTH:.1f} mm"
        ),
        "MagnetHoleDiameter": (
            "Diameter of the refined magnet slot. Slightly smaller than the magnet, so it is held"
            f" by friction. <br> <br> default = {const.REFINED_HOLE_DIAMETER} mm"
        ),
    },
}


def add_properties(
    obj: fc.DocumentObject,
    *,
    remove_channel: bool,
    chamfer: bool,
    magnet_holes_default: bool,
    refined: bool = False,
) -> None:
    """Add magnet holes properties to an object.

    Args:
        obj (FreeCAD.DocumentObject): Document object.
        remove_channel (bool): Does the object support magnet remove channel.
        chamfer (bool): Does the object support hole chamfer.
        magnet_holes_default (bool): Should magnet holes be enabled by default.
        refined (bool): Does the object support Gridfinity Refined magnet holes.

    """
    ## Gridfinity Parameters
    obj.addProperty(
        "App::PropertyBool",
        "MagnetHoles",
        "Gridfinity",
        "Toggle the magnet holes on or off",
    ).MagnetHoles = magnet_holes_default

    ## Gridfinity Non Standard Parameters
    obj.addProperty(
        "App::PropertyLength",
        "MagnetHoleDepth",
        "GridfinityNonStandard",
        _HOLE_SIZE_TOOLTIPS["Standard"]["MagnetHoleDepth"],
    ).MagnetHoleDepth = const.MAGNET_HOLE_DEPTH

    obj.addProperty(
        "App::PropertyLength",
        "MagnetHoleDiameter",
        "GridfinityNonStandard",
        _HOLE_SIZE_TOOLTIPS["Standard"]["MagnetHoleDiameter"],
    ).MagnetHoleDiameter = const.MAGNET_HOLE_DIAMETER

    obj.addProperty(
        "App::PropertyEnumeration",
        "MagnetHolesShape",
        "GridfinityNonStandard",
        (
            "Shape of magnet holes, change to suit your printers capabilities which might require"
            "testing."
            "<br> Round is press fit by default, increase to 6.5 mm if using glue."
            "<br> <br> Crush ribs are an alternative press fit style."
            "<br> <br> Hex is a legacy press fit style."
            + (
                "<br> <br> Refined: the magnet slides in from the side and is held by friction."
                if refined
                else ""
            )
        ),
    ).MagnetHolesShape = const.BIN_HOLE_SHAPES if refined else const.HOLE_SHAPES

    if refined:
        add_hole_size_storage_properties(obj)

    if chamfer:
        obj.addProperty(
            "App::PropertyLength",
            "MagnetHoleChamfer",
            "GridfinityNonStandard",
            "The depth at which magnet hole chamfer starts.",
        ).MagnetHoleChamfer = 0.25

    if remove_channel:
        obj.addProperty(
            "App::PropertyBool",
            "MagnetRemoveChannel",
            "GridfinityNonStandard",
            "Toggle the magnet remove channel on or off",
        ).MagnetRemoveChannel = False

    obj.addProperty(
        "App::PropertyInteger",
        "CrushRibsCount",
        "GridfinityNonStandard",
        "Number of crush ribs <br><br> default = 12",
    ).CrushRibsCount = const.CRUSH_RIB_N

    obj.addProperty(
        "App::PropertyFloatConstraint",
        "CrushRibsWaviness",
        "GridfinityNonStandard",
        "Waviness of crush ribs, from range [0, 1]",
    ).CrushRibsWaviness = (const.CRUSH_RIB_WAVINESS, 0, 1, 0.05)

    ## Expert Only Parameters
    obj.addProperty(
        "App::PropertyLength",
        "MagnetHoleDistanceFromEdge",
        "zzExpertOnly",
        "Distance of the magnet holes from bin edge <br> <br> default = 8.0 mm",
        read_only=True,
    ).MagnetHoleDistanceFromEdge = const.MAGNET_HOLE_DISTANCE_FROM_EDGE


_HOLE_SIZE_PROPERTIES = ("MagnetHoleDiameter", "MagnetHoleDepth")


def add_hole_size_storage_properties(obj: fc.DocumentObject) -> None:
    """Add hidden properties that store the magnet hole size per hole type.

    Refined holes and the other hole types each keep their own diameter and depth. The visible
    `MagnetHoleDiameter` and `MagnetHoleDepth` show the values of the selected hole type, see
    `on_changed`. The values for the other hole types are taken from the object, the refined values
    start at their defaults.
    """
    stored_values = {
        "MagnetHoleDiameterStandard": obj.MagnetHoleDiameter,
        "MagnetHoleDepthStandard": obj.MagnetHoleDepth,
        "MagnetHoleDiameterRefined": const.REFINED_HOLE_DIAMETER,
        "MagnetHoleDepthRefined": const.REFINED_HOLE_DEPTH,
    }
    for name, value in stored_values.items():
        if not hasattr(obj, name):
            obj.addProperty(
                "App::PropertyLength",
                name,
                "Hidden",
                "Stored magnet hole size, used when switching the magnet hole shape",
                hidden=True,
            )
            setattr(obj, name, value)
    _update_hole_size_tooltips(obj)


def _hole_size_type(obj: fc.DocumentObject) -> str:
    return "Refined" if obj.MagnetHolesShape == "Refined" else "Standard"


def _update_hole_size_tooltips(obj: fc.DocumentObject) -> None:
    for name, tooltip in _HOLE_SIZE_TOOLTIPS[_hole_size_type(obj)].items():
        obj.setDocumentationOfProperty(name, tooltip)


def on_changed(obj: fc.DocumentObject, prop: str) -> None:
    """Keep separate magnet hole sizes for refined holes and the other hole types.

    Changing the diameter or depth stores the value for the selected hole type. Changing the hole
    shape loads the stored values and tooltips of the new hole type.
    """
    if prop not in ("MagnetHolesShape", *_HOLE_SIZE_PROPERTIES):
        return
    if "Restore" in obj.State or not hasattr(obj, "MagnetHoleDepthRefined"):
        return

    suffix = _hole_size_type(obj)
    if prop == "MagnetHolesShape":
        for name in _HOLE_SIZE_PROPERTIES:
            stored_value = getattr(obj, name + suffix)
            if getattr(obj, name) != stored_value:
                setattr(obj, name, stored_value)
        _update_hole_size_tooltips(obj)
        utils.refresh_property_editor()
    else:
        setattr(obj, prop + suffix, getattr(obj, prop))


def _crush_ribs(radius: fc.Units.Quantity, *, n: int, beta: float) -> tuple[Part.Face, float]:
    """Make crush ribs inner face.

    Args:
        radius (fc.Units.Quantity): Inner radius.
        n (int): Number of ribs.
        beta (float): Waviness of the ribs. It is the angle at wich inner at outer arcs meet.
        A value of 0 would result in a perfect circle.

    """
    alpha = math.pi / n / 2

    def get_midpoint(beta: float) -> float:
        return (math.sin(beta) - math.sin(alpha)) / math.sin(beta - alpha)

    r1 = radius.Value
    r2 = radius.Value / get_midpoint(beta)
    r3 = r2 * get_midpoint(-beta)

    p1 = fc.Vector(r2, 0)
    p2 = fc.Vector(r2 * math.cos(2 * alpha), r2 * math.sin(2 * alpha))
    q = r1 * fc.Vector(math.cos(alpha), math.sin(alpha))
    r = r3 * fc.Vector(math.cos(alpha), math.sin(alpha))

    lines = []
    for _ in range(n):
        lines.append(Part.Arc(p1, q, p2))
        lines.append(Part.Arc(p1, r, p2))
    for i, arc in enumerate(lines):
        placement = fc.Placement(
            fc.Vector(0, 0, 0),
            fc.Vector(0, 0, 1),
            math.degrees((i + 0.5) / len(lines) * 2 * math.pi),
        )
        arc.rotate(placement)
    return utils.curve_to_face(lines), r3 - r1


def _hex_shape(radius: fc.Units.Quantity) -> Part.Shape:
    # Ratio of 2/sqrt(3) converts from inscribed circle radius to circumscribed
    # circle radius
    radius = 2 * radius / math.sqrt(3)

    p = fc.ActiveDocument.addObject("Part::RegularPolygon")
    p.Polygon = 6
    p.Circumradius = radius
    p.recompute()

    p_wire: Part.Wire = p.Shape
    shape = Part.Face(p_wire)
    fc.ActiveDocument.removeObject(p.Name)
    return shape


def from_obj(obj: fc.DocumentObject) -> Part.Shape:
    """Create a single magnet hole from object properties."""
    if not obj.MagnetHoles:
        raise ValueError("Object doesn't have magnet holes enables")

    hole_shape = obj.MagnetHolesShape
    radius = obj.MagnetHoleDiameter / 2
    depth = obj.MagnetHoleDepth
    chamfer_depth = obj.MagnetHoleChamfer if hasattr(obj, "MagnetHoleChamfer") else None

    if hole_shape == "Hex":
        shape = _hex_shape(radius)
        chamfer_width = (2 / math.sqrt(3) - 1) * radius
    elif hole_shape == "Crush ribs":
        shape, ch = _crush_ribs(
            radius,
            n=obj.CrushRibsCount,
            beta=obj.CrushRibsWaviness * math.pi / 2,
        )
        chamfer_width = ch * unitmm
    elif hole_shape == "Refined":
        raise ValueError("Refined magnet holes are made with refined_holes()")
    elif hole_shape == "Round":
        shape = Part.Face(Part.Wire(Part.makeCircle(radius)))
        chamfer_width = chamfer_depth
    else:
        raise ValueError(f"Unrecognised magnet hole shape {hole_shape:!r}")

    shape = shape.extrude(fc.Vector(0, 0, depth))

    if obj.Baseplate:
        assert chamfer_depth is not None
        chamfer_shape = Part.makeCone(
            radius,
            radius + chamfer_width,
            chamfer_depth,
            fc.Vector(0, 0, depth - chamfer_depth),
        )
        shape = shape.fuse(chamfer_shape)

    return shape


def depth_from_bottom(obj: fc.DocumentObject) -> fc.Units.Quantity:
    """Get the distance from the bottom of the bin to the top of the magnet holes."""
    if obj.MagnetHolesShape == "Refined":
        return obj.MagnetHoleDepth + const.LAYER_HEIGHT * const.REFINED_HOLE_BOTTOM_LAYERS * unitmm
    return obj.MagnetHoleDepth


def refined_hole(diameter: float, height: float) -> Part.Shape:
    """Create a single Gridfinity Refined magnet hole.

    Matches `refined_hole()` from gridfinity-rebuilt-openscad. The magnet is pushed in from the +X
    direction and held by friction. A small poke hole in the bottom allows removing the magnet.
    The bottom of the bin is at z = 0.

    Args:
        diameter (float): Diameter of the magnet slot.
        height (float): Height of the magnet slot. The slot starts a few layers above the bottom.

    """
    if height <= 0:
        raise ValueError("Refined magnet hole depth must be larger than 0 mm")
    refined_offset = const.LAYER_HEIGHT * const.REFINED_HOLE_BOTTOM_LAYERS
    radius = diameter / 2

    # Poke through - for removing a magnet using a toothpick
    ptl = refined_offset + const.LAYER_HEIGHT  # Additional layer just in case
    poke_through_height = height + ptl
    poke_hole_diameter = 2.5
    magic_constant = 5.60
    poke_hole_center = fc.Vector(-12.53 + magic_constant, 0, refined_offset - ptl)

    shapes: list[Part.Shape] = [
        # Magnet hole
        Part.makeBox(11, 2 * radius, height, fc.Vector(0, -radius, refined_offset)),
        Part.makeCylinder(radius, height, fc.Vector(0, 0, refined_offset)),
        # Poke hole
        Part.makeBox(
            10 - magic_constant,
            poke_hole_diameter,
            poke_through_height,
            poke_hole_center + fc.Vector(0, -poke_hole_diameter / 2, 0),
        ),
        Part.makeCylinder(poke_hole_diameter / 2, poke_through_height, poke_hole_center),
    ]
    return utils.multi_fuse(shapes).removeSplitter()


def refined_holes(obj: fc.DocumentObject) -> Part.Shape:
    """Create Gridfinity Refined magnet holes for the four corners of a single grid cell.

    The magnet slots point outwards, rotated 90 degrees per corner, as in
    gridfinity-rebuilt-openscad. The shape is clipped to the grid cell, so it doesn't cut into
    neighbouring cells.
    """
    x_hole_pos = obj.xGridSize / 2 - obj.MagnetHoleDistanceFromEdge
    y_hole_pos = obj.yGridSize / 2 - obj.MagnetHoleDistanceFromEdge

    hole = refined_hole(obj.MagnetHoleDiameter.Value, obj.MagnetHoleDepth.Value)
    positions = [
        (0, x_hole_pos, y_hole_pos),
        (90, -x_hole_pos, y_hole_pos),
        (180, -x_hole_pos, -y_hole_pos),
        (270, x_hole_pos, -y_hole_pos),
    ]
    shape = utils.multi_fuse(
        [
            hole.rotated(fc.Vector(0, 0, 0), fc.Vector(0, 0, 1), angle).translate(fc.Vector(x, y))
            for angle, x, y in positions
        ],
    )

    bb = shape.BoundBox
    cell = Part.makeBox(
        obj.xGridSize,
        obj.yGridSize,
        bb.ZLength + 2,
        fc.Vector(-obj.xGridSize / 2, -obj.yGridSize / 2, bb.ZMin - 1),
    )
    return shape.common(cell)


def remove_channel(obj: fc.DocumentObject) -> Part.Shape:
    """Create a magnet remove channel shape for four magnets from object properties."""
    x_hole_pos = obj.xGridSize / 2 - obj.MagnetHoleDistanceFromEdge
    y_hole_pos = obj.yGridSize / 2 - obj.MagnetHoleDistanceFromEdge
    alpha = math.pi / 8

    r = obj.MagnetHoleDiameter / 2
    x1 = r * math.cos(alpha)
    y1 = r * math.sin(alpha)
    p1 = fc.Vector(x1, y1)
    p2 = fc.Vector(x1 + 2 * y1, y1)
    p3 = fc.Vector(x1 + 3 * y1, 0)
    p4 = fc.Vector(x1 + 2 * y1, -y1)
    p5 = fc.Vector(x1, -y1)
    lines = [
        Part.LineSegment(p1, p2),
        Part.Arc(p2, p3, p4),
        Part.LineSegment(p4, p5),
        Part.LineSegment(p5, p1),
    ]
    face = utils.curve_to_face(lines)
    shape = face.extrude(fc.Vector(0, 0, obj.MagnetHoleDepth))

    positions = [
        (45, -x_hole_pos, -y_hole_pos),
        (135, x_hole_pos, -y_hole_pos),
        (225, x_hole_pos, y_hole_pos),
        (315, -x_hole_pos, y_hole_pos),
    ]
    return utils.multi_fuse(
        [
            shape.rotated(fc.Vector(0, 0, 0), fc.Vector(0, 0, 1), angle).translate(fc.Vector(x, y))
            for angle, x, y in positions
        ],
    )
