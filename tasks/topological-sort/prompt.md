Write a function:

```python
def topo_sort(graph: dict) -> list
```

`graph` maps each node to a list of nodes that depend on it — an edge
`u -> v` means `u` must come before `v` in the output. Every node appears as a
key, including nodes with no outgoing edges (their value is an empty list).
Node names are strings.

Return a list containing every node exactly once, in an order that respects all
edges. When several nodes are ready at the same time, the result must be
**deterministic**: always emit the alphabetically smallest ready node first.
A node is ready once all nodes with an edge pointing to it have been emitted.

If the graph contains a cycle, raise `ValueError`.

The empty graph returns an empty list.
