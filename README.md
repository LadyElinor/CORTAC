# CORTAC

Offline reference tools for **Warranted Agent Commonwealth design 0.2**. CORTAC checks synthetic role assignments and governance arithmetic, and prepares an evaluation scaffold for comparing agent teams.

**Current state: offline research software. No agents, credentials, grants, signing, live execution, or scored society study.** The included profile remains unratified with execution disabled. Software version `0.1.0` is separate from constitutional design version `0.2`.

## Start here

Python 3.10 or newer is required. The tools and tests use the Python standard library; installation and API keys are unnecessary.

From the repository root:

```sh
python scripts/verify.py
python scripts/wac.py validate-profile package/inputs/profile.extracted.json
python scripts/wac.py assemble --profile package/inputs/profile.extracted.json --roster package/fixtures/feasible.json
python scripts/wac.py verify --profile package/inputs/profile.extracted.json --roster package/fixtures/feasible.json --certificate package/results/feasible.json
python evaluation/readiness.py
```

On Windows, use `py -3` instead of `python`; on systems where Python 3 is named `python3`, use that name. Commands use repository-relative paths. The verification script also works when invoked by absolute path from another directory.

`verify.py` checks the delivered file inventories, runs all four test suites (121 tests at import), verifies the assignment witness, and confirms that both scored-study gates refuse with exit code 2. It exits nonzero on an unexpected result. It does not regenerate committed fixtures or result files. To retain a current machine-readable report:

```sh
python scripts/verify.py --report .local/verification.json
```

The captured repository-preparation results are in [docs/verification.json](docs/verification.json). They are a dated local observation, not a GitHub Actions run.

## Components

| Path | Purpose |
| --- | --- |
| [`package/wac_offline/`](package/wac_offline/) | Profile checking, joint case-and-appeal assignment search, witness verification, exact rational votes and splits |
| [`package/fixtures/`](package/fixtures/) | Declared synthetic rosters and governance inputs |
| [`evaluation/`](evaluation/) | Exposed scenarios, proposed arms and budgets, metrics, fabricated analysis smoke data, and readiness gates |
| [`verification/`](verification/) | Additional adversarial checks and preserved incoming verification records |
| [`scripts/`](scripts/) | Root-level CLI and complete verification entry points |
| [`provenance/import.json`](provenance/import.json) | Input ZIP identity and scope of repository preparation |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Automated checks and installed-package smoke test |

Read the [offline-tool contract](package/README.md) and [evaluation contract](evaluation/README.md) for supported fields, assumptions, status semantics, and regeneration commands. The original `START_HERE.txt` and component reports are retained as import records.

## What a successful check means

The assignment search finds a witness or reports `INFEASIBLE` or `SEARCH_INCOMPLETE` within its supplied finite model. Controllers, capacity, competence, and independence are declared synthetic inputs. A witness does not authenticate those declarations, perform the charter's uniform domain-first lottery, or appoint anyone.

CLI semantic reports can have exit code 0 even when their status is `INFEASIBLE`, `SEARCH_INCOMPLETE`, or `INVALID_WITNESS`. Consumers must inspect the JSON status. The root verification command checks the expected status as well as the process exit code.

The evaluation scaffold contains **216 exposed examples** and proposes **540 main arm slots plus 80 matched ablation slots**. None has been executed as an agent trial. Its 62 fabricated equal-arm rows only exercise analysis plumbing. Public fixtures and evaluator keys are development material, not sealed holdouts.

These commands deliberately exit 2:

```sh
python evaluation/readiness.py --require-scored-ready
python evaluation/analyze.py --mode scored
```

A normal readiness check can exit 0 while reporting `SOURCE_GATED_NO_SCORED_RUN`: file integrity is not study readiness. This repository implements no real scored runner or trust verifier.

## Optional installation

To install only the `wac_offline` CLI package into a virtual environment:

```sh
python -m pip install .
wac-offline --help
```

The wheel includes the frozen profile baseline. Evaluation scripts, fixtures, and reports are used from the full repository checkout rather than installed by the wheel. Runtime dependencies are empty; building or installing may fetch the declared setuptools build dependency.

## Source and authority boundaries

This repository preserves the uploaded offline bundle's files byte-for-byte. The bundle contains labeled text exports of the charter/profile, not authenticated original source artifacts. Its original-artifact digest fields remain null. Repository preparation has not reclassified those exports, supplied signatures, or cleared adoption/readiness gates.

The five-function architecture comes from the WAC proposal associated with [Metanoia](https://github.com/LadyElinor/Metanoia) and [Adiona](https://github.com/LadyElinor/Adiona). CORTAC does not connect to either repository or claim compatibility with their live enforcement. No network or model API calls are made by the offline tools.

## Development and upload

- [Contributing and validation](CONTRIBUTING.md)
- [Upload to LadyElinor/CORTAC](docs/UPLOAD.md), including Windows PowerShell commands
- [Repository preparation record](docs/REPOSITORY_PREPARATION.md)

CI is supplied for Linux Python 3.10, 3.12 and 3.14, and Windows Python 3.12. Its workflow has read-only repository permissions and no publishing step. Remote CI results and branch protection are not established by this package.

No license was supplied in the input bundle or selected during preparation. No license grant is added here.
