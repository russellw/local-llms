# Router

Maps a request path to a registered route and captures its parameters.

## Patterns

A pattern is a `/`-separated list of segments. A segment is one of:

- **static** -- matches itself exactly: `users`
- **parameter** -- `:name`, matches exactly one segment and captures it under
  `name`
- **wildcard** -- `*name`, matches **all remaining segments** and captures them
  joined with `/`. Only legal as the last segment. It may match zero segments,
  capturing `""`.

## Precedence

This is the part that is easy to get wrong.

**Registration order does not decide anything.** When several patterns match a
path, the winner is chosen by comparing segments left to right. At the first
segment where the candidates differ, the more specific one wins:

    static  >  parameter  >  wildcard

So `/users/me` beats `/users/:id`, and `/users/:id` beats `/*rest`, no matter
which was registered first. Only if two patterns are identical in specificity
at every segment does the earlier registration win.

## Trailing slashes

`/users/me` and `/users/me/` are the same path. A trailing slash is never
significant and never produces an empty final segment. The root path `/` has no
segments.

## No match

`match` returns `None` when nothing matches. It never raises.
