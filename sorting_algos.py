"""
sorting_algos.py - all sorting algorithms of the project.

Every algorithm works on a list of (key, row_index) pairs and compares only
the key. A Counter object records how many comparisons and swaps happened.

Bubble, Selection, Insertion, Merge and Quick sort follow the class-style code:
the sorting logic is the same as the plain textbook version on numbers. The
only extra parts are: `c` (to count comparisons / swaps), `desc` (to choose
ascending or descending) and `before()` (compares only the key of a pair).

Notes about the metrics:
  * insertion / shell: every element shift is counted as one "swap"
  * merge sort: every element written back into arr counts as one "swap"
  * counting / radix / bucket are not comparison sorts, so they only report
    "swaps" (= element placements) and bucket sort's insertion-sort comparisons
"""
import random
import time

MAX_COUNT_RANGE = 8_000_000   # counting sort needs an array of this size at most


class Counter:
    def __init__(self):
        self.comparisons = 0
        self.swaps = 0


def before(c, a, b, desc=False):
    """True if item a must come strictly before item b. Counts a comparison."""
    c.comparisons += 1
    if desc:
        return a[0] > b[0]
    return a[0] < b[0]


# ---------------------------------------------------------------- simple sorts
def bubble_sort(items, c, desc=False):
    arr = items[:]                         # work on a copy
    n = len(arr)
    for i in range(n - 1):                 # n-1 rounds
        for j in range(0, n - 1 - i):      # the last i elements are already in place
            # same as: arr[j] > arr[j + 1]   (for ascending order)
            if before(c, arr[j + 1], arr[j], desc):
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                c.swaps += 1
    return arr


def selection_sort(items, c, desc=False):
    arr = items[:]
    n = len(arr)
    for i in range(n - 1):
        mini = i                           # index of the smallest element seen so far
        for j in range(i + 1, n):
            # same as: arr[j] < arr[mini]   (for ascending order)
            if before(c, arr[j], arr[mini], desc):
                mini = j
        arr[i], arr[mini] = arr[mini], arr[i]
        if mini != i:
            c.swaps += 1                   # swapping an element with itself is not counted
    return arr


def insertion_sort(items, c, desc=False):
    arr = items[:]                 # work on a copy, the original list stays untouched
    n = len(arr)
    for i in range(1, n):
        key = arr[i]               # the element we want to put in its correct place
        j = i - 1                  # start looking at the element just left of key
        # keep going while we have not fallen off the left end AND the element at j
        # must come after key (for ascending order: arr[j] > key)
        while j >= 0 and before(c, key, arr[j], desc):
            arr[j + 1] = arr[j]    # shift the bigger element one place to the right
            c.swaps += 1           # every shift is counted as one swap
            j = j - 1              # move one more place to the left
        arr[j + 1] = key           # drop key into the gap
    return arr


def cocktail_sort(items, c, desc=False):
    """Bubble sort that goes forward and then backward (extra algorithm 1)."""
    arr = items[:]
    n=len(arr)
    start=0
    end=n-1
    swapped=True

    while swapped:
        swapped = False
        for i in range(start, end):
            if before(c, arr[i + 1], arr[i], desc):
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                c.swaps += 1
                swapped = True
        if not swapped:
            break
        start -= 1
        swapped = False
        for i in range(start - 1, end - 1, -1):
            if before(c, arr[i + 1], arr[i], desc):
                arr[i], arr[i + 1] = arr[i + 1], arr[i]
                c.swaps += 1
                swapped = True
        if not swapped:
            break
        end += 1
    return arr


def shell_sort(items, c, desc=False):
    """Insertion sort with shrinking gaps (extra algorithm 2)."""
    a = items[:]
    n = len(a)
    gap = n // 2
    while gap > 0:
        for i in range(gap, n):
            current = a[i]
            j = i
            while j >= gap and before(c, current, a[j - gap], desc):
                a[j] = a[j - gap]
                c.swaps += 1
                j -= gap
            a[j] = current
        gap //= 2
    return a


