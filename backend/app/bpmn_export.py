"""FAM -> BPMN 2.0 export.

A FAM stores its workflow in BBO terms, and BBO is an OWL rendering of the
BPMN 2.0 metamodel - so the process structure maps 1:1 onto BPMN XML:
bbo:Process -> <process>, bbo:SubProcess -> <subProcess>, the task/event/
gateway classes -> their BPMN elements, and the sequence flows ->
<sequenceFlow> (a ConditionalSequenceFlow carries its routesOn trigger as
the <conditionExpression> text).

What a FAM does NOT store is a diagram. BPMN tools (bpmn-js, bpmn.io,
Camunda Modeler) only display files that carry a BPMNDiagram section with
explicit coordinates, so this module also computes a layout:

- layered left to right per container: a node's column is the length of the
  longest path from the start event, counting only forward edges;
- gateway branches get their own rows: the first outgoing flow stays on the
  source's row, every further one opens a row below;
- loop back edges (flows that would close a cycle) are excluded from the
  ranking and routed through a lane below the rows;
- a subprocess is laid out first and then placed in its parent as a single
  node of the resulting size, expanded, with its children visible inside.

Entry point: ``fam_to_bpmn(graph, name) -> str`` (BPMN 2.0 XML).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from rdflib import RDF, RDFS, Graph, Namespace, URIRef

logger = logging.getLogger("ontoui_app")

BBO = Namespace("https://www.irit.fr/recherches/MELODI/ontologies/BBO#")
OBOP = Namespace("http://purl.org/net/obop/")

_BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
_BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
_DC = "http://www.omg.org/spec/DD/20100524/DC"
_DI = "http://www.omg.org/spec/DD/20100524/DI"
_XSI = "http://www.w3.org/2001/XMLSchema-instance"

# The BPMN semantic elements go into the default namespace, so the file
# reads like hand-written BPMN; DI keeps its conventional prefixes.
ET.register_namespace("", _BPMN)
ET.register_namespace("bpmndi", _BPMNDI)
ET.register_namespace("dc", _DC)
ET.register_namespace("di", _DI)
ET.register_namespace("xsi", _XSI)

# BBO flow-node class -> BPMN element tag. Checked in order, first type of
# the node that appears here wins (relevant when a node carries several
# types, e.g. a SubProcess that is also typed as an Activity).
_NODE_TAGS: tuple[tuple[URIRef, str], ...] = (
    (BBO.SubProcess, "subProcess"),
    (BBO.ProcessStartEvent, "startEvent"),
    (BBO.SubProcessStartEvent, "startEvent"),
    (BBO.StartEvent, "startEvent"),
    (BBO.EndEvent, "endEvent"),
    (BBO.UserTask, "userTask"),
    (BBO.ScriptTask, "scriptTask"),
    (BBO.Task, "task"),
    (BBO.ExclusiveGateway, "exclusiveGateway"),
    (BBO.Gateway, "exclusiveGateway"),
)

# Element sizes in diagram units - the defaults bpmn-js draws with.
_SIZES = {
    "startEvent": (36.0, 36.0),
    "endEvent": (36.0, 36.0),
    "exclusiveGateway": (50.0, 50.0),
}
_TASK_SIZE = (100.0, 80.0)
_H_GAP = 60.0  # between columns
_V_GAP = 40.0  # between rows, and the extra lane for back edges
_SUB_PAD = 40.0  # padding between a subprocess border and its children
_MARGIN = 40.0  # margin of the whole plane


@dataclass
class _Node:
    iri: URIRef
    tag: str
    label: str
    doc: str | None
    width: float
    height: float
    children: _Layout | None = None  # the inner layout of a subProcess
    # local position within the container (set by the layout), then
    # translated to absolute plane coordinates (BPMN DI uses absolute
    # coordinates even for elements nested in a subprocess)
    x: float = 0.0
    y: float = 0.0

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2


@dataclass
class _Flow:
    iri: URIRef
    source: URIRef
    target: URIRef
    name: str | None
    condition_text: str | None
    is_back_edge: bool = False
    waypoints: list[tuple[float, float]] = field(default_factory=list)


@dataclass
class _Layout:
    nodes: dict[URIRef, _Node]
    flows: list[_Flow]
    width: float = 0.0
    height: float = 0.0


def fam_to_bpmn(graph: Graph, name: str = "Application process") -> str:
    """Serialize the FAM's workflow as a displayable BPMN 2.0 XML document."""
    return _Exporter(graph).export(name)


def _local(iri) -> str:
    """The last path/fragment segment of an IRI - the human-meaningful part."""
    s = str(iri)
    return s.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


