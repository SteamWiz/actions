# Changelog

All notable changes to `steamwiz/actions` are documented here.

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
Releases are tagged as `v{major}.{minor}.{patch}` on the `main` branch.

<!-- releases will be appended below by the maintainer -->

## Unreleased

### Changed

- Bump the GitHub-owned actions in every workflow, including the deprecated
  `python-pipeline.yml`: `actions/checkout` v4 → v7, `actions/setup-python`
  v5 → v7, `actions/upload-artifact` v4 → v7, `actions/download-artifact`
  v4 → v8 and `actions/create-github-app-token` v1 → v3. All now run on
  Node 24 (self-hosted runners need Actions Runner 2.327.1 or later). No
  workflow inputs, outputs or secrets changed. `download-artifact` v8 fails
  the step on an artifact digest mismatch, where v4 only warned.
  `create-github-app-token` v3 logs a deprecation warning for the `app-id`
  input, which is still accepted.

### Fixed

- `cloudflare-deploy.yml` now downloads the artifact into `directory`
  (`download-artifact` `path: ${{ inputs.directory }}`), the same directory
  `wrangler pages deploy` deploys. Before, the artifact was extracted into the
  workspace root while the default `directory: html` pointed at a folder that
  did not exist, so `mdbook-build.yml` followed by `cloudflare-deploy.yml`
  with default inputs could not deploy. Callers passing `directory: .` or
  `directory: html` need no change. `directory` is no longer a subfolder
  inside the artifact: a caller whose custom artifact keeps the site in a
  subfolder and passes that subfolder's name would now deploy
  `<name>/` containing `<name>/`, and should upload the subfolder itself
  instead. README and SPEC examples no longer pass `directory: html` (it is
  the default).
- `test-shared-workflows.yml` `deploy-download` job now downloads exactly as
  `cloudflare-deploy.yml` does with default inputs and fails unless
  `html/index.html` exists, instead of accepting either layout.

### Added

- `test-shared-workflows.yml` self-test: runs `python-ci.yml`,
  `python-style.yml` and `mdbook-build.yml` from the pull-request branch
  against fixtures in `test/`, `pyproject.toml` and `book.toml`.