# ----------------------------------------------------------- divide & conquer
def divide(arr, l, r, c, desc=False):
    if l < r:
        m = (l + r) // 2
        divide(arr, l, m, c, desc)         # sort the left half
        divide(arr, m + 1, r, c, desc)     # sort the right half
        merge(arr, l, m, r, c, desc)       # join the two sorted halves


def merge(arr, l, m, r, c, desc=False):
    s1 = m - l + 1                         # size of the left half
    s2 = r - m                             # size of the right half
    left_arr = [0] * s1
    right_arr = [0] * s2
    for i in range(s1):
        left_arr[i] = arr[l + i]
    for j in range(s2):
        right_arr[j] = arr[m + 1 + j]

    i = 0
    j = 0
    k = l
    while i < s1 and j < s2:
        # take from the right only if it is STRICTLY before the left one.
        # With equal keys the left one goes first, and that keeps merge sort stable.
        if not before(c, right_arr[j], left_arr[i], desc):
            arr[k] = left_arr[i]
            i += 1
        else:
            arr[k] = right_arr[j]
            j += 1
        c.swaps += 1
        k += 1
    while i < s1:                          # left half still has elements
        arr[k] = left_arr[i]
        i += 1
        k += 1
        c.swaps += 1
    # if the RIGHT half has elements left, they are already at their final
    # positions in arr, so no loop is needed for them


def merge_sort(items, c, desc=False):
    arr = items[:]
    divide(arr, 0, len(arr) - 1, c, desc)
    return arr


def QuickSort(arr, l, r, c, desc=False):
    if l < r:
        p = partition(arr, l, r, c, desc)
        QuickSort(arr, l, p - 1, c, desc)      # sort the part left of the pivot
        QuickSort(arr, p + 1, r, c, desc)      # sort the part right of the pivot


def partition(arr, l, r, c, desc=False):
    # project only: pick a random pivot and move it to position l. Without this,
    # data that is already sorted would make quick sort very slow (and very deep).
    k = random.randint(l, r)
    arr[l], arr[k] = arr[k], arr[l]
    if k != l:
        c.swaps += 1

    pivot = arr[l]
    i = l + 1
    j = r
    while True:
        # i moves right while arr[i] < pivot (stops at an element that is >= pivot)
        while i <= j and before(c, arr[i], pivot, desc):
            i = i + 1
        # j moves left while arr[j] > pivot (stops at an element that is <= pivot)
        while i <= j and before(c, pivot, arr[j], desc):
            j = j - 1
        if i < j:
            arr[i], arr[j] = arr[j], arr[i]
            c.swaps += 1
            i = i + 1                      # move on, otherwise equal keys loop forever
            j = j - 1
        else:
            break
    arr[l], arr[j] = arr[j], arr[l]        # put the pivot in its final place
    if l != j:
        c.swaps += 1
    return j


def quick_sort(items, c, desc=False):
    arr = items[:]
    QuickSort(arr, 0, len(arr) - 1, c, desc)
    return arr


# --------------------------------------------------- linear time (numbers only)
def _int_keys(items, desc):
    """Turn float keys into non-negative ints (x10 keeps one decimal digit).
    For descending order we negate first, so the same ascending code works."""
    vals = [int(round(k * 10)) for k, _ in items]
    if desc:
        vals = [-v for v in vals]
    low = min(vals)
    return [v - low for v in vals]


def counting_sort(items, c, desc=False):
    n = len(items)
    if n == 0:
        return []
    vals = _int_keys(items, desc)
    k = max(vals)
    if k > MAX_COUNT_RANGE:
        raise ValueError("Counting sort: key range too large for this column "
                         "(use Radix Sort instead)")
    count = [0] * (k + 1)
    for v in vals:
        count[v] += 1
    for i in range(1, k + 1):
        count[i] += count[i - 1]
    output = [None] * n
    for i in range(n - 1, -1, -1):      # backwards -> stable
        v = vals[i]
        count[v] -= 1
        output[count[v]] = items[i]
        c.swaps += 1
    return output


def radix_sort(items, c, desc=False):
    n = len(items)
    if n == 0:
        return []
    vals = _int_keys(items, desc)
    order = list(range(n))
    biggest = max(vals)
    exp = 1
    while biggest // exp > 0:           # one counting-sort pass per digit
        count = [0] * 10
        for i in order:
            count[(vals[i] // exp) % 10] += 1
        for d in range(1, 10):
            count[d] += count[d - 1]
        out = [0] * n
        for i in reversed(order):
            d = (vals[i] // exp) % 10
            count[d] -= 1
            out[count[d]] = i
            c.swaps += 1
        order = out
        exp *= 10
    return [items[i] for i in order]


def bucket_sort(items, c, desc=False):
    n = len(items)
    if n == 0:
        return []
    vals = _int_keys(items, desc)
    biggest = max(vals)
    buckets = [[] for _ in range(n)]
    for i, v in enumerate(vals):
        b = 0 if biggest == 0 else min(n - 1, v * n // (biggest + 1))
        buckets[b].append(i)
        c.swaps += 1
    result = []
    for bucket in buckets:              # insertion sort inside every bucket
        for x in range(1, len(bucket)):
            current = bucket[x]
            y = x - 1
            while y >= 0:
                c.comparisons += 1
                if vals[current] < vals[bucket[y]]:
                    bucket[y + 1] = bucket[y]
                    c.swaps += 1
                    y -= 1
                else:
                    break
            bucket[y + 1] = current
        result.extend(bucket)
    return [items[i] for i in result]


# ------------------------------------------------------------------- registry
# slow = can take very long on 15k rows (O(n^2) behaviour)
ALGORITHMS = {
    "Bubble Sort":    dict(fn=bubble_sort,    complexity="O(n²)",              stable=True,  numeric_only=False, slow=True),
    "Selection Sort": dict(fn=selection_sort, complexity="O(n²)",              stable=False, numeric_only=False, slow=True),
    "Insertion Sort": dict(fn=insertion_sort, complexity="O(n²)",              stable=True,  numeric_only=False, slow=True),
    "Merge Sort":     dict(fn=merge_sort,     complexity="O(n log n)",         stable=True,  numeric_only=False, slow=False),
    "Quick Sort":     dict(fn=quick_sort,     complexity="O(n log n) avg",     stable=False, numeric_only=False, slow=False),
    "Counting Sort":  dict(fn=counting_sort,  complexity="O(n + k)",           stable=True,  numeric_only=True,  slow=False),
    "Radix Sort":     dict(fn=radix_sort,     complexity="O(d·(n + b))",       stable=True,  numeric_only=True,  slow=False),
    "Bucket Sort":    dict(fn=bucket_sort,    complexity="O(n + k) avg",       stable=True,  numeric_only=True,  slow=True),
    "Shell Sort (extra)":    dict(fn=shell_sort,    complexity="O(n²) worst",  stable=False, numeric_only=False, slow=False),
    "Cocktail Sort (extra)": dict(fn=cocktail_sort, complexity="O(n²)",        stable=True,  numeric_only=False, slow=True),
}


def algorithm_label(name):
    info = ALGORITHMS[name]
    return f"{name}  [{info['complexity']}, {'stable' if info['stable'] else 'not stable'}]"


def run_sort(name, items, desc=False):
    """Run one algorithm. Returns order of row indices + metrics."""
    c = Counter()
    start = time.perf_counter()
    result = ALGORITHMS[name]["fn"](items, c, desc)
    ms = (time.perf_counter() - start) * 1000
    return {"order": [idx for _, idx in result], "ms": ms,
            "comparisons": c.comparisons, "swaps": c.swaps}


def multi_level_sort(indices, levels):
    """Sort by several columns. levels = [(key_function, desc), ...] where the
    first level is the most important one.

    Trick: run a STABLE sort (merge sort) once per level, starting from the
    least important level. Later (more important) sorts keep the earlier order
    for rows that tie.
    """
    c = Counter()
    start = time.perf_counter()
    current = list(indices)
    for keyfn, desc in reversed(levels):
        items = [(keyfn(i), i) for i in current]
        current = [idx for _, idx in merge_sort(items, c, desc)]
    ms = (time.perf_counter() - start) * 1000
    return {"order": current, "ms": ms, "comparisons": c.comparisons, "swaps": c.swaps}