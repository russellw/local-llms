# Design

`Store.open(fs)` opens the store kept in the filesystem `fs`, creating an
empty one if there is nothing there yet. `get`, `keys` and `commit` read and
change it. The filesystem is `src/fs.py`; its docstring says what survives
when the power goes out.

## Keys and values

Keys and values are strings. A key is any non-empty string, whatever
characters it contains. `get` of a key the store does not hold returns
`None`. `keys` returns the keys the store holds, sorted.

## Commits

`commit(changes)` applies a dict of changes as one: a string value sets that
key, and `None` deletes it. Deleting a key the store does not hold is not an
error.

The power can go out at any moment, including partway through a commit or
while the store is being opened. Whenever it happens, opening the store
afterwards gives its contents exactly as they were before the commit that was
under way, or exactly as they are after it: never some keys from before and
some from after, and never a value that no commit set. Once `commit` has
returned, that commit is permanent, and no later power loss can undo it.

A store can hold a lot of data, so a commit writes data only for the keys it
changes. Rewriting every value on each commit is not acceptable, however small
the store happens to be.
