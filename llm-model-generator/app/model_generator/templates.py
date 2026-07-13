"""Deterministic SHACL-IR -> OntoUI model builder (the rule core).

Builds the BBO control flow + OBOP UI layer + embedded validation SHACL as an
rdflib graph, mirroring the hand-built restaurant pattern:

  * one self-contained subprocess per entity:
      start -> generate_form -> user_enters -> processing -> gateway
        --submit--> save -> confirmation -> notification -> subprocess EndEvent
        --cancel--> abort -> cancel EndEvent
  * subprocesses chained in the main process, then ONE final SHACL validation:
      start -> insert_E1 -> ... -> insert_En -> final_validation
            -> user_receives_validation -> end_event
  * a shared "Continue" action/button on every notification screen
  * per relationship (RelationSpec) an obop:Connection + Connectors, executed by
    a MakeConnectionAction ScriptTask spliced after the save task of the later
    of the two entities' subprocesses (save -> make_connection -> confirmation).

No LLM here — this is the reproducible structure. Output is plain triples, so
there are no string-template / whitespace pitfalls.
"""

from __future__ import annotations

from rdflib import RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, XSD

from .ir import EntitySpec

OBOP = Namespace("http://purl.org/net/obop/")
BBO = Namespace("https://www.irit.fr/recherches/MELODI/ontologies/BBO#")
SH = Namespace("http://www.w3.org/ns/shacl#")
DASH = Namespace("http://datashapes.org/dash#")

DEFAULT_BASE = "http://example.org/generated/"


