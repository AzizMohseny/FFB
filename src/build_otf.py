"""
build_otf.py

A minimal UFO -> OTF compiler built directly on fontTools (no ufo2ft,
which isn't installable in this offline environment). Reads outlines,
metrics, and metadata straight from the UFO's .glif/plist files and
assembles a CFF-flavored OTF, then compiles the project's generated
GSUB/GPOS .fea files into it via fontTools.feaLib.

This intentionally reimplements a small slice of what ufo2ft does, only
covering what this project's fonts need: single-master CFF outlines
(no components needed here, no variable font support, no OpenType hinting).

Usage:
    python3 build_otf.py <ufo_path> <features.fea ...> --out font.otf
"""

import argparse
import plistlib
import re
from pathlib import Path

from fontTools.ttLib import TTFont, newTable
from fontTools.ufoLib.glifLib import GlyphSet
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.cffLib import CFFFontSet, TopDictIndex, TopDict, PrivateDict, GlobalSubrsIndex, CharStrings, IndexedStrings
from fontTools.misc.psCharStrings import T2CharString
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString


# ---------------------------------------------------------------------------
# UFO reading helpers
# ---------------------------------------------------------------------------

class _GlyphRecorder:
    """Captures everything glifLib.readGlyph gives us for one glyph."""

    def __init__(self):
        self.width = 0
        self.height = 0
        self.unicodes = []
        self.anchors = []
        self.components = []
        self._pen_data = None  # filled in by caller via drawPoints

    def setWidth(self, w):
        self.width = w

    def setHeight(self, h):
        self.height = h

    def addUnicode(self, code):
        self.unicodes.append(code)

    def addAnchor(self, anchorDict):
        self.anchors.append(dict(anchorDict))

    def addComponent(self, baseName, transformation, identifier=None, **kwargs):
        self.components.append((baseName, transformation))

    def addImage(self, *a, **k):
        pass

    def addGuideline(self, *a, **k):
        pass

    def addLib(self, *a, **k):
        pass

    # glifLib will also call drawPoints(pointPen) if we implement it via a
    # PointPen adapter; simplest path is to use glifLib's built-in
    # `readGlyphFromString` with a pointPen bridging to a segment pen.


def load_ufo(ufo_path: Path):
    """Returns (glyph_order, {name: GlyphRecord}, unitsPerEm, fontinfo dict)."""
    with open(ufo_path / "fontinfo.plist", "rb") as f:
        fontinfo = plistlib.load(f)
    with open(ufo_path / "lib.plist", "rb") as f:
        lib = plistlib.load(f)
    glyph_order = lib.get("public.glyphOrder")

    gs = GlyphSet(str(ufo_path / "glyphs"))
    if not glyph_order:
        glyph_order = sorted(gs.keys())

    records = {}
    for name in gs.keys():
        rec = _GlyphRecorder()
        gs.readGlyph(name, rec, pointPen=None)
        records[name] = rec

    return glyph_order, records, fontinfo.get("unitsPerEm", 1000), fontinfo


# ---------------------------------------------------------------------------
# Outline extraction (contours -> T2 charstrings) via PointPen bridge
# ---------------------------------------------------------------------------

from fontTools.pens.pointPen import PointToSegmentPen


class _UFOGlyphProxy:
    """Makes a single UFO glyph look like the 'glyph' objects BasePen's
    addComponent() expects: something with a .draw(pen) method, so nested
    components can be decomposed recursively."""

    def __init__(self, glyphset, name):
        self._gs = glyphset
        self._name = name

    def draw(self, pen):
        point_pen = PointToSegmentPen(pen)
        self._gs.readGlyph(self._name, _NoOpRecorder(), pointPen=point_pen)


class _UFOGlyphSetProxy:
    """dict-like: glyphSetProxy[name] -> _UFOGlyphProxy, as required by
    fontTools.pens.basePen.BasePen.addComponent()."""

    def __init__(self, glyphset):
        self._gs = glyphset

    def __getitem__(self, name):
        return _UFOGlyphProxy(self._gs, name)

    def __contains__(self, name):
        return name in self._gs


class _NoOpRecorder:
    def setWidth(self, w):
        pass
    def setHeight(self, h):
        pass
    def addUnicode(self, code):
        pass
    def addAnchor(self, a):
        pass
    def addComponent(self, baseName, transformation, identifier=None, **k):
        pass
    def addImage(self, *a, **k):
        pass
    def addGuideline(self, *a, **k):
        pass
    def addLib(self, *a, **k):
        pass


