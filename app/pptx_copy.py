"""Copies one slide's real content (shapes, text, images, tables,
formatting) from a source .pptx into a target .pptx being built.

python-pptx has no built-in "copy this slide into another deck" — this is
the well-known low-level workaround: add a blank slide in the target, then
deep-copy every shape element from the source slide's XML tree into it, and
re-point every relationship (images, hyperlinks) the copied shapes refer to
at freshly created relationships in the target part.

What this does NOT carry over: the source slide's own master/theme (colors,
fonts, background, logo baked into the layout) — the copied slide uses the
target deck's layout instead. In practice, most real slides set their own
fonts/colors/positions explicitly and look right regardless; slides that
lean on inherited placeholder styling can look slightly different. Slides
with charts, SmartArt or embedded OLE objects are flagged as unsupported so
the caller can fall back to a rendered image instead of risking a corrupt
shape.
"""
from __future__ import annotations

import copy
import io

from pptx.oxml.ns import qn

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_SLIDE_LAYOUT_RELTYPE = R_NS + "/slideLayout"
_R_ATTRS = {
    qn("r:embed"), qn("r:link"), qn("r:id"), qn("r:pict"), qn("r:href"),
}
# python-pptx's own prefix map registers the markup-compatibility namespace
# as "ve", not the more common "mc" — qn("mc:...") raises KeyError, so this
# tag is matched by its Clark-notation name directly instead.
_ALTERNATE_CONTENT_TAG = "{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"

def slide_has_unsupported_content(slide) -> bool:
    """True if the slide contains a chart, embedded OLE object, or SmartArt
    — content the simple XML copy below can't safely reproduce (those parts
    carry their own separate data parts and relationships this copier
    doesn't follow)."""
    tree = slide.shapes._spTree
    for el in tree.iter():
        if el.tag == qn("p:graphicFrame"):
            # A graphicFrame is fine if it's just a plain table; charts,
            # SmartArt and embedded objects use other graphicData URIs.
            graphic_data = el.find(qn("a:graphic") + "/" + qn("a:graphicData"))
            uri = (graphic_data.get("uri") if graphic_data is not None else "") or ""
            if uri and "/table" not in uri:
                return True
        if el.tag == _ALTERNATE_CONTENT_TAG:
            # Fallback-wrapped content (some newer chart/shape types) —
            # copying only one branch risks a broken shape, so bail out.
            return True
    return False


def _pick_blank_layout(target_prs):
    for layout in target_prs.slide_layouts:
        if layout.name.strip().lower() == "blank":
            return layout
    # Fall back to the last layout, which is conventionally "Blank" in the
    # default python-pptx template, or just the last available one.
    return target_prs.slide_layouts[-1]


def copy_slide_native(source_prs, source_slide, target_prs, layout=None):
    """Append a copy of source_slide to target_prs and return the new slide."""
    layout = layout or _pick_blank_layout(target_prs)
    new_slide = target_prs.slides.add_slide(layout)

    # Strip whatever placeholder shapes the layout put on the new slide —
    # we're replacing the slide's content wholesale with the source's own.
    for shape in list(new_slide.shapes):
        shape._element.getparent().remove(shape._element)

    src_tree = source_slide.shapes._spTree
    dst_tree = new_slide.shapes._spTree
    skip_tags = {qn("p:nvGrpSpPr"), qn("p:grpSpPr")}
    for child in src_tree.iterchildren():
        if child.tag in skip_tags:
            continue
        dst_tree.append(copy.deepcopy(child))

    _copy_relationships(source_slide, new_slide)
    _copy_background(source_slide, new_slide)
    return new_slide


def _copy_relationships(source_slide, new_slide) -> None:
    rel_map: dict[str, str] = {}
    for rel_id, rel in list(source_slide.part.rels.items()):
        try:
            if rel.is_external:
                if "hyperlink" in rel.reltype:
                    new_rid = new_slide.part.relate_to(rel.target_ref, rel.reltype, is_external=True)
                    rel_map[rel_id] = new_rid
                continue
            if "image" in rel.reltype:
                # Register the image in the TARGET package's own image-part
                # registry (get_or_add_image_part), rather than reusing the
                # source part object as-is: that part's partname (e.g.
                # "/ppt/media/image1.png") was assigned within the SOURCE
                # package's own numbering and can collide with an unrelated
                # image the target package numbers the same way, producing
                # two zip entries at the same path — a corrupt .pptx that
                # some viewers silently mangle and others (LibreOffice)
                # refuse to open. get_or_add_image_part also de-dupes
                # identical images by content hash.
                image_bytes = rel.target_part.blob
                image_part, new_rid = new_slide.part.get_or_add_image_part(io.BytesIO(image_bytes))
                rel_map[rel_id] = new_rid
            elif rel.reltype == _SLIDE_LAYOUT_RELTYPE:
                continue
            else:
                # A relationship we do not copy leaves the source rId in the
                # XML. PowerPoint may then show an empty icon or reject the
                # exported package as damaged; let the exporter use its
                # rendered-image fallback instead.
                raise ValueError(f"unsupported slide relationship: {rel.reltype}")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"could not copy slide relationship {rel_id}") from exc

    if not rel_map:
        return
    for el in new_slide.shapes._spTree.iter():
        for attr in list(el.attrib.keys()):
            if attr in _R_ATTRS or attr.startswith("{%s}" % R_NS):
                val = el.get(attr)
                if val in rel_map:
                    el.set(attr, rel_map[val])


def _copy_background(source_slide, new_slide) -> None:
    src_bg = source_slide._element.find(qn("p:cSld") + "/" + qn("p:bg"))
    if src_bg is None:
        return
    dst_cSld = new_slide._element.find(qn("p:cSld"))
    existing = dst_cSld.find(qn("p:bg"))
    if existing is not None:
        dst_cSld.remove(existing)
    dst_cSld.insert(0, copy.deepcopy(src_bg))
