#!/usr/bin/env python3
"""Independent verifier for RHOMBUS-SPEC.md Sections 2, 4, and 5.

Only Python's standard library is used. No producer or other checker is called.
The public entry point is: python3 gpt_check.py FILE.certs.jsonl
"""

import json
import sys


# JSON integers must retain their value even on Python versions with a default
# decimal-conversion digit limit. Certificate component bounds are checked later.
if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)


LIMIT = 1 << 62
MAX_CYCLES = 4096
MAX_NODES = 100000
MAX_DEPTH = 64  # Number of edges from the root, whose depth is zero.
ZERO = (0, 0)
ONE = (1, 0)
ROOTS = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))
LEAF_KEYS = {
    "cycles", "cycle_coefficients", "triangles", "triangle_coefficients",
    "scale", "pair",
}


class Invalid(ValueError):
    """An invalid certificate, with a user-facing explanation."""


def require(condition, reason):
    if not condition:
        raise Invalid(reason)


def exact_keys(obj, expected, where):
    require(type(obj) is dict, where + " must be an object")
    actual = set(obj)
    require(actual == expected,
            where + " must have exactly keys " + ", ".join(sorted(expected)))


def no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "duplicate JSON key " + repr(key))
        obj[key] = value
    return obj


def no_constant(value):
    raise Invalid("non-JSON numeric constant " + value)


def parse_record(line):
    try:
        return json.loads(line, object_pairs_hook=no_duplicates,
                          parse_constant=no_constant)
    except json.JSONDecodeError as exc:
        raise Invalid("invalid JSON: " + exc.msg) from None
    except RecursionError:
        raise Invalid("JSON nesting exceeds parser capacity") from None


