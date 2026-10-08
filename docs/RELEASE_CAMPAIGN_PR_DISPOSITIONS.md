# PR reconciliation and private review record

Fetched all advertised heads, tags and PR-head refs. GitHub REST confirms the listed PRs remain open drafts. Integration uses fresh branches from the observed main heads. No original PR is closed or merged by this record.

| Repository / PR | Exact head | Capability | Disposition |
|---|---|---|---|
| proof-carrying-science #74 | `037c47a2e8c90cbef76093ec26b31b6ee7f088e0` | Fail-closed executable authority and claim binding | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science #78 | `794bca3e74847f95cd5efdc7105385a0d18cae2c` | Apache open-core release preparation and ProofLab | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science #79 | `3827b989852d825235d5432726633ca9442c2d62` | Semantic translation contract and Explanation IR | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science #80 | `d6e77de2bc38a818827e2f422a4ff88909a5333c` | Pinned semantic checker protocol and evaluation infrastructure | Protocol and evaluation integrated; formal semantic source overlay absent, so authoritative semantic check remains BLOCKED |
| proof-carrying-science #81 | `8a7b60f4d7935b522bb5e0317379442fe3c12950` | Historical disclosure audit tooling | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #81 | `9e282285c0bef9bf672ea8962180ce36968c1af3` | Public core source links | BLOCKED: source publication and separate website rights clearance have not occurred; public-link change withheld |
| proof-carrying-science-site #82 | `f86e9349eec2f8372d6edb4f330733b894ff5246` | Countermodel Lab | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #83 | `15f5655995d6d0319e8f65344a701262a0a25190` | Semantic demos, notebook and consented replay data | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #84 | `55fed6c2e46ad5825b04ce2032de2d7a72b11c44` | Semantic Gauntlet | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #85 | `553dece68cb3190da7832935a40e93d26a291d8b` | Evaluation firewall | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #86 | `3453a6bf73102423fb8559073418aac0f5b206c4` | Semantic Repair Lab | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #87 | `16112c855f83cec7346e2908795eed1a6bd10a61` | Model Foundry | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #88 | `3651b702b6a8286e917f1ba39ec397db8303a5a7` | Multi-Step Repair Planner | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |
| proof-carrying-science-site #89 | `b2dd8c1aa363e339d9846f848f67a25ee4f7a4b7` | Historical disclosure audit tooling | Equivalent functionality integrated on release/verified-integrated-campaign; proposed supersession after protected merge and review |

Core #74 is an ancestor of #78, #78 of #79 and #79 of #80. The latest stack was reconciled once, with #81 applied separately. Website #82–#88 includes reconstructed stacks: every added file from #82–#87 remains present in #88, and overlapping changes were reviewed and tested. Website #89 was applied separately. No reported Phase II-B CertiForge source or 527-case artifact appears in fetched heads/tags/PR refs. The fetched older kernel-compile branch is a PCS harness, not later CertiForge research.

Remote main observations:

- proof-carrying-science: `01ff72174cfbd6049485df2c07da6e32d38fa9eb`; GitHub visibility PRIVATE.
- proof-carrying-science-site: `edf23f36033b01b5c74bf0276fbacb0b379316cb`; GitHub visibility PRIVATE.
- certiforge: `13e90681f8db83416179d031e4167ed68d4e5dca`; GitHub visibility PRIVATE.

Core main has an active ruleset: no deletion/force push, PR thread resolution, linear history, and the required `Workers Builds: pcs-core-ci-only` check. Its approval count is zero. Website and CertiForge have no observed branch protection/rulesets. Actions administration and deployment endpoints returned 403 despite repository metadata advertising admin permission. No live deployment revision is established by these observations.

Protected merge, original-PR closure, public CI activation, tag creation and deployment remain separate operations. Skipped jobs are not validation evidence.
