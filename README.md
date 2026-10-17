# contrib-postgres

PostgreSQL storage backend for [Bazaar Compute Node](https://github.com/yuchanns/bazaar-compute-node).

Install:

```sh
bcn contrib add bazaar-contrib-postgres --source https://pypi.org/simple/
```

In `~/.bcn/config.toml`, enable `postgres` and update the existing storage entries:

```toml
[[contribs]]
package = "bazaar-contrib-postgres"
[[contribs.enabled]]
entry = "postgres"
[contribs.enabled.config]
dsn = "postgresql://user:password@localhost:5432/bcn"

[[contribs]]
package = "bazaar-contrib-storage"
[[contribs.enabled]]
entry = "storage"
[[contribs.enabled]]
entry = "database"
[contribs.enabled.config]
backend = "postgres"
```

Start with `bcn run`.
