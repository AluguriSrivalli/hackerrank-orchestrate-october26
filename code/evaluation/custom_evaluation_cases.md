# Additional Custom Evaluation Cases

These participant-created cases complement the 32 public benchmark rows. Cases A–C are synthetic regression scenarios, not copied expected answers; Case D is a targeted regression on an already-redacted retained record. They exercise edge cases from the project contract.

## Case A — Request does not authorize deletion

**Input:** “Please correct my shipping address; do not delete my account.”

**Expected:** `NOT_APPLICABLE` with an empty step array. Request classification must precede destructive actions.

**Covered by:** `test_non_request_is_not_applicable`.

## Case B — Cross-time identity link with historical readback

**Input evidence:** A pre-cutoff account readback for `account_7421` reports HTTP 404. A later snapshot associates `account_7421` with `user_7421` but reports the account active after the audit cutoff.

**Expected:** The resource association may be used to locate the earlier readback; the pre-cutoff record remains `ABSENT` evidence, while the later `ACTIVE` state must remain in the future-evidence bucket and must not override the historical result.

**Covered by:** `test_identity_link_propagates_to_time_separated_readback_without_backdating_state`.

## Case C — Ambiguous activity candidates

**Input evidence:** Two distinct analytics resources have `ANONYMIZE_RECORD` events inside the same reported-at window.

**Expected:** No resource is assigned from time proximity alone. The resolver returns no unique candidate, avoiding false identity attribution.

**Covered by:** `test_unique_activity_locator_refuses_ambiguous_resources`.

## Case D — Already-redacted retained support message

**Input evidence:** A support message is authoritatively linked to a subject, and all direct identifiers are already null/redacted at the cutoff.

**Expected:** No false exposed-PII finding; retain an evidence-backed `VERIFY_RECORD_REDACTED` step for the in-scope retained record.

**Covered by:** `test_already_redacted_support_record_keeps_verification_step`.