from fontTools.pens.recordingPen import DecomposingRecordingPen, RecordingPen
from fix_overlaps import normalize_glyph_overlaps, _split_contours, _signed_area, _bbox_of_segments


def build_charstring(ufo_path: Path, glyph_name: str, width: int, private, globalSubrs):
    """Read one glyph's outline directly and convert to a T2CharString,
    decomposing any UFO components and normalizing contour winding
    direction to avoid white gaps where strokes overlap (see
    fix_overlaps.py) along the way."""
    gs = GlyphSet(str(ufo_path / "glyphs"))
    glyphset_proxy = _UFOGlyphSetProxy(gs)

    def draw_fully_decomposed(pen):
        decomposing = DecomposingRecordingPen(glyphset_proxy)
        point_pen = PointToSegmentPen(decomposing)
        gs.readGlyph(glyph_name, _NoOpRecorder(), pointPen=point_pen)
        decomposing.replay(pen)

    corrected_segments = normalize_glyph_overlaps(draw_fully_decomposed)

    t2pen = T2CharStringPen(width, None)
    for op, pts in corrected_segments:
        getattr(t2pen, op)(*pts) if pts else getattr(t2pen, op)()
    return t2pen.getCharString(private, globalSubrs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ufo_path")
    ap.add_argument("fea_files", nargs="+")
    ap.add_argument("--out", default="font.otf")
    ap.add_argument("--allow-open-contours", action="store_true",
                    help="build even if the UFO has open contours (single-line/skeleton "
                         "drawings). They will NOT be stroked: renderers fill them as "
                         "degenerate shapes, so the result will look wrong.")
    args = ap.parse_args()

    ufo_path = Path(args.ufo_path)
    glyph_order, records, upm, fontinfo = load_ufo(ufo_path)

    print(f"Loaded UFO: {len(glyph_order)} glyphs, unitsPerEm={upm}")

    # Guard: this compiler fills outlines. Open contours (single-line fonts)
    # need to be expanded to filled outlines first (e.g. stroke/offset in
    # FontLab or Glyphs); otherwise the output is garbage.
    import re as _re
    n_open, open_glyphs = 0, []
    for _p in sorted((Path(args.ufo_path) / "glyphs").glob("*.glif")):
        _n = len(_re.findall(r'<point [^>]*type="move"', _p.read_text(encoding="utf-8")))
        if _n:
            n_open += _n
            open_glyphs.append(_p.stem)
    if n_open:
        msg = (f"{n_open} open contour(s) in {len(open_glyphs)} glyph(s) "
               f"(e.g. {', '.join(open_glyphs[:5])}). This looks like a single-line font; "
               "its strokes must be expanded to closed outlines before building.")
        if not args.allow_open_contours:
            raise SystemExit("ERROR: " + msg + "\nUse --allow-open-contours to build anyway.")
        print("WARNING: " + msg)

    # Ensure a space (U+0020) glyph exists -- many Arabic-only UFOs never
    # draw one, which breaks word-spacing and can make some apps refuse to
    # render text at all. Synthesize a blank one if missing.
    has_space = any(0x20 in r.unicodes for r in records.values())
    synthesized_glyphs = set()
    if not has_space:
        space_width = round(upm / 3)
        print(f"No U+0020 (space) glyph found -- synthesizing one (width={space_width}).")
        glyph_order.append("space")
        synth = _GlyphRecorder()
        synth.width = space_width
        synth.unicodes = [0x20]
        records["space"] = synth
        synthesized_glyphs.add("space")

    font = TTFont()
    font.sfntVersion = "OTTO"  # CFF-flavored OpenType; must match the CFF outlines below
    font.setGlyphOrder(glyph_order)

    # --- CFF table -------------------------------------------------------
    cff = CFFFontSet()
    cff.major, cff.minor = 1, 0
    cff.fontNames = [fontinfo.get("postscriptFontName", "MasterRegular")]

    strings = IndexedStrings()
    private = PrivateDict(strings=strings)
    globalSubrs = GlobalSubrsIndex()

    topDict = TopDict(strings=strings)
    topDict.charset = glyph_order
    topDict.Private = private
    topDict.FontMatrix = [1.0 / upm, 0, 0, 1.0 / upm, 0, 0]
    topDict.FontBBox = [0, fontinfo.get("descender", -250), upm, fontinfo.get("ascender", upm)]

    charstrings = CharStrings(None, None, globalSubrs, private, glyph_order, None)
    charstrings.charStringsIndex = None  # populated below via direct dict assignment
    cs_dict = {}
    for name in glyph_order:
        rec = records.get(name)
        width = rec.width if rec else 0
        if name in synthesized_glyphs:
            # synthesized blank glyph (e.g. space) -- no outline to read from disk
            cs_dict[name] = T2CharStringPen(width, None).getCharString(private, globalSubrs)
            continue
        try:
            cs = build_charstring(ufo_path, name, width, private, globalSubrs)
        except KeyError:
            # glyph in glyphOrder but missing on disk (shouldn't normally happen)
            cs = T2CharStringPen(width, None).getCharString(private, globalSubrs)
        cs_dict[name] = cs
    charstrings.charStrings = cs_dict

    topDict.CharStrings = charstrings
    topDict.FontName = cff.fontNames[0]

    cff.topDictIndex = TopDictIndex()
    cff.topDictIndex.append(topDict)
    cff.GlobalSubrs = globalSubrs
    cff.strings = strings

    font["CFF "] = newTable("CFF ")
    font["CFF "].cff = cff

    # --- cmap --------------------------------------------------------------
    cmap_table = newTable("cmap")
    cmap_table.tableVersion = 0
    from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
    mapping = {}
    for name, rec in records.items():
        for code in rec.unicodes:
            mapping[code] = name
    subtable = CmapSubtable.getSubtableClass(4)(4)
    subtable.platformID, subtable.platEncID, subtable.format, subtable.language = 3, 1, 4, 0
    subtable.cmap = mapping
    cmap_table.tables = [subtable]
    font["cmap"] = cmap_table

    # --- hmtx / hhea ---------------------------------------------------------
    hmtx = newTable("hmtx")
    hmtx.metrics = {name: (records[name].width if name in records else 0, 0) for name in glyph_order}
    font["hmtx"] = hmtx

    hhea = newTable("hhea")
    hhea.tableVersion = 0x00010000
    hhea.ascent = fontinfo.get("openTypeHheaAscender", fontinfo.get("ascender", upm))
    hhea.descent = fontinfo.get("openTypeHheaDescender", fontinfo.get("descender", -upm // 4))
    hhea.lineGap = fontinfo.get("openTypeHheaLineGap", 0)
    hhea.advanceWidthMax = max((m[0] for m in hmtx.metrics.values()), default=upm)
    hhea.minLeftSideBearing = 0
    hhea.minRightSideBearing = 0
    hhea.xMaxExtent = upm
    hhea.caretSlopeRise = 1
    hhea.caretSlopeRun = 0
    hhea.caretOffset = 0
    hhea.reserved0 = hhea.reserved1 = hhea.reserved2 = hhea.reserved3 = 0
    hhea.metricDataFormat = 0
    hhea.numberOfHMetrics = len(glyph_order)
    font["hhea"] = hhea

    # --- maxp ----------------------------------------------------------------
    maxp = newTable("maxp")
    maxp.tableVersion = 0x00005000  # CFF outlines -> version 0.5
    maxp.numGlyphs = len(glyph_order)
    font["maxp"] = maxp

    # --- head ------------------------------------------------------------
    head = newTable("head")
    head.tableVersion = 1.0
    head.fontRevision = 1.0
    head.checkSumAdjustment = 0
    head.magicNumber = 0x5F0F3CF5
    head.flags = 0x000B
    head.unitsPerEm = upm
    import time
    mac_epoch_now = int(time.time()) + 2082844800  # seconds from 1904-01-01 to 1970-01-01 + now
    head.created = head.modified = mac_epoch_now
    xs = []
    ys = []
    head.xMin, head.yMin, head.xMax, head.yMax = 0, fontinfo.get("descender", -250), upm, fontinfo.get("ascender", upm)
    head.macStyle = 0
    head.lowestRecPPEM = 6
    head.fontDirectionHint = 2
    head.indexToLocFormat = 0
    head.glyphDataFormat = 0
    font["head"] = head

    # --- OS/2 --------------------------------------------------------------
    os2 = newTable("OS/2")
    os2.version = 4
    os2.xAvgCharWidth = int(sum(m[0] for m in hmtx.metrics.values()) / max(len(hmtx.metrics), 1))
    os2.usWeightClass = 400
    os2.usWidthClass = 5
    os2.fsType = 0
    for attr in ("ySubscriptXSize", "ySubscriptYSize", "ySubscriptXOffset", "ySubscriptYOffset",
                 "ySuperscriptXSize", "ySuperscriptYSize", "ySuperscriptXOffset", "ySuperscriptYOffset",
                 "yStrikeoutSize", "yStrikeoutPosition"):
        setattr(os2, attr, 0)
    os2.sFamilyClass = 0
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    os2.panose = Panose()
    for i in range(1, 5):
        setattr(os2, f"ulUnicodeRange{i}", 0)
    os2.achVendID = "NONE"
    os2.fsSelection = 0x40
    os2.usFirstCharIndex = min(mapping.keys(), default=0x20)
    os2.usLastCharIndex = max(mapping.keys(), default=0x7E)
    os2.sTypoAscender = fontinfo.get("openTypeOS2TypoAscender", fontinfo.get("ascender", upm))
    os2.sTypoDescender = fontinfo.get("openTypeOS2TypoDescender", fontinfo.get("descender", -upm // 4))
    os2.sTypoLineGap = fontinfo.get("openTypeOS2TypoLineGap", 0)
    os2.usWinAscent = fontinfo.get("openTypeOS2WinAscent", fontinfo.get("ascender", upm))
    os2.usWinDescent = abs(fontinfo.get("openTypeOS2WinDescent", fontinfo.get("descender", -upm // 4)))
    os2.ulCodePageRange1 = 1 << 1  # Latin 1 + Arabic bit set below
    os2.ulCodePageRange1 |= 1 << 4  # Arabic codepage bit
    os2.ulCodePageRange2 = 0
    os2.sxHeight = fontinfo.get("xHeight", int(upm * 0.5))
    os2.sCapHeight = fontinfo.get("capHeight", int(upm * 0.7))
    os2.usDefaultChar = 0
    os2.usBreakChar = 0x20
    os2.usMaxContext = 8
    font["OS/2"] = os2

    # --- post --------------------------------------------------------------
    post = newTable("post")
    post.formatType = 3.0
    post.italicAngle = fontinfo.get("italicAngle", 0)
    post.underlinePosition = fontinfo.get("postscriptUnderlinePosition", -75)
    post.underlineThickness = fontinfo.get("postscriptUnderlineThickness", 50)
    post.isFixedPitch = 0
    post.minMemType42 = post.maxMemType42 = post.minMemType1 = post.maxMemType1 = 0
    font["post"] = post

    # --- DSIG (stub) ---------------------------------------------------------
    # Microsoft Word on Windows will not reliably apply a font -- or will
    # ignore its OpenType Layout features (GSUB/GPOS) -- if it has no DSIG
    # table at all, even an empty placeholder one. No real signature is
    # needed; an empty stub is standard practice and satisfies Word's check.
    from fontTools.ttLib.tables.D_S_I_G_ import table_D_S_I_G_
    dsig = table_D_S_I_G_()
    dsig.ulVersion = 1
    dsig.usFlag = 0
    dsig.usNumSigs = 0
    dsig.signatureRecords = []
    font["DSIG"] = dsig

    # --- name ----------------------------------------------------------------
    name_table = newTable("name")
    family = fontinfo.get("familyName", "Master")
    style = fontinfo.get("styleName", "Regular")
    full = f"{family} {style}"
    ps_name = fontinfo.get("postscriptFontName", full.replace(" ", ""))
    name_records = [
        (1, family), (2, style), (3, f"1.000;NONE;{ps_name}"),
        (4, full), (5, "Version 1.000"), (6, ps_name),
    ]
    for nameID, value in name_records:
        name_table.setName(value, nameID, 3, 1, 0x409)
        name_table.setName(value, nameID, 1, 0, 0)
    font["name"] = name_table

    print("Built base tables. Compiling GSUB/GPOS features...")

    combined_fea = "\n\n".join(Path(p).read_text(encoding="utf-8") for p in args.fea_files)
    tmp_fea = Path("/tmp/_combined_features.fea")
    tmp_fea.write_text(combined_fea, encoding="utf-8")

    addOpenTypeFeaturesFromString(font, combined_fea, filename=str(tmp_fea))

    font.save(args.out)
    print(f"Saved: {args.out}")


if __name__ == "__main__":
    main()
