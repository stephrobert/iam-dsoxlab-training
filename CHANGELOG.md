# Changelog

All notable changes to this catalog are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this catalog
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

**What a version means here.** A catalog is not a library: a MINOR bump adds
labs or changes what the repository promises, a PATCH fixes a statement or a
test without changing what a lab proves, and a MAJOR renames or removes labs,
which breaks the progress already recorded by learners.

## [0.2.2] - 2026-10-23

### Added

- A verdict can no longer be committed together with what it measures. The
  `verdicts-et-commun-separes` hook refuses a commit carrying
  `validation-labs.json` alongside anything the cycle plays:
  `challenge/tests/`, `setup.yaml`, `cleanup.yaml`, `lab.yaml` of any lab, and
  the shared tooling. It is itself tested, in both directions, by a hook of its
  own.

  This closes a case **no measurement can catch afterwards**. The staleness of
  a verdict used to be judged by comparing DATES, and that comparison was wrong
  in both directions on 2026-10-22: a correction committed together with the
  verdicts it invalidated passed as healthy, and labs re-attested on a branch
  came back "to be re-attested" after their squash merge, their content
  unchanged. When a squashed pull request touches a test *after* its campaign,
  the single commit carries both and the squash has destroyed what told them
  apart. It cannot be observed, so it is prevented.

  The statement stays allowed next to a verdict: it is not played by the cycle,
  and forbidding it would demand a campaign for a typo.

### Fixed

- `pipelineMustNotLeakSecretsInConfig` is removed from `.plumber.yaml`, where
  it was declared twice. Plumber dropped that control and answers "was removed
  and is now ignored: secret detection is no longer part of Plumber; remove
  this block". Keeping it suggested that secret detection was covered here. It
  is not, and `detect-private-key` is what comes closest, as a hook.

## [0.2.1] - 2026-10-19

### Changed

- **Every `doc_url` now points at `www.stephane-robert.info`.** The site moved
  from `blog.` to `www.`, and the old host redirects with a 301 to the same
  path. Nothing was broken: `validate-structure --check-urls` follows
  redirections, and this catalogue was green before a single line changed. The
  migration is housekeeping, not repair: a `doc_url` should point at the page
  rather than depend on a redirection that will be removed one day.

  The paths are identical between the two hosts, so only the host changed. The
  359 `doc_url` the catalogues declare were looked up in the site's own
  repository, offline: all of them exist there, including twenty-three pages
  the old host answered with a 404.

## [0.2.0] - 2026-10-17

### Changed

- **The validator reads the contract, not the terminal panel.**
  `scripts/valider-labs.py` parsed the score out of what `dsoxlab check`
  *displays*. That panel is interface: it changed in dsoxlab 0.4.0 and the
  regex stopped finding anything. It now reads `check --json`, which carries a
  `schema`, and the reading lives in `scripts/verdict_check.py`, **identical in
  all twelve catalogs**.

- **Three verdicts, not two.** A run where every collected test skipped
  measured nothing: it is **SKIP**, neither green nor red, and it stays to be
  measured. Painting it red would accuse the lab of what is missing from the
  machine. `--check` therefore exits `10` in that case, against `1` for a RED,
  mirroring `dsoxlab doctor --strict` where 9 is repaired and 10 is remeasured.

- **The README takes the reference structure** shared by the twelve catalogs:
  fourteen sections, in both languages. Seven of them describe dsoxlab rather
  than the subject, and are therefore identical everywhere.

### Requires

- **dsoxlab 0.4.1 or later**, which introduced the `status` field of
  `check --json`. Without it the validator refuses to conclude rather than
  guessing.

### Also

- le README annonçait « aucun lab n'est encore écrit » alors que le dépôt en porte seize.
