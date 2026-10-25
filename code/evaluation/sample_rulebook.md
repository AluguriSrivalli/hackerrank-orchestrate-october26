# Sample Output Rulebook — Ghost Data Still Exists

## Method and scope

This rulebook was written by inspecting all 32 rows in `dataset/sample_deletion_requests.csv` and their corresponding arrays in `dataset/sample_output.csv` before making further prediction-logic changes. It records observed benchmark conventions; sample labels are used for validation only and must not be embedded as case-specific prediction rules.

## Inferred global rules

1. **Status:** `NOT_APPLICABLE` is for requests that do not authorize deletion and must have no steps. `COMPLETE` uses only evidence-backed `VERIFICATION` steps. `INCOMPLETE` uses supported findings, a proposed remediation plan, and follow-up verification with blank evidence IDs for proposed work.
2. **Finding operations:** remaining prohibited copies use `REPORT_REMAINING_RECORD/PRESENT`; identifying fields in retained records use `REPORT_EXPOSED_PII/PRESENT`; active sync/import paths use `REPORT_ACTIVE_DATA_FLOW/ACTIVE`; unsafe backup eligibility uses `REPORT_RESTORE_RISK/ACTIVE`.
3. **Policy mapping:** full deletion maps to `DELETE_RECORD/ABSENT` then `VERIFY_RECORD_ABSENT`; retained support/audit/tombstone records map to redaction or presence verification; analytics/telemetry maps to anonymization; active flows map to disablement; unsafe backup restore maps to restore blocking.
4. **Ordering:** phases are ordered `FINDING` → `REMEDIATION` → `VERIFICATION`. Within each phase, operations follow the allowed operation order in the project contract; peers are ordered by `system_id`, then `resource_id`. `step_no` is assigned only after final ordering.
5. **Evidence:** findings must cite evidence. `COMPLETE` verification steps cite evidence proving the state at `audit_at`. Proposed remediation and follow-up verification in `INCOMPLETE` cases have `evidence_id: ""`. `reported_status` alone is not proof.
6. **Time:** evidence after `audit_at` cannot prove historical state. It may help locate a resource to check, but its later state must not be backdated.
7. **Identity and ambiguity:** current and historical identifiers should be used. Resource ownership must be grounded in evidence; similar emails or coincidental batch timestamps are not sufficient to assign a record to a person.
8. **Tombstones:** retain the required stable internal reference but redact direct identifiers.
9. **Serialization:** exactly seven fields per step (`step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`); arrays are ordered, JSON-valid, and numbered consecutively.

## Case-by-case reverse engineering

### case_01 — COMPLETE (1 steps)

- **Request intent:** Hi, I haven’t used this account in years and would like it closed. Please remove the profile and the personal details attached to it.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_001` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_54`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_02 — COMPLETE (1 steps)

- **Request intent:** Intenté eliminar mi cuenta ayer, pero la página terminó mostrando un error. ¿Pueden comprobar si todavía queda algún dato y completar la eliminación si hace falta?
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_002` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_54`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_03 — COMPLETE (3 steps)

- **Request intent:** Je demande la suppression définitive du compte associé à cette adresse e-mail. Veuillez examiner les identifiants actuels et antérieurs conformément à votre procédure de confidentialité. Merci de confirmer le résultat une fois la vérification terminée.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_7566` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_94`.
  - **2. VERIFICATION / security_service / `audit_record_2016` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_94`.
  - **3. VERIFICATION / analytics_platform / `analytics_9406` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_94`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_04 — COMPLETE (2 steps)

- **Request intent:** I’m deleting my account. You can keep anonymous statistics, but nothing in analytics should still point back to me.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_004` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_54`.
  - **2. VERIFICATION / analytics_platform / `analytics_901` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_56`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_05 — INCOMPLETE (3 steps)

- **Request intent:** I deleted this account and received a confirmation, but the same email address is still recognized. Please remove any remaining copy of my profile.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / account_service / `account_005` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_54`.
  - **2. REMEDIATION / account_service / `account_005` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_005` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_06 — INCOMPLETE (4 steps)

- **Request intent:** My account page is gone, but my old profile still appears when I search for it. Can you remove that search result too?
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_001` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_57`.
  - **2. REMEDIATION / search_service / `search_001` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_006` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / search_service / `search_001` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_07 — INCOMPLETE (4 steps)

