# Partner Request Support workflows

The service helps reviewers decide whether a proposed institution already exists in CLARISA and gather evidence for handling a partner request. It offers a browser review workflow and a separate backend automatic-evaluation endpoint. It does not establish institutional eligibility through a score alone.

## Browser review

A reviewer signs in through CLARISA, then uploads the institution template or fetches pending requests. Spreadsheet upload creates upstream requests by default. Pending-request processing selects ten oldest requests at a time unless an API caller supplies explicit IDs.

Processing synchronizes the institution snapshot, reuses cached matches where available, and searches uncached names/acronyms. The reviewer can inspect candidate scores, translation metadata, and web research. Human accept/reject actions are separate requests that modify CLARISA using the signed-in user's token and identifier.

Manual labels are excellent (0.85+), good (0.70+), fair (0.60+), and no match below the accepted threshold. These are search-confidence aids for review, not automatic approval labels.

## Automatic evaluation

Integrators can call `/api/auto-partner-request` with institution metadata. It rejects near-certain or separately confirmed duplicates, otherwise uses web/rules evaluation to choose ACCEPT or MANUAL_REVIEW. The [API guide](API_GUIDE.md#automated-evaluation) defines exact boundaries, flags, and request fields.

Optional creation/response modes can modify CLARISA. MANUAL_REVIEW leaves the request pending and attempts requester/admin notification when configured. Auto-response disabled still permits model calls and notifications. Missing-field information is returned on the web/rules path; current implementation does not use completeness as an independent acceptance gate there.

## Continuing or operating the service

Use the [backend README](../backend/README.md), [frontend README](../frontend/README.md), and [design](HIGH_LEVEL_DESIGN.md) for setup and component responsibilities. Confirm the target branch/environment before testing; development and service-main use different cache tables and frontend environment destinations.

Live CLARISA, Supabase, AWS/OpenAI, S3, and optional email configuration are external dependencies. Local schema/offline checks do not validate institutional policy, provider accuracy, deployed authentication, or email delivery. The retained [rules reference](../backend/docs/CGIAR_INSTITUTION_RULES.md) provides business context and should be reconciled with the current policy owner when behavior requirements change.
