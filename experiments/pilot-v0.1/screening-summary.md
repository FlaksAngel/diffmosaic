# Pilot v0.1 static eligibility screen

The screen uses DiffMosaic 0.7.0 `mutate-plan` with a pre-declared maximum of
20 candidates. It is a read-only operation over each exact `(base, head)`
pair. A source candidate is eligible for a mutation-adequacy experiment only
when the plan contains at least one supported diff-local mutation.

| Source candidate | Base / head | Planned sites | Decision | Raw plan |
| --- | --- | ---: | --- | --- |
| Click declaration order | `00e592c` / `047adef` | 0 | Excluded | `click-declaration-order-screening.json` |
| Flask IPv6 routing | `de8429f` / `7203fea` | 0 | Excluded | `flask-ipv6-routing-screening.json` |
| pytest exception chain | `a3a62a0` / `0d6fbde` | 0 | Excluded | `pytest-exception-chain-screening.json` |
| Flask automatic options | `d8eaaba` / `a82e942` | 2 | Study; result recorded | `flask-automatic-options-screening.json` |
| pytest option destination | `8d40684` / `532b201` | 2 | Excluded after baseline | `pytest-option-destination-screening.json` |

The first three records remain in `corpus/pilot-v0.1.json` with role
`excluded` and a specific reason. They must not be aggregated as observations
with zero mutation adequacy. The fourth record has a trusted image, a verified
baseline and a separate mutation execution report; it is the first `study`
subject, not an aggregate result. The fifth record is a second-community
source candidate excluded after its baseline exposed an untracked generated
source-file dependency under the clean archive model.
