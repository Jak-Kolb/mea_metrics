# Stage 6 verify matrix

host: JakPC (setsid-detached)  
started: 2026-09-22T16:41:49+00:00  
finished: 2026-09-22T17:03:37+00:00  
log: `reports/stage6/pipeline.log`

Rasters / regions were verified earlier on Mac (2026-09-19); correlograms → metrics → summary on jakpc.

| recording | rasters | regions | correlograms | metrics | summary |
|---|---|---|---|---|---|
| ER52_ImpactWithBicuculline | PASS | PASS | PASS | PASS | PASS |
| JMSM_ImpactWithoutBicuculline | PASS | PASS | PASS | PASS | PASS |
| SM_pHshock | PASS* | PASS | PASS | PASS | PASS |

\* SM_pHshock rasters: spike trains exact; `end_time_s` accepted within 1 sample after neo uint32 unwrap (`PORT_NOTES.md`).

## Peak counts (report-only under Jak gate)

Exact bars remain uniformity + leaderProb. Peak % vs `RecordingMetrics` (matrix vs column `smoothdata` ULPs):

| recording | peak-count match |
|---|---|
| ER52_ImpactWithBicuculline | 236327/238050 (**99.2762%**) |
| JMSM_ImpactWithoutBicuculline | 99560/110946 (**89.7373%**) |
| SM_pHshock | 180409/202300 (**89.1789%**) |

**Review-doc flag:** JMSM and SM_pHshock peak match ~89% vs ER52 ~99% under the same Jak gate — not a Stage 6 fail, but call out in the thorough review.
