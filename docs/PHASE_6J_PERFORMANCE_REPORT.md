# Phase 6J Performance Report

Updated: 2026-07-10

Measured with 25 iterations against local production QA unless stated.

| Boundary | Result | Budget |
|---|---:|---:|
| Anonymous account contract | 2,518 bytes | <= 12,000 bytes |
| Anonymous session HTTP p95 | 21.16 ms | <= 100 ms |
| Tenant preference save+read p95 | 18.99 ms | <= 50 ms |
| Phase 6I operations payload | 28,832 bytes | <= 30,000 bytes |
| Phase 6I operations p95 | 77.15 ms | <= 100 ms |
| Initial Analyst HTML | 86,251 bytes | <= 100,000 bytes |

The first preference iteration includes schema creation and reached 247.35 ms;
warm p50 was 14.66 ms. The initial implementation reran migrations for every
query and measured 103.40 ms p95. Connection closure and a thread-safe
path/schema initialization cache reduced p95 by about 82%.

Evidence: `review_workspace/phase6j_performance/summary.json`.
