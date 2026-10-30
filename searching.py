"""
searching.py - search algorithms, string/number filters and composite filters.
"""
import time

from schema import NUMERIC_FIELDS, get_key
from sorting_algos import Counter, merge_sort

SEARCH_ALGORITHMS = {
    "Linear Search": "O(n)  - works on any column",
    "Binary Search": "O(log n) - needs sorted data, equals only",
}

TEXT_OPS = ["contains", "starts with", "ends with", "equals", "not equals"]
NUM_OPS = ["=", "!=", ">", ">=", "<", "<="]


def ops_for(col):
    return NUM_OPS if col in NUMERIC_FIELDS else TEXT_OPS


def parse_target(col, text):
    """Convert what the user typed into something comparable."""
    if col in NUMERIC_FIELDS:
        return float(text)            # ValueError is handled by the UI
    return text.strip().lower()


def condition_matches(key, op, target):
    """Check one row's key against one condition (used by every filter)."""
    if op in ("equals", "="):
        return key == target
    if op in ("not equals", "!="):
        return key != target
    if op == "contains":
        return target in key
    if op == "starts with":
        return key.startswith(target)
    if op == "ends with":
        return key.endswith(target)
    if op == ">":
        return key > target
    if op == ">=":
        return key >= target
    if op == "<":
        return key < target
    if op == "<=":
        return key <= target
    raise ValueError("unknown operator " + op)


# ------------------------------------------------------------ search algorithms
def linear_search(keys, target):
    hits, cmp = [], 0
    for pos, k in enumerate(keys):
        cmp += 1
        if k == target:
            hits.append(pos)
    return hits, cmp


def _expand_equal(skeys, pos, target):
    """Given one matching position in a sorted list, collect all equal keys."""
    left = pos
    while left > 0 and skeys[left - 1] == target:
        left -= 1
    right = pos
    while right + 1 < len(skeys) and skeys[right + 1] == target:
        right += 1
    return list(range(left, right + 1))


def binary_search(skeys, target):
    lo, hi, cmp = 0, len(skeys) - 1, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        cmp += 1
        if skeys[mid] == target:
            return _expand_equal(skeys, mid, target), cmp
        cmp += 1
        if skeys[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return [], cmp


def search_column(indices, col, op, text, algorithm, data):
    """Quick search on one column. Returns (matching row indices, info dict)."""
    target = parse_target(col, text)
    note = ""
    start = time.perf_counter()

    exact_algo = algorithm != "Linear Search" and op in ("equals", "=")
    if algorithm != "Linear Search" and not exact_algo:
        note = f"{algorithm} only supports Equals, so Linear Search was used."

    if exact_algo:
        # binary search needs sorted keys -> sort first (time not counted)
        items = [(get_key(data[i], col), i) for i in indices]
        ordered = merge_sort(items, Counter())
        skeys = [k for k, _ in ordered]
        sidx = [i for _, i in ordered]
        search_start = time.perf_counter()
        positions, cmp = binary_search(skeys, target)
        hits = [sidx[p] for p in positions]
        ms = (time.perf_counter() - search_start) * 1000
        used = algorithm
    else:
        hits, cmp = [], 0
        for i in indices:
            cmp += 1
            if condition_matches(get_key(data[i], col), op, target):
                hits.append(i)
        ms = (time.perf_counter() - start) * 1000
        used = "Linear Search"
    return hits, {"ms": ms, "comparisons": cmp, "algorithm": used, "note": note}


# ---------------------------------------------------------- composite filters
def composite_filter(indices, conditions, connectors, data):
    """conditions = [(negate, col, op, text), ...]
    connectors = ['AND' / 'OR', ...] between neighbouring conditions.

    AND binds tighter than OR, like normal logic:
        A OR B AND C   ==   A OR (B AND C)
    """
    parsed = [(neg, col, op, parse_target(col, text)) for neg, col, op, text in conditions]
    hits = []
    for i in indices:
        row = data[i]
        truths = []
        for neg, col, op, target in parsed:
            t = condition_matches(get_key(row, col), op, target)
            truths.append((not t) if neg else t)
        groups = [[truths[0]]]
        for connector, t in zip(connectors, truths[1:]):
            if connector == "AND":
                groups[-1].append(t)
            else:
                groups.append([t])
        if any(all(g) for g in groups):
            hits.append(i)
    return hits