- **Request intent:** Please delete my account and the identity document I sent to support while resolving a delivery issue.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / support_platform / `support_001` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_58`.
  - **2. REMEDIATION / support_platform / `support_001` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_007` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / support_platform / `support_001` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_08 — INCOMPLETE (4 steps)

- **Request intent:** I closed my account, but an old “download your data” link still works. Please delete that export file as well.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / export_service / `export_001` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_59`.
  - **2. REMEDIATION / export_service / `export_001` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_008` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / export_service / `export_001` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_09 — INCOMPLETE (5 steps)

- **Request intent:** Please permanently delete the account associated with this email address. Please apply the correct treatment to records covered by the request. Please confirm when the review is complete.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / backup_service / `backup_4978` / `REPORT_RESTORE_RISK` / `ACTIVE`** — A backup/restore path remains eligible and could reintroduce deleted data. Evidence: `evidence_93`.
  - **2. REMEDIATION / backup_service / `backup_4978` / `BLOCK_RESTORE` / `BLOCKED`** — Block the unsafe restore path before relying on downstream deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_3960` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / security_service / `audit_record_4902` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / backup_service / `backup_4978` / `VERIFY_RESTORE_BLOCKED` / `BLOCKED`** — Verify that the backup cannot restore deleted data. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_10 — INCOMPLETE (4 steps)

- **Request intent:** I used this Yahoo address before changing the email on my account. Please remove records linked to both the old and current addresses.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / support_platform / `support_002` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_61`.
  - **2. REMEDIATION / support_platform / `support_002` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_010` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / support_platform / `support_002` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_11 — INCOMPLETE (14 steps)

- **Request intent:** I would like the account associated with this address to be erased. Please handle any copies that fall within the scope of the deletion request. Please contact me if you need information to verify the request.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_052` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_03`.
  - **2. FINDING / analytics_platform / `analytics_2034` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_03`.
  - **3. FINDING / support_platform / `support_864` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_03`.
  - **4. FINDING / integration_service / `data_flow_9522` / `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE`** — An active sync/import/connector can recreate prohibited data and must be stopped before dependent record cleanup. Evidence: `evidence_03`.
  - **5. REMEDIATION / integration_service / `data_flow_9522` / `DISABLE_DATA_FLOW` / `DISABLED`** — Remediate the recreation path before deleting downstream copies. Evidence: `(blank: proposed work)`.
  - **6. REMEDIATION / search_service / `search_052` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **7. REMEDIATION / support_platform / `support_864` / `REDACT_RECORD` / `REDACTED`** — Retain the record but remove identifying fields required by policy. Evidence: `(blank: proposed work)`.
  - **8. REMEDIATION / analytics_platform / `analytics_2034` / `ANONYMIZE_RECORD` / `ANONYMIZED`** — Retain the analytics/telemetry record only after irreversibly unlinking it from the subject. Evidence: `(blank: proposed work)`.
  - **9. VERIFICATION / account_service / `account_4248` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **10. VERIFICATION / search_service / `search_052` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **11. VERIFICATION / security_service / `audit_record_9394` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **12. VERIFICATION / support_platform / `support_864` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `(blank: proposed work)`.
  - **13. VERIFICATION / analytics_platform / `analytics_2034` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `(blank: proposed work)`.
  - **14. VERIFICATION / integration_service / `data_flow_9522` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_12 — INCOMPLETE (5 steps)

- **Request intent:** I changed the email on this account before deleting it. Please check that nothing tied to the old address was left behind, even in systems that do not display the email.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / analytics_platform / `analytics_9914` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_01`.
  - **2. REMEDIATION / analytics_platform / `analytics_9914` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_9797` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / analytics_platform / `analytics_9914` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / security_service / `audit_record_2945` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_13 — INCOMPLETE (8 steps)

- **Request intent:** Please close my account and process the associated personal-data deletion. Please check the records connected to the account before confirming completion. Please contact me if you need information to verify the request.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_1308` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_03`.
  - **2. FINDING / support_platform / `support_4218` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_03`.
  - **3. REMEDIATION / search_service / `search_1308` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / support_platform / `support_4218` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_9335` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / search_service / `search_1308` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / support_platform / `support_4218` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **8. VERIFICATION / security_service / `audit_record_4816` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_14 — INCOMPLETE (5 steps)

- **Request intent:** このメールアドレスに関連するアカウントの完全な削除を依頼します。 プライバシー手続きに従い、現在および過去の識別情報を確認してください。 確認が完了したら結果をお知らせください。
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / backup_service / `backup_3870` / `REPORT_RESTORE_RISK` / `ACTIVE`** — A backup/restore path remains eligible and could reintroduce deleted data. Evidence: `evidence_03`.
  - **2. REMEDIATION / backup_service / `backup_3870` / `BLOCK_RESTORE` / `BLOCKED`** — Block the unsafe restore path before relying on downstream deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_3677` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / security_service / `audit_record_987` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / backup_service / `backup_3870` / `VERIFY_RESTORE_BLOCKED` / `BLOCKED`** — Verify that the backup cannot restore deleted data. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_15 — INCOMPLETE (5 steps)

