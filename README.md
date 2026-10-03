# steamwiz/actions

Shared GitHub Actions reusable-workflow library for the Steamwiz GitHub organisation.
Any Steamwiz project (or any public GitHub user) can call these workflows with a single `uses:` line.

## Workflows

| Workflow | Purpose |
|---|---|
| [`python-ci.yml`](#python-ciyml) | Test + coverage gate for a Python (Poetry) project. Read-only. |
| [`python-style.yml`](#python-styleyml) | pycodestyle check. Optional: call it only if you want it. |
| [`python-release.yml`](#python-releaseyml) | Version bump, tag and GitHub Release via python-semantic-release. The only workflow that writes. |
| [`python-pipeline.yml`](#python-pipelineyml-deprecated) | **Deprecated** monolith of the three above. Removed in v2. |
| [`mdbook-build.yml`](#mdbook-buildyml) | Build an mdBook documentation site |
| [`cloudflare-deploy.yml`](#cloudflare-deployyml) | Deploy a static site to Cloudflare Pages |

---

## Recommended layout for a Python package

Split the checks that run on every pull request from the release, so that
pull requests run with a read-only token and never show permanently "skipped"
jobs. Two caller workflows per project:

```yaml
# .github/workflows/pr.yml - runs on every pull request, read-only
name: CI

on:
  pull_request:

permissions:
  contents: read
  checks: write

# One run per PR; a new push cancels the superseded run.
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  python:
    uses: steamwiz/actions/.github/workflows/python-ci.yml@v1
    with:
      python-version: '3.13'
      source-dir: mypackage
      coverage-min: 95
```

```yaml
# .github/workflows/ci.yml - manual release, run from `main`
# The file name matters: PyPI trusted publishing is registered against it.
name: Release

on:
  workflow_dispatch:
    inputs:
      release-level:
        description: "Force a release at this level, or leave empty for commit-driven"
        type: choice
        options: ['', patch, minor, major]
        default: ''

permissions:
  contents: read

# Never cancel a release part-way through.
concurrency:
  group: release
  cancel-in-progress: false

jobs:
  test:
    uses: steamwiz/actions/.github/workflows/python-ci.yml@v1
    permissions:
      contents: read
      checks: write
    with:
      python-version: '3.13'
      source-dir: mypackage
      coverage-min: 95

  release:
    needs: test
    uses: steamwiz/actions/.github/workflows/python-release.yml@v1
    permissions:
      contents: write
      issues: write
      pull-requests: write
    with:
      python-version: '3.13'
      release-level: ${{ inputs.release-level }}
    secrets:
      APP_ID: ${{ secrets.APP_ID }}
      APP_PRIVATE_KEY: ${{ secrets.APP_PRIVATE_KEY }}

  build:
    needs: release
    if: needs.release.outputs.released == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ needs.release.outputs.tag }}
          persist-credentials: false
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      - run: pip install "poetry==2.*"
      - run: poetry install --no-root
      - run: poetry build
      - uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 30

  publish:
    needs: build
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/download-artifact@v4
        with:
          name: dist
          path: dist/
      - uses: pypa/gh-action-pypi-publish@release/v1
```

To add a style check, add a job to `pr.yml` that calls `python-style.yml`.
Projects that do not want one simply omit it.

---

## `python-ci.yml`

Runs the test suite under coverage (job **Test**) and enforces the coverage
threshold (job **Coverage**). Needs only `contents: read` and `checks: write`.
The coverage table is added to the run summary.

| Input | Type | Default | Description |
|---|---|---|---|
| `python-version` | string | `'3.13'` | Python version for `actions/setup-python` |
| `source-dir` | string | `''` | Package measured for coverage. Defaults to the repo name with hyphens to underscores. |
| `coverage-min` | number | `80` | Minimum coverage %; the Coverage job fails if below |

No secrets, no outputs.

---

## `python-style.yml`

Runs pycodestyle (job **Style**). Only call it if you want the check.

| Input | Type | Default | Description |
|---|---|---|---|
| `python-version` | string | `'3.13'` | Python version for `actions/setup-python` |
| `source-dir` | string | `''` | Package to check. Defaults to the repo name with hyphens to underscores. |
| `style-dirs` | string | `'test'` | Space-separated extra directories to check (missing ones are skipped) |

---

## `python-release.yml`

Runs python-semantic-release: bumps the version, tags, pushes and creates the
GitHub Release. Refuses to run on any ref other than `main`, so dispatching the
caller from a branch is a safe dry run. Needs the permissions shown in the
example above.

| Input | Type | Default | Description |
|---|---|---|---|
| `python-version` | string | `'3.13'` | Python version for `actions/setup-python` |
| `release-level` | string | `''` | `patch`, `minor` or `major` to force a level; anything else non-empty is rejected |

| Secret | Required | Description |
|---|---|---|
| `APP_ID` / `APP_PRIVATE_KEY` | Yes | steamwiz-releasebot GitHub App credentials |

| Output | Description |
|---|---|
| `version` | Released version (e.g. `1.4.2`), or empty |
| `released` | `'true'` if a release occurred, `'false'` otherwise |
| `tag` | Git tag created (e.g. `v1.4.2`), or empty |

The `pyproject.toml` configuration it expects is described under
[`python-pipeline.yml`](#pyprojecttoml-configuration-required) below and is unchanged.

---

## `python-pipeline.yml` (deprecated)

> Use `python-ci.yml`, `python-style.yml` and `python-release.yml` instead.
> This workflow bundles the release job with the test jobs, so every caller,
> including pull-request runs, must grant write permissions, and Release/Style
> show up as skipped on every PR. It is unchanged and will be removed in v2.


Full CI/CD pipeline: install → test → coverage → style → release → build.

PyPI publish is **not** included; see [PyPI Publish Pattern](#pypi-publish-pattern).

### Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `python-version` | string | `'3.13'` | Python version for `actions/setup-python` |
| `source-dir` | string | `''` | Source package directory. Defaults to repo name with hyphens → underscores. |
| `coverage-min` | number | `80` | Minimum coverage %; fails if below |
| `style-dirs` | string | `'test'` | Space-separated extra dirs for pycodestyle (beyond `source-dir`) |
| `do-pytest` | boolean | `true` | `false` to skip pytest and coverage |
| `do-coverage` | boolean | `true` | `false` to skip coverage check (pytest still runs) |
| `do-style` | boolean | `true` | `false` to skip pycodestyle |
| `do-release` | boolean | `true` | `false` to skip the release job |
| `release-level` | string | `''` | `patch`, `minor`, or `major` to force a release at that level |

### Secrets

| Secret | Required | Description |
|---|---|---|
| `GH_TOKEN` | Yes (release only) | GitHub token with `contents: write`, `issues: write` for python-semantic-release |

Pass via `secrets: inherit` from the caller.

### Outputs

| Output | Description |
|---|---|
| `version` | Released version string (e.g. `1.4.2`), or empty |
| `released` | `'true'` if a release occurred, `'false'` otherwise |
| `tag` | Git tag created (e.g. `v1.4.2`), or empty |

### Minimal caller example

```yaml
# .github/workflows/pipeline.yml
name: Pipeline

on:
  push:
    branches: [main]
  pull_request:

jobs:
  python:
    uses: steamwiz/actions/.github/workflows/python-pipeline.yml@v1
    secrets: inherit
```

### Full caller example (with publish and docs)

```yaml
# .github/workflows/pipeline.yml
name: Pipeline

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:
    inputs:
      release-level:
        description: "Force release level (patch/minor/major/none)"
        required: false
        default: none

jobs:
  python:
    uses: steamwiz/actions/.github/workflows/python-pipeline.yml@v1
    with:
      python-version: '3.13'
      coverage-min: 96
      do-release: ${{ github.event_name != 'workflow_dispatch' || inputs.release-level != 'none' }}
      release-level: ${{ github.event_name == 'workflow_dispatch' && inputs.release-level != 'none' && inputs.release-level || '' }}
    secrets: inherit

  publish:
    needs: python
    if: needs.python.outputs.released == 'true'
    uses: ./.github/workflows/publish.yml
    secrets: inherit

  build-docs:
    uses: steamwiz/actions/.github/workflows/mdbook-build.yml@v1

  deploy-docs:
    needs: [python, build-docs]
    if: github.ref == 'refs/heads/main'
    uses: steamwiz/actions/.github/workflows/cloudflare-deploy.yml@v1
    with:
      cloudflare-project-name: my-project
      directory: html
    secrets: inherit
```

### `pyproject.toml` configuration required

Projects must include this block (or equivalent):

```toml
[tool.semantic_release]
tag_format = "v{version}"
version_toml = ["pyproject.toml:tool.poetry.version"]
build_command = false

[tool.semantic_release.branches.main]
match = "main"
prerelease = false

[tool.semantic_release.remote.token]
env = "GH_TOKEN"

[tool.semantic_release.publish]
upload_to_vcs_release = false
```

Start with `version = "0.0.0"` in `[tool.poetry]`; python-semantic-release will manage it.

---

## `mdbook-build.yml`

Builds an mdBook site and uploads it as an artifact.

### Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `mdbook-version` | string | `'latest'` | mdBook version to install |
| `output-dir` | string | `'html'` | Build output directory (must match `book.toml`) |
| `artifact-name` | string | `'mdbook-site'` | Name of the uploaded artifact |
| `artifact-retention-days` | number | `7` | Artifact retention in days |

### Outputs

| Output | Description |
|---|---|
| `artifact-name` | The artifact name (for downstream reference) |

### Example

```yaml
build-docs:
  uses: steamwiz/actions/.github/workflows/mdbook-build.yml@v1
```

---

## `cloudflare-deploy.yml`

Downloads a static site artifact and deploys it to Cloudflare Pages using
`cloudflare/wrangler-action`.

### Inputs

| Input | Type | Default | Description |
|---|---|---|---|
| `cloudflare-project-name` | string | — **(required)** | Cloudflare Pages project name |
| `artifact-name` | string | `'mdbook-site'` | Artifact to download and deploy |
| `directory` | string | `'html'` | Subdirectory within the artifact to deploy |

### Secrets

| Secret | Required | Description |
|---|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Yes | Cloudflare account ID (32 hex chars) |
| `CLOUDFLARE_API_TOKEN` | Yes | API token with Pages edit permission |

### Example

```yaml
deploy-docs:
  needs: build-docs
  if: github.ref == 'refs/heads/main'
  uses: steamwiz/actions/.github/workflows/cloudflare-deploy.yml@v1
  with:
    cloudflare-project-name: my-project
    directory: html
  secrets: inherit
```

---

## PyPI Publish Pattern

PyPI's OIDC trusted publisher issues tokens per job, and PyPI matches the
**filename of the top-level (caller) workflow**, not of any reusable workflow it
calls. The shared library therefore does not include a publish workflow: the
`build` and `publish` jobs live in the project's own release workflow
(`.github/workflows/ci.yml`; see the layout example above).

Register a GitHub Actions trusted publisher on PyPI with:

| Field | Value |
|---|---|
| Owner | `steamwiz` |
| Repository | your project repo (e.g. `busy`) |
| Workflow filename | `ci.yml` (the workflow that contains the `publish` job) |
| Environment | `pypi` |

Create a GitHub Environment named `pypi` in the project repo settings.

> Renaming or moving the workflow that contains `publish` breaks publishing
> until the trusted publisher is re-registered on PyPI.

---

## Versioning

| Ref | Meaning |
|---|---|
| `@v1` | Floating major-version tag; always the latest `v1.x.y` |
| `@v1.2.3` | Pinned exact release |
| `@main` | HEAD; for testing only |

Pin callers to `@v1` for automatic non-breaking updates. Major version increments
only on breaking changes to workflow inputs or job structure.

## Action Pinning

All third-party actions are pinned to full-length commit SHAs. Dependabot keeps
these current via weekly PRs. See `SPEC.md §12` for the full pinning table.
