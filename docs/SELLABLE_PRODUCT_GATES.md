# Sellable product gates

## What PCS can plausibly sell first

A **fixed-scope computational assurance pilot**, delivered as a service-backed engagement using the PCS software.

The customer brings one bounded workflow and 3–10 scoped claims. PCS delivers a signed, replayable evidence bundle, human-readable report, assumptions/limitations statement, and technical review.

## Gate A — demo-ready

Current status: **substantially met**.

Requirements:

- coherent landing page;
- browser product demo;
- working CLI architecture;
- synthetic PK/PD reference case;
- signed package and external policy model;
- explicit non-claims.

## Gate B — design-partner-ready

Current status: **close, but external validation open**.

Required before describing the product as externally validated:

- one workflow supplied by someone outside the PCS development process;
- intake claim ledger frozen before seeing the result;
- clean-room replay by a second person/environment;
- integration time measured;
- missing adapters and manual steps recorded;
- customer/reviewer feedback captured.

## Gate C — paid-pilot-ready

Current status: **commercial operations open**.

Required:

- business entity/payment route;
- counsel-reviewed pilot/SOW/confidentiality/data-handling terms;
- signing-key custody procedure (engineering procedure/tooling implemented; real custody deployment still must be exercised);
- versioned release procedure;
- data deletion/retention process (hash-bound local plan/receipt tooling implemented; partner-specific contractual retention still must be agreed and exercised);
- incident/failure response;
- external workflow completed at least once;
- scope language that avoids regulatory/clinical overclaim.

A successful Lean kernel build is highly desirable but is **not** required to sell a computational-assurance pilot, provided the product accurately states that the Python replay checker is the executable TCB.

## Gate D — repeatable software product

Not yet met.

Additional requirements:

- multiple external workflows;
- stable adapter API;
- organization identity/RBAC;
- enterprise deployment story;
- durable audit storage;
- support/upgrade process;
- security review;
- repeatable pricing and buyer;
- stronger formal refinement between serialized certificate state, decision kernel, and Lean assurance judgment.

## Gate E — regulated/GxP product

Longer-term.

Requires domain-specific validation/quality work, customer quality-system integration, records/signature analysis, change control, and expert regulatory review. PCS must not imply that ordinary software verification automatically satisfies these obligations.
