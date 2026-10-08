#!/usr/bin/env python3
"""Hand-made positive and adversarial controls, run through the actual CLI.

This file neither imports the checker nor reads certificates from data/. The
fixtures below are explicit small graphs and algebraic identities. Only tests
of declared size limits expand those fixtures into large lists or trees.
"""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
BOUND = 1 << 62
KINDS = ("unknown", "rhombus_refuted", "rhombus_tu", "tri_refuted", "tri_tu")


def encode(n, edges):
    """Fixture encoder: put edges at their triangular-number bit positions."""
    bits = ["0"] * (n * (n - 1) // 2)
    for a, b in edges:
        a, b = sorted((a, b))
        assert 0 <= a < b < n
        bits[b * (b - 1) // 2 + a] = "1"
    bits = "".join(bits)
    bits += "0" * (-len(bits) % 6)
    payload = "".join(chr(63 + int(bits[i:i + 6], 2)) for i in range(0, len(bits), 6))
    if n <= 62:
        prefix = chr(63 + n)
    else:
        assert n <= 258047
        prefix = "~" + "".join(chr(63 + ((n >> shift) & 63)) for shift in (12, 6, 0))
    return prefix + payload


def complete(n):
    return [(a, b) for a in range(n) for b in range(a + 1, n)]


K23_EDGES = [(a, b) for a in (0, 1) for b in (2, 3, 4)]
K23_CYCLES = [[0, 2, 1, 3], [0, 2, 1, 4]]
GADGET_EDGES = [(2, 3), (3, 0), (0, 1), (1, 2),
                (4, 5), (5, 0), (1, 4), (3, 5)]
GADGET_CYCLES = [[2, 3, 0, 1], [4, 5, 0, 1]]

# Known strings anchor order, column order, bit significance, and padding.
assert encode(0, []) == "?"
assert encode(2, [(0, 1)]) == "A_"
assert encode(3, complete(3)) == "Bw"
assert encode(4, complete(4)) == "C~"
assert encode(5, K23_EDGES) == "D]o"


def rhombus(n, edges, cycles, coefficients, scale, pair, edge=None):
    body = dict(cycles=cycles, coefficients=coefficients, scale=scale, pair=pair)
    if edge is not None:
        body["edge"] = edge
    return dict(g6=encode(n, edges), verdict="tu" if edge is not None else "refuted",
                witness={"rhombus": body})


def leaf(cycles, cycle_coefficients, triangles, triangle_coefficients,
         scale, pair, edge=None, zeta=None):
    body = dict(cycles=cycles, cycle_coefficients=cycle_coefficients,
                triangles=triangles, triangle_coefficients=triangle_coefficients,
                scale=scale, pair=pair)
    if edge is not None:
        body.update(edge=edge, zeta=zeta)
    return {"leaf": body}


def split(triangle, plus, minus):
    return dict(split=triangle, plus=plus, minus=minus)


def tri(n, edges, tree, verdict="refuted"):
    return dict(g6=encode(n, edges), verdict=verdict, witness={"tri": {"tree": tree}})


def lift(record):
    """Express a hand-made rhombus identity as a root triangle-tree leaf."""
    r = record["witness"]["rhombus"]
    tree = leaf(r["cycles"], [[c, 0] for c in r["coefficients"]], [], [],
                [r["scale"], 0], r["pair"], r.get("edge"), 0 if "edge" in r else None)
    return dict(g6=record["g6"], verdict=record["verdict"], witness={"tri": {"tree": tree}})


def equal_triangle_leaf(swapped=False):
    # When both orientations agree, t(012) - t(013) = e_2 - e_3.
    return leaf([], [], [[0, 1, 2], [1, 0, 3] if swapped else [0, 1, 3]],
                [[1, 0], [-1, 0]], [1, 0], [2, 3])


def opposite_triangle_leaf(rotation, scale):
    # With r for 012, t for 013 and u for 023:
    # u*t(012) - t(013) + t(023) = (u*r - t)*(e_0 - e_1).
    return leaf([], [], [[0, 1, 2], [0, 1, 3], [0, 2, 3]],
                [rotation, [-1, 0], [1, 0]], scale, [0, 1])


def k4_triangle_tree(wrong_ring=False):
    # These four scales are hand-expanded using w^2 = w - 1.
    scales = [[-2, 2], [0, 1], [1, -1], [0, -2]]
    if wrong_ring:
        # Hand-expanded under the WRONG relation w^2 = -w - 1 instead.
        scales = [[-2, 0], [0, 3], [1, 1], [0, -4]]
    return split([0, 1, 2],
                 split([0, 1, 3], equal_triangle_leaf(),
                       split([0, 2, 3],
                             opposite_triangle_leaf([0, 1], scales[0]),
                             opposite_triangle_leaf([1, -1], scales[1]))),
                 split([0, 1, 3],
                       split([0, 2, 3],
                             opposite_triangle_leaf([0, 1], scales[2]),
                             opposite_triangle_leaf([1, -1], scales[3])),
                       equal_triangle_leaf()))


def rotated_gadget(reverse_edge=False):
    # R = e_2 - e_4 - e_3 + e_5. For T=(3,5,6), r=w^s:
    # R + r^-1*t(T,s) = e_2 - e_4 - r^-1*(e_3 - e_6).
    edge = [6, 3] if reverse_edge else [3, 6]
    plus_k, minus_k = (2, 4) if reverse_edge else (5, 1)
    plus = leaf(GADGET_CYCLES, [[1, 0], [-1, 0]], [[3, 5, 6]],
                [[1, -1]], [1, 0], [2, 4], edge, plus_k)
    minus = leaf(GADGET_CYCLES, [[1, 0], [-1, 0]], [[3, 5, 6]],
                 [[0, 1]], [1, 0], [2, 4], edge, minus_k)
    return tri(7, GADGET_EDGES + [(3, 6), (5, 6)],
               split([3, 5, 6], plus, minus), "tu")


R = rhombus(5, K23_EDGES, K23_CYCLES, [1, -1], 1, [4, 3])
RK4 = rhombus(4, complete(4), [[0, 1, 2, 3], [0, 2, 1, 3]],
              [1, -1], 2, [2, 1])
U = rhombus(6, GADGET_EDGES, GADGET_CYCLES, [1, -1], 1, [2, 4], [3, 5])
TC = lift(R)
TU = lift(U)
KT = tri(4, complete(4), k4_triangle_tree())
ROT = rotated_gadget()
UNKNOWN = {"g6": "?", "verdict": "unknown"}
RP = ("witness", "rhombus")
TP = ("witness", "tri", "tree")
LP = TP + ("leaf",)
KP = TP + ("plus", "plus", "leaf")
OP = TP + ("plus", "minus", "plus", "leaf")
ROT_PLUS = TP + ("plus", "leaf")


def changed(record, path, value):
    result = copy.deepcopy(record)
    current = result
    for step in path[:-1]:
        current = current[step]
    current[path[-1]] = value
    return result


def removed(record, path):
    result = copy.deepcopy(record)
    current = result
    for step in path[:-1]:
        current = current[step]
    del current[path[-1]]
    return result


def dumps(obj):
    return json.dumps(obj, separators=(",", ":"))


def control(name, payload, reason=None, kinds=None, line=1):
    return (name, payload, reason, kinds, line)


def positive(name, record, kind):
    return control(name, record, kinds=[kind])


def mutant(name, record, path, value, reason):
    return control(name, changed(record, path, value), reason)


def chain_record(depth):
    edges = list(K23_EDGES)
    triangles = []
    for index in range(depth):
        a = 5 + 3 * index
        triangles.append([a, a + 1, a + 2])
        edges.extend([(a, a + 1), (a, a + 2), (a + 1, a + 2)])
    base = TC["witness"]["tri"]["tree"]
    tree = base
    for triangle in reversed(triangles):
        tree = split(triangle, tree, base)
    return tri(5 + 3 * depth, edges, tree)


def node_budget_record(leaves):
    # A full binary tree with L leaves has 2*L-1 nodes. There is a fresh
    # triangle for each depth; reuse on separate branches is permitted.
    edges = list(K23_EDGES)
    triangles = []
    for index in range(16):
        a = 5 + 3 * index
        triangles.append([a, a + 1, a + 2])
        edges.extend([(a, a + 1), (a, a + 2), (a + 1, a + 2)])
    base = TC["witness"]["tri"]["tree"]

    def build(count, depth=0):
        if count == 1:
            return base
        left = count // 2
        return split(triangles[depth], build(left, depth + 1), build(count - left, depth + 1))

    return tri(53, edges, build(leaves))


def cases():
    yield positive("unknown empty graph", UNKNOWN, "unknown")
    yield positive("unknown K3", {"g6": "Bw", "verdict": "unknown"}, "unknown")
    yield positive("K2,3 collision from two rows", R, "rhombus_refuted")
    yield positive("K4 collision, scale two", RK4, "rhombus_refuted")
    yield positive("embeddable forced-distance gadget", U, "rhombus_tu")
    yield positive("root tri leaf with cycles only", TC, "tri_refuted")
    yield positive("root tri unit leaf, zeta zero", TU, "tri_tu")
    yield positive("K4 triangles only, both orientations", KT, "tri_refuted")
    yield positive("rotated unit leaves, zeta five and one", ROT, "tri_tu")
    yield positive("rotated unit leaves, zeta two and four", rotated_gadget(True), "tri_tu")
    z3 = changed(changed(TU, LP + ("edge",), [5, 3]), LP + ("zeta",), 3)
    yield positive("root unit leaf, zeta three", z3, "tri_tu")
    neg = changed(changed(R, RP + ("coefficients",), [-1, 1]), RP + ("scale",), -1)
    yield positive("negative rhombus scale", neg, "rhombus_refuted")
    max_coeff = changed(changed(R, RP + ("coefficients",), [BOUND - 1, 1 - BOUND]),
                        RP + ("scale",), BOUND - 1)
    yield positive("largest permitted integer components", max_coeff, "rhombus_refuted")
    complex_leaf = changed(changed(TC, LP + ("cycle_coefficients",), [[2, -3], [-2, 3]]),
                           LP + ("scale",), [2, -3])
    yield positive("nonreal nonunit complex scale", complex_leaf, "tri_refuted")
    imaginary_leaf = changed(changed(TC, LP + ("cycle_coefficients",), [[0, 1], [0, -1]]),
                             LP + ("scale",), [0, 1])
    yield positive("scale with only a w component", imaginary_leaf, "tri_refuted")

    # A shared target vertex cancels. The K2,3 rows still equal e_4-e_3.
    cancel_a = rhombus(6, K23_EDGES + [(5, 4)], K23_CYCLES, [1, -1],
                       1, [5, 3], [5, 4])
    cancel_b = rhombus(6, K23_EDGES + [(5, 4)], K23_CYCLES, [-1, 1],
                       1, [3, 5], [4, 5])
    double_b = rhombus(5, K23_EDGES + [(3, 4)],
                       K23_CYCLES + [[0, 3, 1, 4]], [1, -2, 1], 1, [2, 3], [3, 4])
    double_a = rhombus(5, K23_EDGES + [(3, 4)],
                       K23_CYCLES + [[0, 3, 1, 4]], [-1, 2, -1], 1, [3, 2], [4, 3])
    for name, record in (("a equals p cancellation", cancel_a),
                         ("b equals q cancellation", cancel_b),
                         ("b equals p doubling", double_b),
                         ("a equals q doubling", double_a)):
        yield positive("rhombus " + name, record, "rhombus_tu")
        yield positive("tri " + name, lift(record), "tri_tu")

    mixed = tri(9, K23_EDGES + [(5, 4), (6, 7), (6, 8), (7, 8)],
                split([6, 7, 8], lift(cancel_a)["witness"]["tri"]["tree"],
                      TC["witness"]["tri"]["tree"]), "tu")
    yield positive("mixed unit and collision leaves mean tu", mixed, "tri_tu")
    siblings = tri(4, complete(4), split([0, 1, 2],
                   split([0, 1, 3], lift(RK4)["witness"]["tri"]["tree"],
                         lift(RK4)["witness"]["tri"]["tree"]),
                   split([0, 1, 3], lift(RK4)["witness"]["tri"]["tree"],
                         lift(RK4)["witness"]["tri"]["tree"])))
    yield positive("same split on separate branches is legal", siblings, "tri_refuted")
    repeated_triangles = changed(KT, KP + ("triangles",),
                                 [[0, 1, 2], [0, 1, 3], [0, 1, 2], [0, 1, 2]])
    repeated_triangles = changed(repeated_triangles, KP + ("triangle_coefficients",),
                                 [[1, 0], [-1, 0], [2, -1], [-2, 1]])
    yield positive("duplicate leaf rows are allowed", repeated_triangles, "tri_refuted")
    for n in (62, 63):
        yield positive("graph6 order " + str(n), changed(R, ("g6",), encode(n, K23_EDGES)),
                       "rhombus_refuted")
    yield positive("standard optional graph6 header", changed(R, ("g6",), ">>graph6<<" + R["g6"]),
                   "rhombus_refuted")
    yield control("six-record file and exact counters", "\n".join(map(dumps, (UNKNOWN, R, U, TC, TU, KT))) + "\n",
                  kinds=["unknown", "rhombus_refuted", "rhombus_tu", "tri_refuted", "tri_tu", "tri_refuted"])
    yield control("empty file", "", kinds=[])
    yield control("CRLF and final line without newline", dumps(UNKNOWN) + "\r\n" + dumps(R),
                  kinds=["unknown", "rhombus_refuted"])

    # JSON and exact object schemas, including duplicate keys at nested levels.
    yield control("malformed JSON", "{", "invalid JSON")
    yield control("blank record", "\n", "invalid JSON")
    yield control("invalid UTF-8", b'\xff\n', "not valid UTF-8")
    yield control("nonobject record", "[]", "record must be an object")
    yield control("duplicate top key", '{"g6":"?","g6":"?","verdict":"unknown"}', "duplicate JSON key")
    yield control("duplicate escaped key", '{"g6":"?","g\\u0036":"?","verdict":"unknown"}', "duplicate JSON key")
    yield control("duplicate rhombus key", dumps(R).replace('"scale":1', '"scale":1,"scale":1'), "duplicate JSON key")
    yield control("duplicate leaf key", dumps(TC).replace('"scale":[1,0]', '"scale":[1,0],"scale":[1,0]'), "duplicate JSON key")
    yield control("duplicate split key", dumps(KT).replace('"split":[0,1,2]', '"split":[0,1,2],"split":[0,1,2]'), "duplicate JSON key")
    yield control("NaN numeric extension", dumps(R).replace('"scale":1', '"scale":NaN'), "non-JSON numeric constant")
    yield control("Infinity numeric extension", dumps(R).replace('"scale":1', '"scale":Infinity'), "non-JSON numeric constant")
    yield control("5000-digit integer is parsed then bounded", dumps(R).replace('"scale":1', '"scale":' + '9' * 5000),
                  "absolute value below 2^62")
    yield mutant("unknown may not carry a witness", UNKNOWN, ("witness",), {}, "record must have exactly keys")
    yield mutant("extra top key", R, ("extra",), 0, "record must have exactly keys")
    yield control("missing g6", removed(R, ("g6",)), "record must have exactly keys")
    yield control("missing verdict", removed(R, ("verdict",)), "verdict must be")
    yield control("missing witness", removed(R, ("witness",)), "record must have exactly keys")
    yield mutant("unsupported verdict", R, ("verdict",), "embedded", "verdict must be")
    yield mutant("nonstring verdict", R, ("verdict",), True, "verdict must be")
    yield mutant("witness is not an object", R, ("witness",), [], "witness must have exactly")
    yield mutant("two witness alternatives", R, ("witness",), {"rhombus": R["witness"]["rhombus"], "tri": {}},
                  "witness must have exactly")
    yield mutant("unsupported witness", R, ("witness",), {"other": {}}, "witness must have exactly")
    yield mutant("rhombus extra key", R, RP + ("extra",), 0, "rhombus must have exactly keys")
    yield mutant("rhombus object required", R, RP, [], "rhombus must be an object")
    yield control("rhombus missing coefficients", removed(R, RP + ("coefficients",)), "rhombus must have exactly keys")
    yield mutant("refuted rhombus cannot have edge", R, RP + ("edge",), [0, 2], "rhombus must have exactly keys")
    yield control("tu rhombus requires edge", removed(U, RP + ("edge",)), "rhombus must have exactly keys")

    for name, value, reason in (
            ("nonstring", 5, "g6 must be a string"),
            ("empty", "", "g6 is empty"),
            ("bad character", "A!", "outside ASCII"),
            ("nonascii", "A\u00e9", "outside ASCII"),
            ("embedded newline", "A_\n", "outside ASCII"),
            ("truncated payload", "D]", "payload length"),
            ("extra payload", "D]o?", "payload length"),
            ("nonzero padding", "A`", "padding bits"),
            ("truncated order18", "~?", "truncated 18-bit"),
            ("truncated order36", "~~???", "truncated 36-bit"),
            ("nonminimal order18", "~??@", "not minimal"),
            ("nonminimal order36", "~~?????~", "not minimal"),
            ("huge order tiny payload", "~~~~~~~~", "payload length")):
        yield mutant("graph6 " + name, UNKNOWN, ("g6",), value, reason)

    for name, path, value, reason in (
            ("empty cycle list", ("cycles",), [], "nonempty list"),
            ("cycle list type", ("cycles",), {}, "nonempty list"),
            ("too many cycles", ("cycles",), [K23_CYCLES[0]] * 4097, "at most 4096"),
            ("cycle has three vertices", ("cycles", 0), [0, 2, 1], "list of 4"),
            ("repeated cycle vertex", ("cycles", 0), [0, 2, 0, 3], "vertices must be distinct"),
            ("missing cycle edge", ("cycles", 0), [0, 1, 2, 3], "missing cycle edge"),
            ("boolean cycle vertex", ("cycles", 0, 0), False, "JSON integer"),
            ("float cycle vertex", ("cycles", 0, 0), 0.0, "JSON integer"),
            ("negative cycle vertex", ("cycles", 0, 0), -1, "out of range"),
            ("large cycle vertex", ("cycles", 0, 0), 5, "out of range"),
            ("coefficient length", ("coefficients",), [1], "match cycles in length"),
            ("coefficient list type", ("coefficients",), 2, "match cycles in length"),
            ("zero coefficient", ("coefficients", 0), 0, "coefficient must be nonzero"),
            ("boolean coefficient", ("coefficients", 0), True, "JSON integer"),
            ("float coefficient", ("coefficients", 0), 1.0, "JSON integer"),
            ("string coefficient", ("coefficients", 0), "1", "JSON integer"),
            ("coefficient positive bound", ("coefficients", 0), BOUND, "absolute value below"),
            ("coefficient negative bound", ("coefficients", 0), -BOUND, "absolute value below"),
            ("zero scale", ("scale",), 0, "scale must be nonzero"),
            ("boolean scale", ("scale",), True, "JSON integer"),
            ("float scale", ("scale",), 1.0, "JSON integer"),
            ("scale positive bound", ("scale",), BOUND, "absolute value below"),
            ("scale negative bound", ("scale",), -BOUND, "absolute value below"),
            ("pair length", ("pair",), [4], "list of 2"),
            ("pair equal vertices", ("pair",), [4, 4], "vertices must be distinct"),
            ("pair out of range", ("pair",), [5, 3], "out of range"),
            ("pair boolean", ("pair",), [True, 3], "JSON integer"),
            ("wrong identity", ("scale",), 2, "identity fails")):
        yield mutant("rhombus " + name, R, RP + path, value, reason)
    yield mutant("rhombus tu pair is an edge", U, RP + ("pair",), [2, 3], "tu pair must be a non-edge")
    yield mutant("rhombus edge is missing", U, RP + ("edge",), [2, 4], "edge is not an edge")
    yield mutant("rhombus edge equal endpoints", U, RP + ("edge",), [3, 3], "vertices must be distinct")
    yield mutant("rhombus edge out of range", U, RP + ("edge",), [3, 6], "out of range")
    yield mutant("rhombus edge boolean", U, RP + ("edge",), [True, 5], "JSON integer")

    yield mutant("tri exact wrapper keys", TC, ("witness", "tri", "extra"), 0, "tri must have exactly keys")
    yield control("tri missing tree", removed(TC, TP), "tri must have exactly keys")
    yield mutant("tree is not a node", TC, TP, None, "must be a node object")
    yield mutant("node has no alternative", TC, TP, {}, "leaf node must have exactly keys")
    yield mutant("leaf node extra key", TC, TP + ("extra",), 0, "leaf node must have exactly keys")
    yield mutant("leaf object required", TC, LP, None, "must be an object")
    yield mutant("leaf extra key", TC, LP + ("extra",), 0, "must have exactly keys")
    yield control("leaf required empty list missing", removed(TC, LP + ("triangles",)), "must have exactly keys")
    yield control("missing minus child", removed(KT, TP + ("minus",)), "split node must have exactly keys")
    yield control("missing plus child", removed(KT, TP + ("plus",)), "split node must have exactly keys")
    yield mutant("null child", KT, TP + ("minus",), None, "must be a node object")
    yield mutant("array child", KT, TP + ("plus",), [], "must be a node object")
    yield mutant("extra split key", KT, TP + ("extra",), 0, "split node must have exactly keys")
    yield mutant("both node alternatives", KT, TP + ("leaf",), {}, "split node must have exactly keys")
    for name, value, reason in (
            ("unsorted", [1, 0, 2], "sorted triangle"),
            ("repeated vertex", [0, 1, 1], "vertices must be distinct"),
            ("wrong length", [0, 1], "list of 3"),
            ("boolean", [False, 1, 2], "JSON integer"),
            ("out of range", [0, 1, 4], "out of range")):
        yield mutant("split " + name, KT, TP + ("split",), value, reason)
    yield mutant("split missing triangle edge", KT, ("g6",), encode(4, [(0, 1), (0, 2)]), "missing triangle edge")
    yield mutant("repeat triangle on path", KT, TP + ("plus", "split"), [0, 1, 2], "repeats a split triangle")

    for name, path, value, reason in (
            ("both row lists empty", ("cycles",), [], "cannot both be empty"),
            ("cycle list type", ("cycles",), {}, "cycles must be a list"),
            ("triangle list type", ("triangles",), {}, "triangles must be a list"),
            ("too many cycles", ("cycles",), [K23_CYCLES[0]] * 4097, "at most 4096"),
            ("cycle coefficient length", ("cycle_coefficients",), [], "match its rows in length"),
            ("triangle coefficient length", ("triangle_coefficients",), [[1, 0]], "match its rows in length"),
            ("zero cycle coefficient", ("cycle_coefficients", 0), [0, 0], "must be nonzero"),
            ("scalar coefficient", ("cycle_coefficients", 0), 1, "Z[w] pair"),
            ("long coefficient", ("cycle_coefficients", 0), [1, 0, 0], "Z[w] pair"),
            ("boolean coefficient", ("cycle_coefficients", 0), [True, 0], "JSON integer"),
            ("float w coefficient", ("cycle_coefficients", 0), [1, 0.0], "JSON integer"),
            ("positive coefficient bound", ("cycle_coefficients", 0), [BOUND, 0], "absolute value below"),
            ("negative w coefficient bound", ("cycle_coefficients", 0), [1, -BOUND], "absolute value below"),
            ("zero scale", ("scale",), [0, 0], "must be nonzero"),
            ("scalar scale", ("scale",), 1, "Z[w] pair"),
            ("boolean w scale", ("scale",), [1, False], "JSON integer"),
            ("float scale", ("scale",), [1.0, 0], "JSON integer"),
            ("positive w scale bound", ("scale",), [1, BOUND], "absolute value below"),
            ("negative scale bound", ("scale",), [-BOUND, 0], "absolute value below"),
            ("pair equal endpoints", ("pair",), [3, 3], "vertices must be distinct"),
            ("pair negative", ("pair",), [-1, 3], "out of range"),
            ("pair float", ("pair",), [4.0, 3], "JSON integer"),
            ("repeated cycle vertex", ("cycles", 0), [0, 2, 0, 3], "vertices must be distinct"),
            ("missing cycle edge", ("cycles", 0), [0, 1, 2, 3], "missing cycle edge"),
            ("identity wrong", ("scale",), [1, 1], "identity fails")):
        yield mutant("tri leaf " + name, TC, LP + path, value, reason)
    yield mutant("zero triangle coefficient", KT, KP + ("triangle_coefficients", 0), [0, 0], "must be nonzero")
    yield mutant("triangle coefficient length mismatch", KT, KP + ("triangle_coefficients",), [[1, 0]], "match its rows")
    yield mutant("triangle coefficient float", KT, KP + ("triangle_coefficients", 0), [1, 0.0], "JSON integer")
    yield mutant("triangle coefficient bound", KT, KP + ("triangle_coefficients", 0), [0, BOUND], "absolute value below")
    yield mutant("leaf triangle unsorted", KT, KP + ("triangles", 0), [1, 0, 2], "sorted triangle")
    yield mutant("leaf triangle repeated vertex", KT, KP + ("triangles", 0), [0, 1, 1], "vertices must be distinct")
    yield mutant("leaf triangle out of range", KT, KP + ("triangles", 0), [0, 1, 4], "out of range")
    yield mutant("leaf triangle boolean", KT, KP + ("triangles", 0), [False, 1, 2], "JSON integer")
    yield mutant("leaf triangle not on path", KT, KP + ("triangles", 0), [0, 2, 3], "not split on this path")
    yield mutant("sibling split cannot justify a leaf", KT, TP + ("minus",), equal_triangle_leaf(), "not split on this path")
    yield control("edge without zeta", removed(TU, LP + ("zeta",)), "edge and zeta together")
    yield control("zeta without edge", removed(TU, LP + ("edge",)), "edge and zeta together")
    for name, path, value, reason in (
            ("edge equal endpoints", ("edge",), [3, 3], "vertices must be distinct"),
            ("edge missing", ("edge",), [2, 4], "edge is not an edge"),
            ("edge out of range", ("edge",), [3, 6], "out of range"),
            ("edge boolean", ("edge",), [True, 5], "JSON integer"),
            ("pair is an edge", ("pair",), [2, 3], "tu pair must be a non-edge"),
            ("negative zeta", ("zeta",), -1, "zeta must be in 0..5"),
            ("large zeta", ("zeta",), 6, "zeta must be in 0..5"),
            ("boolean zeta", ("zeta",), False, "JSON integer"),
            ("float zeta", ("zeta",), 0.0, "JSON integer"),
            ("wrong target rotation", ("zeta",), 2, "identity fails")):
        yield mutant("tri unit " + name, TU, LP + path, value, reason)
    yield mutant("unit leaf with refuted verdict", TU, ("verdict",), "refuted", "verdict/edge mismatch")
    yield mutant("collision leaves with tu verdict", TC, ("verdict",), "tu", "verdict/edge mismatch")
    yield mutant("mixed leaves with refuted verdict", mixed, ("verdict",), "refuted", "verdict/edge mismatch")
    yield mutant("must check leaves after a unit leaf", mixed,
                  TP + ("minus", "leaf", "scale"), [0, 0], "must be nonzero")
    yield mutant("wrong ring w squared equals minus w minus one", KT, TP,
                  k4_triangle_tree(True), "identity fails")
    swapped_children = split([3, 5, 6], ROT["witness"]["tri"]["tree"]["minus"],
                             ROT["witness"]["tri"]["tree"]["plus"])
    yield mutant("orientation signs swapped", ROT, TP, swapped_children, "identity fails")
    yield mutant("triangle row coefficient sign flip", ROT, ROT_PLUS + ("triangle_coefficients", 0),
                  [-1, 1], "identity fails")

    # An embeddable diamond. The off-diagonal leaves below would become
    # identities if +60/-60 were incorrectly replaced by +120/-120:
    # r(0,2,1,3) + t(012,+) + t(013,-) = -2*(e_0-e_1).
    diamond = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3)]
    wrong120 = leaf([[0, 2, 1, 3]], [[1, 0]], [[0, 1, 2], [0, 1, 3]],
                    [[1, 0], [1, 0]], [-2, 0], [0, 1])
    wrong120tree = split([0, 1, 2],
                         split([0, 1, 3], equal_triangle_leaf(), wrong120),
                         split([0, 1, 3], wrong120, equal_triangle_leaf()))
    yield control("false diamond refutation using w squared in place of w",
                  tri(4, diamond, wrong120tree), "identity fails")
    unsorted_tree = split([0, 1, 2],
                          split([0, 1, 3], equal_triangle_leaf(), equal_triangle_leaf(True)),
                          split([0, 1, 3], equal_triangle_leaf(True), equal_triangle_leaf()))
    yield control("set-lookup unsorted triangle falsely refutes diamond",
                  tri(4, diamond, unsorted_tree), "sorted triangle")

    # Adding 8*(2^61)*r(C) changes an integer identity by 2^64*r(C),
    # invisible to a verifier working modulo 2^64. Each coefficient is legal.
    overflow = changed(R, RP + ("cycles",), K23_CYCLES + [K23_CYCLES[0]] * 8)
    overflow = changed(overflow, RP + ("coefficients",), [1, -1] + [1 << 61] * 8)
    yield control("int64 wraparound fake rhombus identity", overflow, "identity fails")
    yield control("int64 wraparound fake tri identity", lift(overflow), "identity fails")
    wide = changed(overflow, RP + ("cycles",), K23_CYCLES + [K23_CYCLES[0]] * 16)
    wide = changed(wide, RP + ("coefficients",), [1, -1] + [1 << 61] * 8 + [-(1 << 61)] * 8)
    yield positive("exact cancellation after sums exceed 2^64", wide, "rhombus_refuted")
    yield positive("tri cancellation after sums exceed 2^64", lift(wide), "tri_refuted")
    yield control("first invalid record reported as line two", dumps(UNKNOWN) + "\n" + dumps(overflow) + "\n" + dumps(R),
                  "identity fails", line=2)
    yield control("UTF-8 error line two", (dumps(UNKNOWN) + "\n").encode() + b'\xff\n',
                  "not valid UTF-8", line=2)

    maximum = changed(R, RP + ("cycles",), K23_CYCLES + [K23_CYCLES[0]] * 4094)
    maximum = changed(maximum, RP + ("coefficients",), [1, -1] + [1, -1] * 2047)
    yield positive("exactly 4096 rhombus cycles", maximum, "rhombus_refuted")
    yield positive("exactly 4096 tri cycles", lift(maximum), "tri_refuted")
    many_triangles = changed(KT, KP + ("triangles",), [[0, 1, 2], [0, 1, 3]] + [[0, 1, 2]] * 4096)
    many_triangles = changed(many_triangles, KP + ("triangle_coefficients",),
                             [[1, 0], [-1, 0]] + [[1, 0], [-1, 0]] * 2048)
    yield positive("no unstated triangle-row limit", many_triangles, "tri_refuted")
    yield positive("depth exactly 64", chain_record(64), "tri_refuted")
    yield control("depth 65", chain_record(65), "exceeds depth 64")
    yield positive("99999 tree nodes", node_budget_record(50000), "tri_refuted")
    yield control("100001 tree nodes", node_budget_record(50001), "exceeds 100000 nodes")


def expected_accept(kinds):
    counts = {name: kinds.count(name) for name in KINDS}
    return "ACCEPT records=" + str(len(kinds)) + " " + " ".join(
        name + "=" + str(counts[name]) for name in KINDS)


def main():
    red = valid = passed = failed = 0
    # Temporary files stay inside the directory authorized by the user.
    with tempfile.TemporaryDirectory(prefix=".selftest-", dir=HERE) as directory:
        input_path = Path(directory) / "control.certs.jsonl"
        for name, payload, reason, kinds, line in cases():
            if isinstance(payload, dict):
                payload = dumps(payload) + "\n"
            if isinstance(payload, str):
                payload = payload.encode("utf-8")
            input_path.write_bytes(payload)
            result = subprocess.run([sys.executable, str(HERE / "gpt_check.py"), str(input_path)],
                                    cwd=HERE, capture_output=True, text=True)
            output = result.stdout.rstrip("\n")
            clean = not result.stderr and len(result.stdout.splitlines()) == 1
            if reason is None:
                valid += 1
                ok = clean and result.returncode == 0 and output == expected_accept(kinds)
            else:
                red += 1
                ok = (clean and result.returncode == 1
                      and output.startswith("REJECT line " + str(line) + ": ")
                      and reason in output)
            if ok:
                passed += 1
            else:
                failed += 1
            print(("PASS " if ok else "FAIL ") + name + ": " + output, flush=True)
            if not ok:
                print("  expected: " + (expected_accept(kinds) if reason is None else reason), flush=True)
                print("  exit=" + str(result.returncode) + " stderr=" + repr(result.stderr), flush=True)
    print("SUMMARY " + ("PASS" if failed == 0 else "FAIL") + " cases=" + str(passed + failed)
          + " red=" + str(red) + " valid=" + str(valid) + " passed=" + str(passed)
          + " failed=" + str(failed))
    return int(failed != 0)


if __name__ == "__main__":
    sys.exit(main())
