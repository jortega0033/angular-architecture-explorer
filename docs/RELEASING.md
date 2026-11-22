# Releasing

Only the owner releases. Agents never tag, publish or create a release.

A release here is a tagged commit on `main`. The project is not published as a package; the version lives in `architecture_explorer/__init__.py` (`__version__`) and is reported by `GET /api/v1/health`.

## Steps

1. Confirm every ticket planned for the release is merged and CI is green on `main` (Linux and Windows, Python 3.12 and 3.13).
2. On a branch, bump `__version__` and move the `Unreleased` lines in `CHANGELOG.md` under a new version heading with the date. Open a pull request; the owner merges it.
3. From a fresh clone of the merge commit with an empty data directory, run the README quickstart verbatim and `python -m unittest discover -s tests -v`. Record the results.
4. Check that no database, data directory or `.env*` file is tracked: `git ls-files`.
5. The owner tags the merge commit: `git tag -a vX.Y.Z -m "vX.Y.Z"` and pushes the tag.
6. The owner creates the GitHub release from the tag, with the changelog section as notes.

The release-candidate gate for epic #1 is ticket #7.
