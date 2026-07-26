import heapq


def topo_sort(graph: dict) -> list:
    indegree = {n: 0 for n in graph}
    for deps in graph.values():
        for v in deps:
            indegree[v] = indegree.get(v, 0) + 1

    ready = [n for n, d in indegree.items() if d == 0]
    heapq.heapify(ready)

    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for v in graph.get(n, []):
            indegree[v] -= 1
            if indegree[v] == 0:
                heapq.heappush(ready, v)

    if len(out) != len(indegree):
        raise ValueError("graph contains a cycle")
    return out