- **Request intent:** I disconnected my account last week, but one of the integrations still seems active. Close the account completely and make sure it can no longer send my data to other systems.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / integration_service / `data_flow_9846` / `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE`** — An active sync/import/connector can recreate prohibited data and must be stopped before dependent record cleanup. Evidence: `evidence_01`.
  - **2. REMEDIATION / integration_service / `data_flow_9846` / `DISABLE_DATA_FLOW` / `DISABLED`** — Remediate the recreation path before deleting downstream copies. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_4745` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / security_service / `audit_record_1596` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / integration_service / `data_flow_9846` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_16 — INCOMPLETE (7 steps)

- **Request intent:** Please treat this message as a request for permanent account deletion. Please include information linked through current or earlier account identifiers. A short confirmation when the process is complete is sufficient.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / account_service / `account_994` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_05`.
  - **2. FINDING / search_service / `search_1007` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_05`.
  - **3. REMEDIATION / account_service / `account_994` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / search_service / `search_1007` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_994` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / search_service / `search_1007` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / security_service / `audit_record_9528` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_17 — INCOMPLETE (5 steps)

- **Request intent:** I want to close this account permanently. You may retain backups if required, but they must not be able to restore my personal profile.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / backup_service / `backup_3245` / `REPORT_RESTORE_RISK` / `ACTIVE`** — A backup/restore path remains eligible and could reintroduce deleted data. Evidence: `evidence_01`.
  - **2. REMEDIATION / backup_service / `backup_3245` / `BLOCK_RESTORE` / `BLOCKED`** — Block the unsafe restore path before relying on downstream deletion. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_4092` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / security_service / `audit_record_1797` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / backup_service / `backup_3245` / `VERIFY_RESTORE_BLOCKED` / `BLOCKED`** — Verify that the backup cannot restore deleted data. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_18 — INCOMPLETE (14 steps)

- **Request intent:** I am asking you to remove my account and the personal information linked to it. Please review any identifiers connected to this account as part of the request. Please let me know once the request has been reviewed.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_4013` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_94`.
  - **2. FINDING / analytics_platform / `analytics_037` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_94`.
  - **3. FINDING / support_platform / `support_5569` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_94`.
  - **4. FINDING / integration_service / `data_flow_4890` / `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE`** — An active sync/import/connector can recreate prohibited data and must be stopped before dependent record cleanup. Evidence: `evidence_94`.
  - **5. REMEDIATION / integration_service / `data_flow_4890` / `DISABLE_DATA_FLOW` / `DISABLED`** — Remediate the recreation path before deleting downstream copies. Evidence: `(blank: proposed work)`.
  - **6. REMEDIATION / search_service / `search_4013` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **7. REMEDIATION / support_platform / `support_5569` / `REDACT_RECORD` / `REDACTED`** — Retain the record but remove identifying fields required by policy. Evidence: `(blank: proposed work)`.
  - **8. REMEDIATION / analytics_platform / `analytics_037` / `ANONYMIZE_RECORD` / `ANONYMIZED`** — Retain the analytics/telemetry record only after irreversibly unlinking it from the subject. Evidence: `(blank: proposed work)`.
  - **9. VERIFICATION / account_service / `account_5521` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **10. VERIFICATION / search_service / `search_4013` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **11. VERIFICATION / security_service / `audit_record_6645` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **12. VERIFICATION / support_platform / `support_5569` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `(blank: proposed work)`.
  - **13. VERIFICATION / analytics_platform / `analytics_037` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `(blank: proposed work)`.
  - **14. VERIFICATION / integration_service / `data_flow_4890` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_19 — INCOMPLETE (8 steps)

- **Request intent:** Please remove my profile and clean my personal details out of earlier support conversations. Some of those messages also relate to another customer, so the conversation itself may need to stay.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_6083` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_01`.
  - **2. FINDING / support_platform / `support_9553` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_01`.
  - **3. REMEDIATION / search_service / `search_6083` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / support_platform / `support_9553` / `REDACT_RECORD` / `REDACTED`** — Retain the record but remove identifying fields required by policy. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_9102` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / search_service / `search_6083` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / security_service / `audit_record_6793` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **8. VERIFICATION / support_platform / `support_9553` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_20 — INCOMPLETE (8 steps)

- **Request intent:** Please treat this message as a request for permanent account deletion. Please check the records connected to the account before confirming completion. Please send a confirmation after the process finishes.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_4262` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_94`.
  - **2. FINDING / integration_service / `data_flow_1770` / `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE`** — An active sync/import/connector can recreate prohibited data and must be stopped before dependent record cleanup. Evidence: `evidence_94`.
  - **3. REMEDIATION / integration_service / `data_flow_1770` / `DISABLE_DATA_FLOW` / `DISABLED`** — Remediate the recreation path before deleting downstream copies. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / search_service / `search_4262` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_5037` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / search_service / `search_4262` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / security_service / `audit_record_5569` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **8. VERIFICATION / integration_service / `data_flow_1770` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_21 — COMPLETE (3 steps)