class _Exporter:
    def __init__(self, graph: Graph):
        self.g = graph
        # IRI -> XML id. BPMN ids must be NCNames and unique in the file.
        self._ids: dict[URIRef, str] = {}

    # -- reading the FAM -----------------------------------------------------

    def export(self, name: str) -> str:
        main = self._main_process()
        layout = self._layout_container(main)
        self._place(layout, _MARGIN, _MARGIN)
        return self._to_xml(main, name, layout)

    def _main_process(self) -> URIRef:
        processes = [
            p
            for p in self.g.subjects(RDF.type, BBO.Process)
            if (p, RDF.type, BBO.SubProcess) not in self.g
        ]
        if not processes:
            raise ValueError("The model contains no bbo:Process to export.")
        if len(processes) > 1:
            logger.warning(
                f"Model has {len(processes)} bbo:Process nodes; exporting "
                f"the first ({processes[0]})."
            )
        return sorted(processes)[0]

    def _node_tag(self, iri: URIRef) -> str | None:
        types = set(self.g.objects(iri, RDF.type))
        return next((tag for cls, tag in _NODE_TAGS if cls in types), None)

    def _label(self, iri: URIRef) -> str:
        label = self.g.value(iri, RDFS.label)
        return str(label) if label else _local(iri).replace("_", " ")

    def _condition_text(self, flow: URIRef) -> str | None:
        cond = self.g.value(flow, BBO.has_conditionExpression)
        if cond is None:
            return None
        # The trigger the condition routes on (R9): an action the user
        # selected or a decision the engine published.
        for pred, words in (
            (OBOP.selectedAction, "selected action"),
            (OBOP.engineDecision, "engine decision"),
        ):
            value = self.g.value(cond, pred)
            if value is not None:
                return f"{words} = {_local(value)}"
        comment = self.g.value(cond, RDFS.comment)
        return str(comment) if comment else _local(cond)

    def _layout_container(self, container: URIRef) -> _Layout:
        """Collect the container's flow nodes and flows and lay them out."""
        nodes: dict[URIRef, _Node] = {}
        flows: list[_Flow] = []
        for member in sorted(self.g.subjects(BBO.has_container, container)):
            if not isinstance(member, URIRef):
                continue
            source = self.g.value(member, BBO.has_sourceRef)
            target = self.g.value(member, BBO.has_targetRef)
            if source is not None and target is not None:
                condition = self._condition_text(member)
                flows.append(
                    _Flow(
                        iri=member,
                        source=source,
                        target=target,
                        # the trigger makes a useful short edge label
                        name=condition.split(" = ")[-1] if condition else None,
                        condition_text=condition,
                    )
                )
                continue
            tag = self._node_tag(member)
            if tag is None:
                continue  # not a flow node (e.g. a data object)
            children = (
                self._layout_container(member) if tag == "subProcess" else None
            )
            if children is not None:
                width = children.width + 2 * _SUB_PAD
                height = children.height + 2 * _SUB_PAD
            else:
                width, height = _SIZES.get(tag, _TASK_SIZE)
            comment = self.g.value(member, RDFS.comment)
            nodes[member] = _Node(
                iri=member,
                tag=tag,
                label=self._label(member),
                doc=str(comment) if comment else None,
                width=width,
                height=height,
                children=children,
            )
        # a flow whose endpoint is missing from the container cannot be drawn
        kept = []
        for flow in flows:
            if flow.source in nodes and flow.target in nodes:
                kept.append(flow)
            else:
                logger.warning(
                    f"BPMN export: dropping flow {flow.iri} - its source or "
                    f"target is not a flow node of {container}."
                )
        layout = _Layout(nodes=nodes, flows=kept)
        self._assign_grid(layout)
        return layout

    # -- layout --------------------------------------------------------------

    def _assign_grid(self, layout: _Layout) -> None:
        """Give every node a (column, row) cell, then local coordinates."""
        nodes, flows = layout.nodes, layout.flows
        succ: dict[URIRef, list[_Flow]] = {n: [] for n in nodes}
        for flow in flows:
            succ[flow.source].append(flow)

        # 1) Back edges: a DFS edge that points at a node still on the stack
        # closes a cycle (a loop in the workflow). Excluding those edges
        # makes the remaining graph acyclic, which the ranking needs.
        state: dict[URIRef, int] = {}  # 1 = on stack, 2 = done
        roots = [
            n
            for n in nodes
            if not any(f.target == n for f in flows)
        ] or list(nodes)
        for root in roots:
            if state.get(root):
                continue
            stack: list[tuple[URIRef, int]] = [(root, 0)]
            state[root] = 1
            while stack:
                node, i = stack[-1]
                if i < len(succ[node]):
                    stack[-1] = (node, i + 1)
                    flow = succ[node][i]
                    if state.get(flow.target) == 1:
                        flow.is_back_edge = True
                    elif not state.get(flow.target):
                        state[flow.target] = 1
                        stack.append((flow.target, 0))
                else:
                    state[node] = 2
                    stack.pop()

        forward = [f for f in flows if not f.is_back_edge]

        # 2) Column = longest forward path from a root (Kahn's algorithm:
        # process nodes only once all their predecessors are ranked).
        indeg = {n: 0 for n in nodes}
        for flow in forward:
            indeg[flow.target] += 1
        col = {n: 0 for n in nodes}
        queue = [n for n in nodes if indeg[n] == 0]
        topo: list[URIRef] = []
        while queue:
            node = queue.pop(0)
            topo.append(node)
            for flow in succ[node]:
                if flow.is_back_edge:
                    continue
                col[flow.target] = max(col[flow.target], col[node] + 1)
                indeg[flow.target] -= 1
                if indeg[flow.target] == 0:
                    queue.append(flow.target)

        # 3) Row: the first outgoing flow continues on the source's row (the
        # "happy path" stays a straight line); every further branch of a
        # gateway opens a new row below. A node that several flows join
        # keeps the row of whichever predecessor reached it first.
        # "First" = the branch that continues deepest, so the longest chain
        # (submit -> validate -> save -> ... -> end) is the straight line and
        # short branches (cancel -> abort) hang below it.
        depth = {n: 0 for n in nodes}
        for node in reversed(topo):
            for flow in succ[node]:
                if not flow.is_back_edge:
                    depth[node] = max(depth[node], depth[flow.target] + 1)
        for flows_of_node in succ.values():
            flows_of_node.sort(key=lambda f: (-depth[f.target], str(f.iri)))
        row = {n: 0 for n in nodes}
        assigned: set[URIRef] = set()
        next_row = 0
        for i, node in enumerate(topo):
            if node not in assigned:
                row[node] = next_row if i == 0 else next_row + 1
                next_row = row[node]
                assigned.add(node)
            for flow in succ[node]:
                if flow.is_back_edge or flow.target in assigned:
                    continue
                if any(
                    f.target in assigned and row[f.target] == row[node]
                    for f in succ[node]
                    if f is not flow and not f.is_back_edge
                ):
                    next_row += 1
                    row[flow.target] = next_row
                else:
                    row[flow.target] = row[node]
                assigned.add(flow.target)

        # 4) Cells -> local coordinates. Every column is as wide as its
        # widest node, every row as tall as its tallest; nodes are centered
        # in their cell so flows between events, tasks and gateways align.
        col_w: dict[int, float] = {}
        row_h: dict[int, float] = {}
        for n, node in nodes.items():
            col_w[col[n]] = max(col_w.get(col[n], 0.0), node.width)
            row_h[row[n]] = max(row_h.get(row[n], 0.0), node.height)
        col_cx: dict[int, float] = {}
        x = 0.0
        for c in sorted(col_w):
            col_cx[c] = x + col_w[c] / 2
            x += col_w[c] + _H_GAP
        row_cy: dict[int, float] = {}
        y = 0.0
        for r in sorted(row_h):
            row_cy[r] = y + row_h[r] / 2
            y += row_h[r] + _V_GAP
        for n, node in nodes.items():
            node.x = col_cx[col[n]] - node.width / 2
            node.y = row_cy[row[n]] - node.height / 2
        layout.width = max(x - _H_GAP, 0.0)
        layout.height = max(y - _V_GAP, 0.0)
        if any(f.is_back_edge for f in flows):
            # reserve a lane below the rows for the loop edges
            layout.height += _V_GAP

    def _place(self, layout: _Layout, dx: float, dy: float) -> None:
        """Translate local coordinates to absolute ones, recurse, route edges."""
        for node in layout.nodes.values():
            node.x += dx
            node.y += dy
            if node.children is not None:
                self._place(node.children, node.x + _SUB_PAD, node.y + _SUB_PAD)
        back_lane = dy + layout.height - _V_GAP / 2
        back_seen = 0
        for flow in layout.flows:
            s = layout.nodes[flow.source]
            t = layout.nodes[flow.target]
            if flow.is_back_edge:
                # down from the source, left through the lane, up into the
                # target's bottom; stacked lanes if there are several loops
                lane = back_lane - 10 * back_seen
                back_seen += 1
                flow.waypoints = [
                    (s.cx, s.y + s.height),
                    (s.cx, lane),
                    (t.cx, lane),
                    (t.cx, t.y + t.height),
                ]
            elif abs(s.cy - t.cy) < 1:
                flow.waypoints = [(s.x + s.width, s.cy), (t.x, t.cy)]
            else:
                # an elbow: out of the source's right edge, vertical jog
                # halfway, into the target's left edge
                mid = (s.x + s.width + t.x) / 2
                flow.waypoints = [
                    (s.x + s.width, s.cy),
                    (mid, s.cy),
                    (mid, t.cy),
                    (t.x, t.cy),
                ]

    # -- XML -----------------------------------------------------------------

    def _id(self, iri: URIRef) -> str:
        """A unique NCName for the element (BPMN ids may not contain ':', '/'...)."""
        if iri not in self._ids:
            base = re.sub(r"[^A-Za-z0-9_.-]", "_", _local(iri)) or "element"
            if not re.match(r"[A-Za-z_]", base):
                base = f"_{base}"
            candidate, n = base, 1
            while candidate in self._ids.values():
                n += 1
                candidate = f"{base}_{n}"
            self._ids[iri] = candidate
        return self._ids[iri]

    def _to_xml(self, main: URIRef, name: str, layout: _Layout) -> str:
        definitions = ET.Element(
            f"{{{_BPMN}}}definitions",
            {
                "id": "Definitions_1",
                "targetNamespace": "http://purl.org/net/obop/bpmn",
                "exporter": "OntoUI",
            },
        )
        process = ET.SubElement(
            definitions,
            f"{{{_BPMN}}}process",
            {"id": self._id(main), "name": name, "isExecutable": "false"},
        )
        self._emit_semantic(process, layout)

        diagram = ET.SubElement(
            definitions, f"{{{_BPMNDI}}}BPMNDiagram", {"id": "Diagram_1"}
        )
        plane = ET.SubElement(
            diagram,
            f"{{{_BPMNDI}}}BPMNPlane",
            {"id": "Plane_1", "bpmnElement": self._id(main)},
        )
        self._emit_di(plane, layout)

        ET.indent(definitions)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            definitions, encoding="unicode"
        )

    def _emit_semantic(self, parent: ET.Element, layout: _Layout) -> None:
        """The flow elements of one container, subprocesses nested recursively."""
        incoming: dict[URIRef, list[URIRef]] = {}
        outgoing: dict[URIRef, list[URIRef]] = {}
        for flow in layout.flows:
            outgoing.setdefault(flow.source, []).append(flow.iri)
            incoming.setdefault(flow.target, []).append(flow.iri)
        for node in layout.nodes.values():
            el = ET.SubElement(
                parent,
                f"{{{_BPMN}}}{node.tag}",
                {"id": self._id(node.iri), "name": node.label},
            )
            if node.doc:
                ET.SubElement(el, f"{{{_BPMN}}}documentation").text = node.doc
            # <incoming>/<outgoing> are optional in the schema, but modeling
            # tools expect them when re-opening a file for editing
            for flow_iri in incoming.get(node.iri, []):
                ET.SubElement(el, f"{{{_BPMN}}}incoming").text = self._id(flow_iri)
            for flow_iri in outgoing.get(node.iri, []):
                ET.SubElement(el, f"{{{_BPMN}}}outgoing").text = self._id(flow_iri)
            if node.children is not None:
                self._emit_semantic(el, node.children)
        for flow in layout.flows:
            attrs = {
                "id": self._id(flow.iri),
                "sourceRef": self._id(flow.source),
                "targetRef": self._id(flow.target),
            }
            if flow.name:
                attrs["name"] = flow.name
            el = ET.SubElement(parent, f"{{{_BPMN}}}sequenceFlow", attrs)
            if flow.condition_text:
                cond = ET.SubElement(
                    el,
                    f"{{{_BPMN}}}conditionExpression",
                    {f"{{{_XSI}}}type": "tFormalExpression"},
                )
                cond.text = flow.condition_text

    def _emit_di(self, plane: ET.Element, layout: _Layout) -> None:
        """Shapes and edges of one container, flattened onto the single plane
        (BPMN DI nests nothing - subprocess children are plane-level shapes
        with absolute coordinates)."""
        for node in layout.nodes.values():
            attrs = {
                "id": f"{self._id(node.iri)}_di",
                "bpmnElement": self._id(node.iri),
            }
            if node.tag == "subProcess":
                attrs["isExpanded"] = "true"
            shape = ET.SubElement(plane, f"{{{_BPMNDI}}}BPMNShape", attrs)
            ET.SubElement(
                shape,
                f"{{{_DC}}}Bounds",
                {
                    "x": f"{node.x:g}",
                    "y": f"{node.y:g}",
                    "width": f"{node.width:g}",
                    "height": f"{node.height:g}",
                },
            )
            if node.children is not None:
                self._emit_di(plane, node.children)
        for flow in layout.flows:
            edge = ET.SubElement(
                plane,
                f"{{{_BPMNDI}}}BPMNEdge",
                {
                    "id": f"{self._id(flow.iri)}_di",
                    "bpmnElement": self._id(flow.iri),
                },
            )
            for wx, wy in flow.waypoints:
                ET.SubElement(
                    edge,
                    f"{{{_DI}}}waypoint",
                    {"x": f"{wx:g}", "y": f"{wy:g}"},
                )