def decode_graph6(value):
    """Decode graph6 directly, including its two extended order encodings.

    Require the shortest order encoding, exact payload length, and zero padding.
    An optional standard >>graph6<< header is accepted inside the JSON string.
    """
    require(type(value) is str, "g6 must be a string")
    if value.startswith(">>graph6<<"):
        value = value[len(">>graph6<<"):]
    require(bool(value), "g6 is empty")
    require(all(63 <= ord(ch) <= 126 for ch in value),
            "g6 contains a character outside ASCII 63..126")
    units = [ord(ch) - 63 for ch in value]
    if units[0] != 63:
        n, offset = units[0], 1
    elif len(units) >= 2 and units[1] != 63:
        require(len(units) >= 4, "g6 has a truncated 18-bit order")
        n = (units[1] << 12) | (units[2] << 6) | units[3]
        offset = 4
        require(n >= 63, "g6 order encoding is not minimal")
    else:
        require(len(units) >= 8, "g6 has a truncated 36-bit order")
        n = 0
        for unit in units[2:8]:
            n = (n << 6) | unit
        offset = 8
        require(n >= 258048, "g6 order encoding is not minimal")
    bit_count = n * (n - 1) // 2
    require(len(units) - offset == (bit_count + 5) // 6,
            "g6 payload length does not match its order")
    if bit_count % 6:
        padding = 6 - bit_count % 6
        require(units[-1] & ((1 << padding) - 1) == 0,
                "g6 has nonzero padding bits")
    adjacency = [set() for _ in range(n)]
    index = 0
    for v in range(1, n):
        for u in range(v):
            if units[offset + index // 6] & (1 << (5 - index % 6)):
                adjacency[u].add(v)
                adjacency[v].add(u)
            index += 1
    return adjacency


def integer(value, where):
    require(type(value) is int, where + " must be a JSON integer (not boolean or float)")
    return value


def bounded_integer(value, where):
    integer(value, where)
    require(abs(value) < LIMIT, where + " must have absolute value below 2^62")
    return value


def vertex_list(value, length, graph, where):
    require(type(value) is list and len(value) == length,
            where + " must be a list of " + str(length) + " vertices")
    for vertex in value:
        integer(vertex, where + " vertex")
        require(0 <= vertex < len(graph), where + " vertex is out of range")
    require(len(set(value)) == length, where + " vertices must be distinct")
    return value


def cycle(value, graph, where):
    vertices = vertex_list(value, 4, graph, where)
    for i in range(4):
        require(vertices[(i + 1) % 4] in graph[vertices[i]],
                where + " has a missing cycle edge")
    return vertices


def triangle(value, graph, where):
    a, b, c = vertex_list(value, 3, graph, where)
    require(a < b < c, where + " must be a sorted triangle a < b < c")
    require(b in graph[a] and c in graph[a] and c in graph[b],
            where + " has a missing triangle edge")
    return (a, b, c)


def pair(value, graph, where):
    return vertex_list(value, 2, graph, where)


def zw(value, where):
    require(type(value) is list and len(value) == 2,
            where + " must be a Z[w] pair [x, y]")
    x = bounded_integer(value[0], where + " real component")
    y = bounded_integer(value[1], where + " w component")
    require(x != 0 or y != 0, where + " must be nonzero")
    return (x, y)


def mul(a, b):
    # (x + y*w)(u + v*w), with w*w = w - 1.
    x, y = a
    u, v = b
    return (x * u - y * v, x * v + y * u + y * v)


def neg(a):
    return (-a[0], -a[1])


def add_at(vector, vertex, value):
    old = vector[vertex]
    vector[vertex] = (old[0] + value[0], old[1] + value[1])


def equal_vectors(left, right, where):
    for vertex, (lhs, rhs) in enumerate(zip(left, right)):
        require(lhs == rhs, where + " identity fails at vertex " + str(vertex)
                + ": " + str(lhs) + " != " + str(rhs))


def verify_rhombus(obj, verdict, graph):
    keys = {"cycles", "coefficients", "scale", "pair"}
    if verdict == "tu":
        keys.add("edge")
    exact_keys(obj, keys, "rhombus")
    cycles = obj["cycles"]
    coefficients = obj["coefficients"]
    require(type(cycles) is list and 1 <= len(cycles) <= MAX_CYCLES,
            "rhombus cycles must be a nonempty list of at most 4096 entries")
    require(type(coefficients) is list and len(coefficients) == len(cycles),
            "rhombus coefficients must match cycles in length")
    scale = bounded_integer(obj["scale"], "rhombus scale")
    require(scale != 0, "rhombus scale must be nonzero")
    a, b = pair(obj["pair"], graph, "rhombus pair")
    target = [0] * len(graph)
    target[a] += scale
    target[b] -= scale
    if verdict == "tu":
        require(b not in graph[a], "rhombus tu pair must be a non-edge")
        p, q = pair(obj["edge"], graph, "rhombus edge")
        require(q in graph[p], "rhombus edge is not an edge of G")
        target[p] -= scale
        target[q] += scale
    actual = [0] * len(graph)
    for index, (vertices, coefficient) in enumerate(zip(cycles, coefficients)):
        where = "rhombus cycle " + str(index)
        u, v, w, x = cycle(vertices, graph, where)
        bounded_integer(coefficient, "rhombus coefficient " + str(index))
        require(coefficient != 0, "rhombus coefficient must be nonzero")
        actual[u] += coefficient
        actual[v] -= coefficient
        actual[w] += coefficient
        actual[x] -= coefficient
    equal_vectors(actual, target, "rhombus")


def verify_leaf(obj, path, graph, where):
    require(type(obj) is dict, where + " must be an object")
    has_edge = "edge" in obj
    require(has_edge == ("zeta" in obj), where + " needs edge and zeta together")
    exact_keys(obj, LEAF_KEYS | ({"edge", "zeta"} if has_edge else set()), where)
    cycles = obj["cycles"]
    triangles = obj["triangles"]
    require(type(cycles) is list and len(cycles) <= MAX_CYCLES,
            where + " cycles must be a list of at most 4096 entries")
    require(type(triangles) is list, where + " triangles must be a list")
    require(bool(cycles) or bool(triangles), where + " row lists cannot both be empty")
    for rows, name in ((cycles, "cycle_coefficients"),
                       (triangles, "triangle_coefficients")):
        require(type(obj[name]) is list and len(obj[name]) == len(rows),
                where + " " + name + " must match its rows in length")
    scale = zw(obj["scale"], where + " scale")
    a, b = pair(obj["pair"], graph, where + " pair")
    target = [ZERO] * len(graph)
    add_at(target, a, ONE)
    add_at(target, b, neg(ONE))
    if has_edge:
        p, q = pair(obj["edge"], graph, where + " edge")
        require(q in graph[p], where + " edge is not an edge of G")
        require(b not in graph[a], where + " tu pair must be a non-edge")
        k = integer(obj["zeta"], where + " zeta")
        require(0 <= k <= 5, where + " zeta must be in 0..5")
        add_at(target, p, neg(ROOTS[k]))
        add_at(target, q, ROOTS[k])
    target = [mul(scale, entry) for entry in target]
    actual = [ZERO] * len(graph)
    for index, (vertices, coefficient) in enumerate(zip(cycles, obj["cycle_coefficients"])):
        u, v, w, x = cycle(vertices, graph, where + " cycle " + str(index))
        coefficient = zw(coefficient, where + " cycle coefficient " + str(index))
        add_at(actual, u, coefficient)
        add_at(actual, v, neg(coefficient))
        add_at(actual, w, coefficient)
        add_at(actual, x, neg(coefficient))
    for index, (vertices, coefficient) in enumerate(zip(triangles, obj["triangle_coefficients"])):
        key = triangle(vertices, graph, where + " triangle " + str(index))
        require(key in path, where + " triangle was not split on this path")
        coefficient = zw(coefficient, where + " triangle coefficient " + str(index))
        rotation = ROOTS[1] if path[key] == 1 else ROOTS[5]
        a, b, c = key
        # t(T,s) = e_c + (w^s - 1)e_a - w^s e_b.
        add_at(actual, c, coefficient)
        add_at(actual, a, mul(coefficient, (rotation[0] - 1, rotation[1])))
        add_at(actual, b, neg(mul(coefficient, rotation)))
    equal_vectors(actual, target, where)
    return has_edge


def verify_tri(obj, verdict, graph):
    exact_keys(obj, {"tree"}, "tri")
    stack = [(obj["tree"], 0, {}, "tree")]
    count = 0
    any_edge = False
    while stack:
        node, depth, path, where = stack.pop()
        count += 1
        require(count <= MAX_NODES, "tri tree exceeds 100000 nodes")
        require(depth <= MAX_DEPTH, "tri tree exceeds depth 64")
        require(type(node) is dict, where + " must be a node object")
        if "split" in node:
            exact_keys(node, {"split", "plus", "minus"}, where + " split node")
            key = triangle(node["split"], graph, where + " split")
            require(key not in path, where + " repeats a split triangle on one path")
            for child, sign in (("minus", -1), ("plus", 1)):
                require(type(node[child]) is dict, where + "." + child + " must be a node object")
                child_path = path.copy()
                child_path[key] = sign
                stack.append((node[child], depth + 1, child_path, where + "." + child))
        else:
            exact_keys(node, {"leaf"}, where + " leaf node")
            has_edge = verify_leaf(node["leaf"], path, graph, where + ".leaf")
            any_edge = any_edge or has_edge
    expected = "tu" if any_edge else "refuted"
    require(verdict == expected,
            "tri verdict/edge mismatch: expected " + expected)


def verify_record(obj):
    require(type(obj) is dict, "record must be an object")
    verdict = obj.get("verdict")
    require(type(verdict) is str and verdict in ("unknown", "refuted", "tu"),
            "verdict must be unknown, refuted, or tu")
    keys = {"g6", "verdict"}
    if verdict != "unknown":
        keys.add("witness")
    exact_keys(obj, keys, "record")
    graph = decode_graph6(obj["g6"])
    if verdict == "unknown":
        return "unknown"
    witness = obj["witness"]
    require(type(witness) is dict and set(witness) in ({"rhombus"}, {"tri"}),
            "witness must have exactly one key: rhombus or tri")
    if "rhombus" in witness:
        verify_rhombus(witness["rhombus"], verdict, graph)
        return "rhombus_" + verdict
    verify_tri(witness["tri"], verdict, graph)
    return "tri_" + verdict


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        print("REJECT line 0: usage: python3 gpt_check.py FILE.certs.jsonl")
        return 1
    counts = dict.fromkeys(("unknown", "rhombus_refuted", "rhombus_tu", "tri_refuted", "tri_tu"), 0)
    records = 0
    line_number = 0
    try:
        with open(argv[0], "rb") as stream:
            for line_number, raw in enumerate(stream, 1):
                try:
                    line = raw.decode("utf-8")
                except UnicodeDecodeError:
                    raise Invalid("record is not valid UTF-8") from None
                kind = verify_record(parse_record(line))
                records += 1
                counts[kind] += 1
    except (Invalid, OSError) as exc:
        # Line zero denotes a command-line or file-open failure, before input.
        print("REJECT line " + str(line_number) + ": " + str(exc))
        return 1
    print("ACCEPT records=" + str(records) + " " + " ".join(
        name + "=" + str(count) for name, count in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