- **Request intent:** I deleted my account and received the confirmation email. Could you verify that the profile is gone and that anything retained for security is limited to what is required?
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_6440` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_92`.
  - **2. VERIFICATION / security_service / `audit_record_3737` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_92`.
  - **3. VERIFICATION / analytics_platform / `analytics_5335` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_92`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_22 — INCOMPLETE (8 steps)

- **Request intent:** Please erase the account linked to this email address. Please apply the correct treatment to records covered by the request. Please send a confirmation after the process finishes.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_8911` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_05`.
  - **2. FINDING / analytics_platform / `analytics_4440` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_05`.
  - **3. REMEDIATION / search_service / `search_8911` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / analytics_platform / `analytics_4440` / `ANONYMIZE_RECORD` / `ANONYMIZED`** — Retain the analytics/telemetry record only after irreversibly unlinking it from the subject. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_4990` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / search_service / `search_8911` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / security_service / `audit_record_3482` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **8. VERIFICATION / analytics_platform / `analytics_4440` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_23 — INCOMPLETE (8 steps)

- **Request intent:** Please delete this account, including the downloadable archive I requested earlier and any search result that still points to me. Security records can stay if policy requires them.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / export_service / `export_7364` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_92`.
  - **2. FINDING / search_service / `search_898` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_92`.
  - **3. REMEDIATION / export_service / `export_7364` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / search_service / `search_898` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_410` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / export_service / `export_7364` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / search_service / `search_898` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **8. VERIFICATION / security_service / `audit_record_4128` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_24 — INCOMPLETE (7 steps)

- **Request intent:** I was told that deletion was complete, but the account and its search result can still be found. Please investigate and finish the deletion.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / account_service / `account_5334` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_92`.
  - **2. FINDING / search_service / `search_5577` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_92`.
  - **3. REMEDIATION / account_service / `account_5334` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **4. REMEDIATION / search_service / `search_5577` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / account_service / `account_5334` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **6. VERIFICATION / search_service / `search_5577` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **7. VERIFICATION / security_service / `audit_record_7095` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_25 — COMPLETE (3 steps)

- **Request intent:** The privacy page still says my request failed. Please inspect the actual systems and tell me whether the account and identifiable analytics data have already been removed.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_3136` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_92`.
  - **2. VERIFICATION / security_service / `audit_record_451` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_92`.
  - **3. VERIFICATION / analytics_platform / `analytics_1895` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_92`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_26 — COMPLETE (6 steps)

- **Request intent:** I found an old report saying my account still existed. Please check the latest state and confirm that the profile is gone and that remaining records cannot identify me.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_5684` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_92`.
  - **2. VERIFICATION / security_service / `audit_record_5416` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_92`.
  - **3. VERIFICATION / support_platform / `support_4715` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `evidence_92`.
  - **4. VERIFICATION / analytics_platform / `analytics_4566` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_92`.
  - **5. VERIFICATION / integration_service / `data_flow_6244` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `evidence_92`.
  - **6. VERIFICATION / backup_service / `backup_3120` / `VERIFY_RESTORE_BLOCKED` / `BLOCKED`** — Verify that the backup cannot restore deleted data. Evidence: `evidence_92`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_27 — COMPLETE (6 steps)

- **Request intent:** Please audit the deletion as it stood when my request was reviewed. I want confirmation that the account was fully removed at that point.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_3866` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_92`.
  - **2. VERIFICATION / security_service / `audit_record_3830` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_92`.
  - **3. VERIFICATION / support_platform / `support_4707` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `evidence_92`.
  - **4. VERIFICATION / analytics_platform / `analytics_4574` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_92`.
  - **5. VERIFICATION / integration_service / `data_flow_2295` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `evidence_92`.
  - **6. VERIFICATION / backup_service / `backup_5970` / `VERIFY_RESTORE_BLOCKED` / `BLOCKED`** — Verify that the backup cannot restore deleted data. Evidence: `evidence_92`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_28 — COMPLETE (6 steps)

- **Request intent:** Can you verify that my account was deleted? A search result with a similar email belongs to someone else, so please do not treat that record as mine.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_5482` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_92`.
  - **2. VERIFICATION / security_service / `audit_record_9265` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_92`.
  - **3. VERIFICATION / support_platform / `support_2351` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `evidence_92`.
  - **4. VERIFICATION / analytics_platform / `analytics_6077` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `evidence_92`.
  - **5. VERIFICATION / integration_service / `data_flow_2337` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `evidence_92`.
  - **6. VERIFICATION / backup_service / `backup_838` / `VERIFY_RESTORE_BLOCKED` / `BLOCKED`** — Verify that the backup cannot restore deleted data. Evidence: `evidence_92`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_29 — INCOMPLETE (14 steps)

