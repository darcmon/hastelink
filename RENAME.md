# Rename to klinkrr

The source, package names, login heading, browser title, and fresh-install
database defaults now use `klinkrr`. The API title already used this name.

## Existing local infrastructure

Database migration completed on September 17, 2026:

- PostgreSQL role: `hastelink` → `klinkrr`
- Application database: `haste_link` → `klinkrr`
- Test database: `haste_link_test` → `klinkrr_test`
- Active `.env` updated to the new application database and role.
- Both databases were renamed in place, preserving their tables and ownership.
- Backups are in the git-ignored `secrets/db-rename-ArtWPP/` directory:
  `app.dump`, `test.dump`, and `roles.sql`. Treat these as private data.
- All 212 backend tests passed against the renamed test database.

These infrastructure names still remain:

- Docker project: `hastelink`
- Docker volumes: `hastelink_pgdata` and `hastelink_miniodata`
- Local repository folder: `/Users/richard/code/hastelink`

Changing `POSTGRES_USER` and `POSTGRES_DB` in Compose only affects initialization
of an empty database volume; it does not rename an existing role or database.
That database/role rename has now been performed separately. Restart any backend
process started before the migration so it loads the updated `.env`. Update any
shell/IDE test configuration to use the following values:

```dotenv
DATABASE_URL=postgresql+asyncpg://klinkrr:localdev@localhost:5432/klinkrr
PHASE1_TEST_DATABASE_URL=postgresql+asyncpg://klinkrr:localdev@localhost:5432/klinkrr_test
```

Preserve the actual password if it differs from the local example above.
`PHASE1_TEST_DATABASE_URL` must be exported into the test process; merely adding
it to `.env` does not make the tests read it.

Renaming the folder changes Compose's default project name. Before starting
Compose from a renamed folder, either migrate both volumes or explicitly attach
the existing volumes. Otherwise, Compose creates fresh volumes, and the old
containers may also conflict on ports. Temporarily use
`docker compose -p hastelink ...` to continue operating the existing stack.
Do not use `docker compose down -v` unless intentionally deleting the database
and uploaded files.

The default bucket is now `klinkrr`; `.env.example` still explicitly selects the
existing generic bucket name `file-approval`. An actual bucket rename requires
creating a new bucket, copying objects, and updating `S3_BUCKET`. Changing a
configuration string alone does not move objects.

## Local folder and Python installation

After handling Compose volumes, close running development processes and rename
the folder to `/Users/richard/code/klinkrr`, then reopen it in the IDE. Recreate
the virtual environment at that path and reinstall with
`python -m pip install -e '.[dev]'`: virtual-environment scripts and editable
installs can embed absolute paths. Old `hastelink.egg-info` is generated metadata;
remove it when replacing the old installation. It is not application data.

Chat transcripts, historical Git commits, and historical file links retain the
old name. They do not need to be rewritten for the application rename.

## GitHub last

1. Open `darcmon/hastelink` on GitHub, then Settings → General.
2. Set Repository name to `klinkrr` and click Rename.
3. In the local checkout, run:

   ```bash
   git remote set-url origin https://github.com/darcmon/klinkrr.git
   git remote -v
   git ls-remote origin HEAD
   ```

GitHub redirects ordinary repository links and Git operations. Avoid creating a
new repository with the old name, which would remove that redirect. GitHub Pages
URLs and references to actions hosted in a renamed repository need separate
updates if applicable.

Reference: https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository
