# Phase2 source validation - pre-acquisition report

Date:2026-11-15. State: **awaiting explicit user approval of acquisition manifest**. No external NASA, mirror, metadata, HEAD, Range or documentation request was made during preparation. The review used existing local source assessment, prior pilot metrics and cached availability only. The loopback automated test server is local, not an external acquisition.

## Review and exact acquisition proposal

Manifest ID: `PHASE2-2026-11-15-v1`. Readable plan: [PHASE2_ACQUISITION_MANIFEST.md](PHASE2_ACQUISITION_MANIFEST.md); machine-readable exact scope: [PHASE2_ACQUISITION_MANIFEST.json](PHASE2_ACQUISITION_MANIFEST.json). JSON SHA-256: `7ce2a1c5f9c18306a5190aaef92d63468fb43907eecdf3d96a60ee24eebdeb4e`.

24 source/date/bbox observation cases cover four SP source IDs, three NRT-family source IDs, South America/Africa/Australia/North America, high-latitude boreal Asia, split dateline selections, earlier NOAA-21 science-quality history and a known S-NPP outage control. SP windows are2023-09-01/2023-03-15 and2022-08-01 for the outage; fixed NRT date is2026-11-13. No rolling substitution, post-cessation S-NPP NRT, multi-year/global extraction or archive transport fallback is approved.

Three NASA metadata requests, three mirror metadata GETs, three mirror HEADs and at most32 bounded mirror Range GETs are separately listed. The total cap is65 external requests/128MiB transferred body bytes, with zero automatic redirects/retries. No whole-year mirror object is authorized. Missing/stale availability, unresolvable objects, required authorization, unsafe headroom or insufficient row-group budget stops the affected work and leaves it unverified. It does not authorize expanding the manifest.

Applicable credential: existing server-side FIRMS_MAP_KEY only. A local nonempty configuration value is present: **true**. This is a presence check, not proof of validity/access. No value was printed, copied into the manifest or sent externally. Anonymous mirror access only; no admin HTTP/API token, Earthdata/LAADS credentials, account provisioning or paid service is included.

## Verified now versus pending

| Finding | Current evidence/status |
| --- | --- |
| Prior offline ingestion review | Existing Phase1 metrics reviewed:34,044 selected local NRT records matched native row multiset; this is prior evidence, not Phase2 official/mirror validation. |
| Manifest arithmetic and allowlists |24 one-day cases, exact source/date/bbox templates and split dateline pairs validated;65-request total verified. |
| Credentials |Nonempty local key configuration only; secret value not exposed; external access not tested. |
| Existing software regressions |120 tests passed,0 failed,0 skipped;1 existing warning. |
| Preservation |All 98 protected backend/pipeline/experiment/data/handoff/archive files match pre-preparation checksums. Existing sample and pilot outputs preserved. |
| Fresh official availability, processing versions and acquisition metadata |Not requested; cached prior bounds are not current confirmation. |
| Official new observation bytes, native parity and normalization resource usage |Not acquired/not measured in Phase2. |
| Mirror object/schema/row availability, row agreement and publication lag |Not requested/not verified. |
| Nonempty dateline correctness, differences/gaps and exposure completeness |Pending approved acquisition; empty matches alone will not prove these. |

Exact comparison result file: [PHASE2_COMPARISON_RESULTS.json](PHASE2_COMPARISON_RESULTS.json). It deliberately has an empty results array,24 not_requested cases, verified=false flags, and null Phase2 measurements. No agreement/difference counts, observations or resource timings were fabricated.

## Current test evidence

Command: pytest `-q --tb=short -p no:cacheprovider --basetemp .tools/phase2-preapproval-tests`, with `FIRE_LIVE_TEST=1` and a temporary local Uvicorn process. Result: **120 passed,0 failed,0 skipped,1 existing Starlette/httpx deprecation warning in19.23seconds**. Existing NASA pipeline and offline pilot tests use fixtures/mocks, not external downloads. Complete output: [PHASE2_PREAPPROVAL_TEST_RESULTS.txt](PHASE2_PREAPPROVAL_TEST_RESULTS.txt).

These tests validate the unchanged existing software. They do not constitute new official NASA/mirror data-comparison evidence. No backend, regional scientific algorithm, security control, API contract, Gemini file or archive was changed. Only new Phase2 plan/status/test documents and ignored local test/snapshot files were created.

## Recommendation and approval gate

**NO-GO for the next global-scale pilot until Phase2 evidence exists.** This is a pending-evidence decision, not a finding that NASA or the mirror failed. On explicit manifest approval, acquire only listed eligible windows/objects under the budgets; preserve originals/checksums, compare per source/collection/actual row stream and measure actual performance/memory/storage. Publish verified mismatches/missing fields/version/coverage/freshness distinctions and unverified cases separately. Go requires trustworthy source identity, native-field parity and stream/coverage handling; partial mirror accessibility may justify another bounded pilot but never blanket mirror equivalence or bulk backfill.

The approval gate comes from the user's explicit instruction: 'Do not make external download requests until I explicitly approve that manifest.' No external acquisition will start before that approval. No deployment, commit or push occurred. Git metadata remains absent from this source export, so tracked/staged history cannot be certified.