- **Request intent:** I used a different email on this account before changing it. Please remove records under both addresses and switch off any integration that could copy them back into search or analytics.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_1993` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_92`.
  - **2. FINDING / analytics_platform / `analytics_5208` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_92`.
  - **3. FINDING / support_platform / `support_5281` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_92`.
  - **4. FINDING / integration_service / `data_flow_3827` / `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE`** — An active sync/import/connector can recreate prohibited data and must be stopped before dependent record cleanup. Evidence: `evidence_92`.
  - **5. REMEDIATION / integration_service / `data_flow_3827` / `DISABLE_DATA_FLOW` / `DISABLED`** — Remediate the recreation path before deleting downstream copies. Evidence: `(blank: proposed work)`.
  - **6. REMEDIATION / search_service / `search_1993` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **7. REMEDIATION / support_platform / `support_5281` / `REDACT_RECORD` / `REDACTED`** — Retain the record but remove identifying fields required by policy. Evidence: `(blank: proposed work)`.
  - **8. REMEDIATION / analytics_platform / `analytics_5208` / `ANONYMIZE_RECORD` / `ANONYMIZED`** — Retain the analytics/telemetry record only after irreversibly unlinking it from the subject. Evidence: `(blank: proposed work)`.
  - **9. VERIFICATION / account_service / `account_7012` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **10. VERIFICATION / search_service / `search_1993` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **11. VERIFICATION / security_service / `audit_record_3954` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **12. VERIFICATION / support_platform / `support_5281` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `(blank: proposed work)`.
  - **13. VERIFICATION / analytics_platform / `analytics_5208` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `(blank: proposed work)`.
  - **14. VERIFICATION / integration_service / `data_flow_3827` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_30 — INCOMPLETE (14 steps)

- **Request intent:** I was told the account had been deleted, but I can still find traces in search, support, and analytics. Please handle them and disable any synchronization that could recreate them.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / search_service / `search_9359` / `REPORT_REMAINING_RECORD` / `PRESENT`** — A policy-governed record is still present, so the case needs a finding before deletion remediation. Evidence: `evidence_92`.
  - **2. FINDING / analytics_platform / `analytics_3697` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_92`.
  - **3. FINDING / support_platform / `support_6477` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_92`.
  - **4. FINDING / integration_service / `data_flow_8524` / `REPORT_ACTIVE_DATA_FLOW` / `ACTIVE`** — An active sync/import/connector can recreate prohibited data and must be stopped before dependent record cleanup. Evidence: `evidence_92`.
  - **5. REMEDIATION / integration_service / `data_flow_8524` / `DISABLE_DATA_FLOW` / `DISABLED`** — Remediate the recreation path before deleting downstream copies. Evidence: `(blank: proposed work)`.
  - **6. REMEDIATION / search_service / `search_9359` / `DELETE_RECORD` / `ABSENT`** — Remove the whole record because the policy treatment for this category is deletion. Evidence: `(blank: proposed work)`.
  - **7. REMEDIATION / support_platform / `support_6477` / `REDACT_RECORD` / `REDACTED`** — Retain the record but remove identifying fields required by policy. Evidence: `(blank: proposed work)`.
  - **8. REMEDIATION / analytics_platform / `analytics_3697` / `ANONYMIZE_RECORD` / `ANONYMIZED`** — Retain the analytics/telemetry record only after irreversibly unlinking it from the subject. Evidence: `(blank: proposed work)`.
  - **9. VERIFICATION / account_service / `account_4163` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **10. VERIFICATION / search_service / `search_9359` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **11. VERIFICATION / security_service / `audit_record_1707` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **12. VERIFICATION / support_platform / `support_6477` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `(blank: proposed work)`.
  - **13. VERIFICATION / analytics_platform / `analytics_3697` / `VERIFY_RECORD_ANONYMIZED` / `ANONYMIZED`** — Verify that retained analytics data can no longer be linked to the subject. Evidence: `(blank: proposed work)`.
  - **14. VERIFICATION / integration_service / `data_flow_8524` / `VERIFY_DATA_FLOW_DISABLED` / `DISABLED`** — Verify that the relevant recreation/synchronization path is inactive. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

### case_31 — COMPLETE (3 steps)

- **Request intent:** I no longer need this account. Please remove my name and contact details, but keeping an internal deleted-account reference is fine if other required records still depend on it.
- **Status rationale:** All supplied steps are evidence-backed verification checks and no finding/remediation is present, matching the sample’s complete-state pattern.
- **Expected steps and why they exist:**
  - **1. VERIFICATION / account_service / `account_4857` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `evidence_51`.
  - **2. VERIFICATION / security_service / `audit_record_6909` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `evidence_51`.
  - **3. VERIFICATION / identity_service / `tombstone_440` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `evidence_51`.
- **Ordering rationale:** Only verification is present, sorted by verification operation order and then system/resource.

### case_32 — INCOMPLETE (5 steps)

- **Request intent:** The account itself is gone, but an internal deleted-account record still shows my personal details. Please keep only the reference needed for retained records and remove the rest.
- **Status rationale:** The sample contains at least one supported finding and/or a proposed remediation, so the deletion remains incomplete until the remediation and verification pass.
- **Expected steps and why they exist:**
  - **1. FINDING / identity_service / `tombstone_9178` / `REPORT_EXPOSED_PII` / `PRESENT`** — A retained record still contains identifying data that policy requires to be removed or anonymized. Evidence: `evidence_51`.
  - **2. REMEDIATION / identity_service / `tombstone_9178` / `REDACT_RECORD` / `REDACTED`** — Retain the record but remove identifying fields required by policy. Evidence: `(blank: proposed work)`.
  - **3. VERIFICATION / account_service / `account_8858` / `VERIFY_RECORD_ABSENT` / `ABSENT`** — Verify the required deleted state for the account or record. Evidence: `(blank: proposed work)`.
  - **4. VERIFICATION / security_service / `audit_record_7068` / `VERIFY_RECORD_PRESENT` / `PRESENT`** — Verify a retained security/audit record that policy requires to remain available. Evidence: `(blank: proposed work)`.
  - **5. VERIFICATION / identity_service / `tombstone_9178` / `VERIFY_RECORD_REDACTED` / `REDACTED`** — Verify that a permitted retained record has had prohibited identifiers removed. Evidence: `(blank: proposed work)`.
- **Ordering rationale:** Findings come first, remediation follows, and verification comes last; within each phase the contract operation priority is applied, then system/resource ordering.

## Baseline mismatch root causes found during prediction comparison

These are diagnostic categories, not instructions to hardcode expected rows:
- **Evidence matching / ownership join:** some expected resources are present in participant-facing sources but the source record itself is de-identified. A resource can be linked to a subject in one time slice/source and have a separate readback in another; the implementation needs to propagate identity association by exact resource ID without using later state as historical proof.
- **Historical identifier/resource recovery:** the account readback may have an explicit 404 but no user fields. A subject-to-resource relationship can exist in another snapshot. The system should use the relationship to target the resource while only accepting the at-cutoff readback as state evidence.
- **Verification generation:** retained support messages that are already redacted still need a verification step when the record is authoritatively in scope; anonymized analytics records likewise need a verification step when the subject-to-resource link is authoritative.
- **Resource/system normalization:** attachment evidence may refer to a storage object while the sample treats the business record as a support attachment. Preserve the policy category but ensure system/resource mapping follows the explicit catalog and contract.
- **Evidence selection:** a newer observation should win if it changes state; authority ranking should only resolve equivalent-state duplicates or same-time observations, rather than allowing an older, less-current source to override a newer state change.
- **Unsubstantiated sample identifiers:** some expected account/audit resource IDs are not present in the participant-facing evidence found by exact resource-ID search. Do not manufacture links to make these cases match; report this as a dataset/evidence limitation and retain conservative output.

## Reproducibility

Run `python3 code/evaluation/main.py` for sample metrics, `python3 -m unittest discover -s code/evaluation -p 'test_*.py'` for regression tests, and `python3 code/main.py` to regenerate all 518 predictions. The rulebook is descriptive; prediction code must remain generalized and case-agnostic.
