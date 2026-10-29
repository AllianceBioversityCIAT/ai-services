# Development and service-main differences

This is a review checklist for promoting documentation from `dev-partner-request-support` to `main-partner-request-support`. It records the comparison made while preparing this documentation, not a guarantee about future branch contents. Refresh references and inspect the complete incoming diff before integration.

## Differences to preserve

| Area | Development | Service-main |
| --- | --- | --- |
| Cache constant in `backend/src/supabase_client.py` | `partner_request_cache_test` | `partner_request_cache_prod` |
| Cache schema in `backend/sql/create_partner_cache_table.sql` | Test table and its indexes/trigger/comments | Production table and corresponding SQL objects |
| Default frontend CORS origin in `backend/api.py` | `https://d27ujrreorxaxf.cloudfront.net` | `https://d2xsau6p4hnevy.cloudfront.net` |
| Login base in `frontend/app/services/authService.ts` | `https://clarisatest-back.ciat.cgiar.org/auth` | `https://api.clarisa.cgiar.org/auth` |
| Badge in `frontend/app/components/Header.tsx` | Testing Environment | Production Environment |

Both CORS defaults also include localhost ports 3000/3001. `CORS_ORIGINS` can override the default. The cache table, login destination, and badge are code/SQL choices, not a unified environment toggle. `NEXT_PUBLIC_API_URL` changes backend calls only.

The previous service-main README also omitted a stale first-three-requests development note. Current development code defaults to ten oldest pending requests, not three. Verify the code after integration rather than restoring that historical limit. An observed backend `.gitignore` difference was only its final newline.

## Integration checklist

1. Let the maintainer integrate development into service-main locally, without pushing yet.
2. Compare service trees and the whole incoming diff. Check missing test/UI files, endpoint paths, and dependency declarations instead of assuming development equals production.
3. Preserve intended production constants/SQL, CORS, login destination, and badge. Verify whether both branches now include the same batch and automatic-evaluation logic.
4. Adapt README/setup/architecture prose that currently says development or names the test cache. Keep this comparison table useful rather than replacing both columns with production values.
5. Validate documentation and relevant behavior against the resulting branch. Report unresolved differences before a push.
6. The maintainer supervises pipelines and promotion through `staging`; completed service documentation accumulates there for the agreed consolidated PR to `main`.

The development and production GitHub workflows trigger Jenkins on pushes to their service branches and on manual dispatch, without a documentation path exclusion. A documentation-only push can start a pipeline. This guide does not authorize release merges, pushes, or deployment.
