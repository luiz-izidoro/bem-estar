# Compliance and repository hygiene

**Status:** reviewed 2026-10-26
**Scope:** repository content, documentation, history, workflows, dependencies and publication policy.

## Licensing

- Original code, documentation and assets are MIT licensed (see [`LICENSE`](../LICENSE)).
- License scope and third-party attribution are in [`NOTICE.md`](../NOTICE.md) and
  [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).
- No third-party source code, runtime image or database is vendored.
- Product names and trademarks are used descriptively; the project is independent and does not
  claim affiliation with Apple, Health Auto Export, MCP vendors or other services.

## Documentation and language

- Repository documentation, code comments, commit messages, API contracts and CLI output are in
  English.
- The dashboard and user-facing product strings are bilingual (PT-BR/EN) by design. Localized
  strings and their tests are product features, not documentation.
- Every document is listed in [`docs/README.md`](README.md); links are checked during review.

## Security and privacy

- No credentials, tokens, private keys, personal paths or real health exports are tracked.
- Secret scanning and push protection are enabled on GitHub.
- Private vulnerability reporting and a `SECURITY.md` disclosure process are in place.
- Raw health data stays local; public deployment guidance separates secrets from the repository.

## Dependency and release policy

- Routine Dependabot version PRs are disabled with `open-pull-requests-limit: 0` to avoid
  notification noise.
- Dependabot alerts and security updates remain enabled; security PRs have their own fixed limit.
- The project publishes **code only**: no GitHub Releases and no version tags.
- [`RELEASE-MANIFEST.md`](../RELEASE-MANIFEST.md) covers every tracked file except itself.

## CI and branch protection

- CI covers Python 3.12–3.14 and the dashboard build.
- CodeQL covers Python and JavaScript/TypeScript.
- `main` requires a pull request, linear history and the six CI/CodeQL checks.
- Force-push, branch deletion and direct pushes by administrators are blocked.

## Validation

```sh
uv sync --extra dev
make check
./scripts/verify_release.sh
```

The release gate runs lint, formatting, strict typing, architecture checks, tests, migrations and the
dashboard build. CI runs the same public gates on every push and pull request.

## Intentional exceptions

- PT-BR UI and localization tests are intentional.
- The project deliberately has no GitHub Release or tag artifacts.
- Runtime health data and production credentials are not part of this repository.
