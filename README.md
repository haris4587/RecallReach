# RecallReach

RecallReach is a standalone GenLayer Intelligent Contract for auditing product-recall communications to specified distributors and retailers. A manufacturer wallet locks the required action, affected wallet/batch pairs, deadline, and evidence cutoff. It posts notices per obligation. Each designated recipient can acknowledge the exact notice by its SHA-256 hash or attest, after the deadline, that the deadline was missed.

## Workflow

1. Deploy `contracts/recall_reach.py` in [GenLayer Studio](https://studio.genlayer.com/) with the built-in wallet, Normal (Full Consensus), and no constructor arguments.
2. Call `register_recall(reference, action, obligations_json, notice_window, evidence_window)` as the manufacturer. The obligations JSON is a list of `[recipient_wallet, batch_id]` pairs, with up to 20 unique pairs. Windows are seconds from registration with `0 < notice_window < evidence_window <= 7776000`. Use a different wallet for each independently controlled organization.
3. For each pair, the manufacturer calls `post_notice(recall_id, recipient, batch, text)`. A notice should explicitly name the batch and request the required action. The write returns the notice hash. The recipient calls `respond(recall_id, batch, notice_hash, kind, text)` with `RECEIVED` or `MISSED`. A denial can use an empty hash only if no notice exists at response time. Notice and response texts are limited to 2 KiB of UTF-8 each.
4. After the evidence cutoff, anyone can call `review(recall_id, recipient, batch)` for each pair. Once all reviews exist, call `finalize(recall_id)`. After an additional 24 hours, finalization can record unresolved reviews as unknown. `get_recall`, `get_obligation`, and `get_decision` expose the audit trail as JSON.

### Verdicts

| Outcome | Rule |
| --- | --- |
| VERIFIED | Every obligation has a timely posted notice and a timely authenticated acknowledgment, supported by validator classification. |
| PARTIAL | At least one obligation is verified and at least one is missed or unknown. |
| VIOLATION | No obligation is verified and at least one is missed through a late on-chain notice or a grounded recipient denial. |
| INCONCLUSIVE | Every obligation is unknown. This includes dispatch without acknowledgment, a late acknowledgment without proof of timely receipt, and unresolved evidence. |

## Consensus and trust

Leader and validators independently classify the same frozen, wallet-authenticated evidence with GenLayer’s [Equivalence Principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle). Each model must ground a positive finding in verbatim text. The contract checks each quotation and compares normalized statuses via strict equality. Different quotations supporting the same status are allowed. Batch coverage, sender identity, record bindings, and timing checks are deterministic. Model disagreement can prevent a review from reaching consensus. The review timeout permits an unknown outcome in that case.

Evidence is captured directly on-chain. A SHA-256 digest over canonical JSON binds each immutable notice, response, and decision. Canonical JSON uses sorted keys, compact separators and ASCII escaping. Decision receipts contain the policy hash and the hashes of evidence assessed. The public registry authenticates wallets. It relies on participants to verify organization ownership, register a complete recipient roster, and make truthful attestations. The verdict covers only this registered workflow and recorded evidence. Use synthetic or public data because submissions are public. Review results are advisory and make no finding about off-chain compliance or actual recall execution.

## Verification

Run `python -m unittest discover -s tests -v` for the local contract-logic tests. The test harness stubs the GenLayer runtime and model. Studio smoke evidence is recorded in [EVIDENCE.md](EVIDENCE.md).
