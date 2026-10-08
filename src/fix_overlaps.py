"""
fix_overlaps.py

CFF/PostScript outlines use the nonzero winding rule with NO automatic
overlap merging (unlike some TrueType rasterizers that tolerate overlaps).
When two contours in a glyph geometrically overlap with OPPOSITE winding
directions, the overlapping region gets winding number 0 and renders as an
unfilled (white) gap -- exactly the symptom of crossing strokes in
handwriting-style connected scripts.

Without a full boolean-geometry library (skia-pathops / booleanOperations,
neither installable offline here), this module applies a practical
heuristic that fontTools itself can compute cheaply:

  1. Compute each contour's signed area (fontTools.pens.areaPen.AreaPen
     integrates the exact area under the bezier segments, so the sign is
     reliable even for curved outlines, not just polygons).
  2. Determine containment: if contour B's bounding box sits entirely
     inside contour A's, B is treated as a "hole" nested in A and should
     have the OPPOSITE sign from A.
  3. Any two contours that are NOT nested in each other, but whose
     bounding boxes still intersect (typical of crossing strokes in a
     connected/cursive design), are forced to the SAME sign so the
     overlap reinforces (winding number 2, still "inside" under nonzero)
     instead of cancelling out to 0.

This is an approximation, not true geometric union -- self-intersecting
outlines can still look slightly different from a proper boolean merge,
but it eliminates the specific white-gap artifact this project has seen.
"""

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.areaPen import AreaPen
from fontTools.pens.pointPen import PointToSegmentPen, SegmentToPointPen


def _bbox_of_segments(segments):
    xs, ys = [], []
    for op, pts in segments:
        for pt in pts:
            xs.append(pt[0])
            ys.append(pt[1])
    if not xs:
        return (0, 0, 0, 0)
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_contains(outer, inner, margin=0.5):
    ox0, oy0, ox1, oy1 = outer
    ix0, iy0, ix1, iy1 = inner
    return ox0 - margin <= ix0 and oy0 - margin <= iy0 and ix1 <= ox1 + margin and iy1 <= oy1 + margin


def _bbox_overlaps(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _signed_area(segments):
    pen = AreaPen(glyphset=None)
    for op, pts in segments:
        if op == "endPath":
            op = "closePath"  # AreaPen can't take open contours; measure as closed
        getattr(pen, op)(*pts) if pts else getattr(pen, op)()
    return pen.value


def _split_contours(recording_pen_value):
    """Split a RecordingPen's .value list into a list of per-contour
    segment lists, splitting on moveTo/closePath boundaries."""
    contours = []
    current = []
    for op, pts in recording_pen_value:
        if op == "moveTo" and current:
            contours.append(current)
            current = []
        current.append((op, pts))
        if op == "closePath":
            contours.append(current)
            current = []
    if current:
        contours.append(current)
    return contours


def _reverse_segments(segments):
    """Reverse a single contour's segment list (flip winding direction)."""
    from fontTools.pens.pointPen import PointToSegmentPen
    from fontTools.pens.reverseContourPen import ReverseContourPen
    from fontTools.pens.recordingPen import RecordingPen

    rec = RecordingPen()
    reverser = ReverseContourPen(rec)
    for op, pts in segments:
        getattr(reverser, op)(*pts) if pts else getattr(reverser, op)()
    return rec.value


def normalize_glyph_overlaps(draw_into_pen_fn):
    """
    draw_into_pen_fn: a function(pen) that draws the glyph's outline into
    the given segment pen (e.g. a lambda calling gs.readGlyph with a
    PointToSegmentPen wrapper).

    Returns a corrected list of (op, pts) segments with contour winding
    directions adjusted to avoid white gaps at overlaps, ready to replay
    into any segment pen (e.g. T2CharStringPen).
    """
    rec = RecordingPen()
    draw_into_pen_fn(rec)
    contours = _split_contours(rec.value)
    if len(contours) <= 1:
        return rec.value

    areas = [_signed_area(c) for c in contours]
    bboxes = [_bbox_of_segments(c) for c in contours]

    n = len(contours)
    # Find a containment parent for each contour (the smallest bbox that
    # still fully contains it), if any.
    parent = [None] * n
    for i in range(n):
        best_parent = None
        best_area = None
        for j in range(n):
            if i == j:
                continue
            if _bbox_contains(bboxes[j], bboxes[i]) and bboxes[j] != bboxes[i]:
                area_j = abs((bboxes[j][2] - bboxes[j][0]) * (bboxes[j][3] - bboxes[j][1]))
                if best_area is None or area_j < best_area:
                    best_area = area_j
                    best_parent = j
        parent[i] = best_parent

    desired_sign = [None] * n

    def resolve(i, visiting=None):
        if desired_sign[i] is not None:
            return desired_sign[i]
        if parent[i] is not None:
            parent_sign = resolve(parent[i])
            desired_sign[i] = -parent_sign  # a nested contour is a hole: opposite sign
        else:
            desired_sign[i] = 1 if areas[i] >= 0 else -1  # top-level: keep its own natural sign as reference
        return desired_sign[i]

    for i in range(n):
        resolve(i)

    # For siblings (no containment relation) whose bboxes still overlap --
    # e.g. two crossing strokes -- force them to match sign so the overlap
    # reinforces instead of cancelling.
    for i in range(n):
        for j in range(i + 1, n):
            if parent[i] == j or parent[j] == i:
                continue  # already handled as a real nested hole
            if _bbox_overlaps(bboxes[i], bboxes[j]):
                desired_sign[j] = desired_sign[i]

    corrected = []
    for i, c in enumerate(contours):
        actual_sign = 1 if areas[i] >= 0 else -1
        if actual_sign != desired_sign[i]:
            c = _reverse_segments(c)
        corrected.extend(c)

    return corrected