class ModelBuilder:
    """Accumulates the generated model triples in a single rdflib graph."""

    def __init__(self, base: str = DEFAULT_BASE):
        self.base = base if base.endswith(("/", "#")) else base + "/"
        self.ex = Namespace(self.base)
        self.g = Graph()
        for prefix, ns in (
            ("", self.ex), ("obop", OBOP), ("bbo", BBO), ("sh", SH),
            ("shacl", SH), ("dash", DASH), ("owl", OWL), ("xsd", XSD),
            ("rdfs", RDFS),
        ):
            self.g.bind(prefix, ns)
        # the single shared "continue past a notification" action
        self.continue_action = self.ex["continue_action"]
        self.main_process = self.ex["app_process"]
        # connection ScriptTasks to splice into a subprocess's save->confirmation
        # chain, keyed by the iri_token of the subprocess they run in
        # (filled by plan_connections before entities are built)
        self._pending_connections: dict[str, list] = {}

    # -- low-level helpers ----------------------------------------------------

    def ind(self, local: str, *types: URIRef) -> URIRef:
        """Mint/declare a named individual with the given rdf:types."""
        uri = self.ex[local]
        self.g.add((uri, RDF.type, OWL.NamedIndividual))
        for t in types:
            self.g.add((uri, RDF.type, t))
        return uri

    def lit(self, s: URIRef, p: URIRef, value, datatype=None) -> None:
        self.g.add((s, p, Literal(value, datatype=datatype)))

    def link(self, s: URIRef, p: URIRef, o) -> None:
        self.g.add((s, p, o if isinstance(o, (URIRef, BNode)) else URIRef(o)))

    def flow(self, local: str, container: URIRef, src: URIRef, tgt: URIRef,
             condition: URIRef | None = None) -> None:
        cls = BBO.ConditionalSequenceFlow if condition else BBO.NormalSequenceFlow
        f = self.ind(local, cls)
        self.link(f, BBO.has_container, container)
        self.link(f, BBO.has_sourceRef, src)
        self.link(f, BBO.has_targetRef, tgt)
        if condition:
            self.link(f, BBO.has_conditionExpression, condition)

    def position(self, s: URIRef, n: int) -> None:
        self.lit(s, OBOP.hasPositionNumber, n, XSD.int)

    # -- shared / main-process scaffolding ------------------------------------

    def build_shared(self) -> None:
        self.ind("app_model", OBOP.Model)
        self.ind(self.main_process.split("/")[-1].split("#")[-1] or "app_process",
                 BBO.Process)
        # continue action shared by all notification screens
        c = self.ind("continue_action", OBOP.Action)
        self.lit(c, OBOP.hasInitiator, "onClick")
        self.lit(c, OBOP.hasLabel, "Continue")
        self.g.add((c, RDFS.comment, Literal(
            "Advance the workflow from a notification screen to the next step.")))

    # -- relationships (obop:Connection) ---------------------------------------

    def plan_connections(self, entities: list[EntitySpec]) -> None:
        """Group each entity's relationships by target and decide placement.

        One obop:Connection per (source, target) entity pair, with one
        obop:Connector per relationship property — mirroring the hand-built
        restaurant model, where restaurant->menu is a single Connection with
        gr:offers and schema:hasMenu connectors. The MakeConnectionAction
        ScriptTask is spliced into the save->confirmation flow of whichever
        subprocess of the pair runs LATER, so both instances exist when it
        fires — correct for any relationship structure, cycles included.
        """
        index = {ent.iri_token: i for i, ent in enumerate(entities)}
        for ent in entities:
            by_target: dict[str, list] = {}
            for rel in ent.relationships:
                by_target.setdefault(rel.target_iri_token, []).append(rel)
            for target_token, rels in sorted(by_target.items()):
                if index[ent.iri_token] >= index[target_token]:
                    later = ent.iri_token
                else:
                    later = target_token
                self._pending_connections.setdefault(later, []).append(
                    (ent.iri_token, target_token, rels)
                )

    def _build_connection(self, sub: URIRef, src: str, tgt: str, rels) -> URIRef:
        """Emit one Connection + its Connectors + MakeConnectionAction + ScriptTask.

        Returns the ScriptTask so the caller can chain it into the subprocess's
        sequence flows.
        """
        conn = self.ind(f"{src}_{tgt}_connection", OBOP.Connection)
        self.link(conn, OBOP.connectionHasSource, self.ex[f"{src}_shape"])
        self.link(conn, OBOP.connectionHasTarget, self.ex[f"{tgt}_shape"])
        for rel in rels:
            connector = self.ind(
                f"connector_{src}_{tgt}_{rel.iri_token}", OBOP.Connector
            )
            self.g.add((connector, SH.path, URIRef(rel.path)))
            self.link(conn, OBOP.hasConnector, connector)
        action = self.ind(f"connection_action_{src}_{tgt}", OBOP.MakeConnectionAction)
        self.link(action, OBOP.hasConnection, conn)
        task = self.ind(f"make_connection_{src}_{tgt}", BBO.ScriptTask)
        self.link(task, BBO.has_container, sub)
        self.link(task, OBOP.executesAction, action)
        self.g.add((task, RDFS.comment, Literal(
            f"Save the object properties linking the {src} instance "
            f"to the {tgt} instance.")))
        return task

    def build_main_process(self, entities: list[EntitySpec]) -> None:
        mp = self.main_process
        start = self.ind("start", BBO.ProcessStartEvent)
        self.link(start, BBO.has_container, mp)
        end = self.ind("end_event", BBO.EndEvent)
        self.g.add((end, RDFS.comment, Literal(
            "The data insertion process is completed.")))
        self.link(end, BBO.has_container, mp)

        # final single SHACL validation over the whole knowledge graph
        fv = self.ind("final_validation", BBO.ScriptTask)
        self.link(fv, BBO.has_container, mp)
        self.link(fv, OBOP.executesAction, self.ex["final_validation_action"])
        self.g.add((fv, RDFS.comment, Literal(
            "Validate the whole stored knowledge graph using SHACL shapes.")))
        fva = self.ind("final_validation_action", OBOP.SHACLValidation)
        self.lit(fva, OBOP.hasInitiator, "onClick")
        self.lit(fva, OBOP.hasInitiator, "onEnter")
        urv = self.ind("user_receives_validation", BBO.UserTask)
        self.link(urv, BBO.has_container, mp)
        self.g.add((urv, RDFS.comment, Literal("User receives the validation results.")))

        # chain: start -> insert_E1 -> ... -> insert_En -> final_validation
        prev = start
        for i, ent in enumerate(entities):
            sub = self.ex[f"insert_{ent.iri_token}"]
            self.flow(f"flow_main_{i}", mp, prev, sub)
            prev = sub
        self.flow("flow_main_final", mp, prev, fv)
        self.flow("flow_main_urv", mp, fv, urv)
        self.flow("flow_main_end", mp, urv, end)

    # -- per-entity subprocess ------------------------------------------------

    def build_entity(self, ent: EntitySpec) -> None:
        n = ent.iri_token
        sub = self.ind(f"insert_{n}", BBO.SubProcess)
        self.link(sub, BBO.has_container, self.main_process)
        self.g.add((sub, RDFS.comment, Literal(f"Insert {ent.label} data.")))

        # --- BBO control-flow nodes ---
        nodes = {
            "start": self.ind(f"start_{n}", BBO.SubProcessStartEvent),
            "gen": self.ind(f"generate_form_{n}", BBO.ScriptTask),
            "user": self.ind(f"user_enters_{n}", BBO.UserTask),
            "proc": self.ind(f"processing_{n}", BBO.ScriptTask),
            "gw": self.ind(f"gateway_{n}", BBO.ExclusiveGateway),
            "save": self.ind(f"save_{n}", BBO.ScriptTask),
            "abort": self.ind(f"abort_{n}", BBO.ScriptTask),
            "confirm": self.ind(f"confirmation_{n}", BBO.ScriptTask),
            "notif_task": self.ind(f"user_gets_notification_{n}", BBO.UserTask),
            "end": self.ind(f"end_{n}", BBO.EndEvent),
            "cancel_end": self.ind(f"cancel_end_{n}", BBO.EndEvent),
        }
        for node in nodes.values():
            self.link(node, BBO.has_container, sub)
        self.g.add((nodes["end"], RDFS.comment, Literal(f"{ent.label} data stored.")))
        self.g.add((nodes["cancel_end"], RDFS.comment,
                    Literal(f"{ent.label} data entry cancelled.")))

        # --- OBOP block + shape + fields + buttons + actions ---
        block = self.ind(f"{n}_block", OBOP.Block)
        self.lit(block, RDFS.label, f"{ent.label} data", RDF.PlainLiteral)
        self.position(block, 0)
        self.link(block, OBOP.targetClass, URIRef(ent.class_uri))

        vlayout = self.ind(f"{n}_vlayout", OBOP.VerticalLayout)
        self.link(vlayout, OBOP.belongsTo, block)
        self.position(vlayout, 0)
        hlayout = self.ind(f"{n}_hlayout", OBOP.HorizontalLayout)
        self.link(hlayout, OBOP.belongsToVisual, vlayout)
        self.position(hlayout, 4)

        shape = self.ind(f"{n}_shape", SH.NodeShape)
        self.link(shape, OBOP.modelBelongsTo, block)
        self.link(shape, SH.targetClass, URIRef(ent.class_uri))

        gen_action = self.ind(f"gen_action_{n}", OBOP.GenerateJSONForm)
        self.link(gen_action, OBOP.actionInBlock, block)
        self.link(nodes["gen"], OBOP.executesAction, gen_action)

        for i, prop in enumerate(ent.properties):
            field = self.ind(f"field_{n}_{prop.iri_token}", OBOP.Field)
            self.link(field, OBOP.belongsTo, block)
            self.link(field, OBOP.belongsToVisual, vlayout)
            self.link(field, OBOP.containsDatatype, URIRef(prop.path))
            self.link(field, OBOP.isRelatedToTargetOntologyInstance, shape)
            self.lit(field, OBOP.hasLabel, prop.label)
            self.position(field, i)
            # property shape (bnode) linked to the field via obop:specifedBy
            ps = BNode()
            self.g.add((shape, SH.property, ps))
            self.g.add((ps, SH.path, URIRef(prop.path)))
            if prop.datatype:
                self.g.add((ps, SH.datatype, URIRef(prop.datatype)))
            self.g.add((ps, SH.maxCount, Literal(1)))
            self.g.add((ps, SH.name, Literal(prop.label)))
            self.g.add((ps, SH.order, Literal(prop.order)))
            self.g.add((ps, DASH.singleLine, Literal(True)))
            self.link(ps, OBOP.specifedBy, field)

        # Relationship property shapes: declare, in the shape itself, that this
        # entity is related to its target entity via the object property, each
        # value conforming to the target's shape. Validation-only — no
        # obop:specifedBy, so the engine renders no form field for them.
        for rel in ent.relationships:
            ps = BNode()
            self.g.add((shape, SH.property, ps))
            self.g.add((ps, SH.path, URIRef(rel.path)))
            self.g.add((ps, SH.node, self.ex[f"{rel.target_iri_token}_shape"]))

        submit_action = self.ind(f"submit_action_{n}", OBOP.SubmitBlockAction)
        self.link(submit_action, OBOP.actionInBlock, block)
        self.lit(submit_action, OBOP.hasInitiator, "onClick")
        self.lit(submit_action, OBOP.hasInitiator, "onEnter")
        self.lit(submit_action, OBOP.hasLabel, "Submit")
        self.link(nodes["save"], OBOP.executesAction, submit_action)

        cancel_action = self.ind(f"cancel_action_{n}", OBOP.CancelBlockAction)
        self.link(cancel_action, OBOP.actionInBlock, block)
        self.lit(cancel_action, OBOP.hasInitiator, "onClick")
        self.lit(cancel_action, OBOP.hasLabel, "Cancel")
        self.link(nodes["abort"], OBOP.executesAction, cancel_action)

        submit_btn = self.ind(f"submit_btn_{n}", OBOP.Button)
        self.link(submit_btn, OBOP.activatesAction, submit_action)
        self.link(submit_btn, OBOP.belongsTo, block)
        self.link(submit_btn, OBOP.belongsToVisual, hlayout)
        self.lit(submit_btn, OBOP.hasLabel, "Submit")
        self.position(submit_btn, 0)

        cancel_btn = self.ind(f"cancel_btn_{n}", OBOP.Button)
        self.link(cancel_btn, OBOP.activatesAction, cancel_action)
        self.link(cancel_btn, OBOP.belongsTo, block)
        self.link(cancel_btn, OBOP.belongsToVisual, hlayout)
        self.lit(cancel_btn, OBOP.hasLabel, "Cancel")
        self.position(cancel_btn, 1)

        # --- notification block + Continue button ---
        notif_block = self.ind(f"{n}_notification_block", OBOP.Block)
        self.lit(notif_block, RDFS.label, f"{ent.label} saved - Notification",
                 RDF.PlainLiteral)
        self.position(notif_block, 0)
        notif_layout = self.ind(f"{n}_notification_layout", OBOP.VerticalLayout)
        self.link(notif_layout, OBOP.belongsTo, notif_block)
        self.position(notif_layout, 0)
        notif_label = self.ind(f"{n}_notification_label", OBOP.Label)
        self.link(notif_label, OBOP.belongsTo, notif_block)
        self.link(notif_label, OBOP.belongsToVisual, notif_layout)
        self.position(notif_label, 0)
        self.lit(notif_label, OBOP.hasText,
                 f"The {ent.label} data have been stored in the database.",
                 RDF.PlainLiteral)
        continue_btn = self.ind(f"continue_btn_{n}", OBOP.Button)
        self.link(continue_btn, OBOP.activatesAction, self.continue_action)
        self.link(continue_btn, OBOP.belongsTo, notif_block)
        self.link(continue_btn, OBOP.belongsToVisual, notif_layout)
        self.lit(continue_btn, OBOP.hasLabel, "Continue")
        self.position(continue_btn, 1)
        confirm_action = self.ind(f"confirm_action_{n}", OBOP.GenerateJSONForm)
        self.link(confirm_action, OBOP.actionInBlock, notif_block)
        self.link(nodes["confirm"], OBOP.executesAction, confirm_action)

        # --- condition expressions (gateway routing) ---
        submit_cond = self.ind(f"submit_cond_{n}", BBO.ConditionExpression)
        self.link(submit_cond, OBOP.selectedAction, submit_action)
        cancel_cond = self.ind(f"cancel_cond_{n}", BBO.ConditionExpression)
        self.link(cancel_cond, OBOP.selectedAction, cancel_action)

        # --- sequence flows (all inside this subprocess) ---
        self.flow(f"flow_{n}_1", sub, nodes["start"], nodes["gen"])
        self.flow(f"flow_{n}_2", sub, nodes["gen"], nodes["user"])
        self.flow(f"flow_{n}_3", sub, nodes["user"], nodes["proc"])
        self.flow(f"flow_{n}_4", sub, nodes["proc"], nodes["gw"])
        self.flow(f"flow_{n}_submit", sub, nodes["gw"], nodes["save"], submit_cond)
        self.flow(f"flow_{n}_cancel", sub, nodes["gw"], nodes["abort"], cancel_cond)
        # save -> [make_connection tasks planned for this subprocess] -> confirm.
        # Consecutive ScriptTasks run back-to-back, so the connection triples are
        # created in the same submit step (BBO tasks cannot nest).
        prev = nodes["save"]
        for k, (src, tgt, rels) in enumerate(self._pending_connections.get(n, [])):
            task = self._build_connection(sub, src, tgt, rels)
            self.flow(f"flow_{n}_5_conn_{k}", sub, prev, task)
            prev = task
        self.flow(f"flow_{n}_5", sub, prev, nodes["confirm"])
        self.flow(f"flow_{n}_6", sub, nodes["confirm"], nodes["notif_task"])
        self.flow(f"flow_{n}_7", sub, nodes["notif_task"], nodes["end"])
        self.flow(f"flow_{n}_abort_end", sub, nodes["abort"], nodes["cancel_end"])


def build_model_graph(entities: list[EntitySpec], base: str = DEFAULT_BASE) -> Graph:
    """Assemble the full model graph from the entity specs."""
    b = ModelBuilder(base)
    b.plan_connections(entities)  # placement must be known before entities build
    b.build_shared()
    for ent in entities:
        b.build_entity(ent)
    b.build_main_process(entities)
    return b.g
