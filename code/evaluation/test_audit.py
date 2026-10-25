"""Small deterministic regression tests for the deletion audit helpers.

Run from the repository root:
    python3 -m unittest code.evaluation.test_audit
"""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("deletion_audit", ROOT / "code" / "main.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)

class AuditRegressionTests(unittest.TestCase):
    def test_non_request_is_not_applicable(self):
        self.assertTrue(audit.is_nonrequest(
            "I still use this account, so please don't delete or change anything."
        ))

    def test_integration_resource_is_a_data_flow_not_an_export(self):
        self.assertEqual(
            audit.resource_category("integration_service",
                                    {"resource_id": "data_flow_42", "enabled": True},
                                    "service_exports connectors"),
            "DATA_FLOW",
        )

    def test_tombstone_is_retained_but_direct_identifiers_trigger_redaction(self):
        self.assertEqual(
            audit.resource_category("identity_service",
                                    {"resource_id": "tombstone_42", "user_id": "user_42"},
                                    "account tombstone"),
            "ACCOUNT_TOMBSTONE",
        )
        self.assertTrue(audit.has_pii(
            {"resource_id": "tombstone_42", "user_id": "user_42",
             "email": "person@example.com"},
            {"person@example.com", "user_42"},
        ))
        self.assertFalse(audit.has_pii(
            {"resource_id": "tombstone_42", "user_id": "user_42",
             "email": None, "phone": None, "email_hash": None},
            {"person@example.com", "user_42"},
        ))

    def test_restore_allowed_is_active(self):
        self.assertTrue(audit.active_bool({"restore_allowed": True}))
        self.assertFalse(audit.active_bool({"restore_allowed": False}))


    def test_active_status_string_is_active_data_flow(self):
        rec = {
            "category": "DATA_FLOW",
            "row": {"status": "ACTIVE", "_raw": "status=ACTIVE"},
        }
        self.assertEqual(audit.state_for(rec), "ACTIVE")


    def test_support_attachment_uses_delete_policy(self):
        self.assertEqual(
            audit.resource_category("support_platform",
                                    {"resource_id": "support_001"},
                                    "delivery_correction_attachment.pdf attachment"),
            "SUPPORT_ATTACHMENT",
        )

    def test_identity_link_parser_extracts_user_reference(self):
        links = audit.load_identity_links()
        self.assertIn("account_5762", links)
        self.assertEqual(links["account_5762"][0]["user_id"], "user_11")




    def test_resource_prefix_overrides_mixed_export_context(self):
        self.assertEqual(
            audit.system_from("", "service_exports account_service analytics_platform search_service search_1993"),
            "search_service",
        )

    def test_handover_explicit_category_is_preserved(self):
        self.assertEqual(
            audit.resource_category(
                "support_platform",
                {"resource_id": "support_4218", "category": "SUPPORT_ATTACHMENT", "status": "FOUND"},
                "customer_account_handover_20261001.txt",
            ),
            "SUPPORT_ATTACHMENT",
        )

    def test_active_handover_status_marks_data_flow_active(self):
        rec = {
            "category": "DATA_FLOW",
            "row": {"resource_id": "data_flow_9522", "status": "ACTIVE"},
        }
        self.assertEqual(audit.state_for(rec), "ACTIVE")

    def test_restore_candidate_without_block_is_active_risk(self):
        rec = {
            "category": "BACKUP_ARCHIVE",
            "row": {"resource_id": "backup_3245", "eligible": "true", "deletion_block": "false"},
        }
        self.assertEqual(audit.state_for(rec), "ACTIVE")

    def test_contact_lookup_is_secondary_identifier(self):
        self.assertEqual(
            audit.resource_category(
                "analytics_platform",
                {"resource_id": "analytics_9914", "event": "contact_lookup_completed"},
                "service_events.log",
            ),
            "SECONDARY_IDENTIFIER",
        )

    def test_later_evidence_is_only_a_followup_candidate(self):
        # Future evidence may identify resources for verification but must not
        # be allowed to change a point-in-time state through state_for itself.
        rec = {"category": "DATA_FLOW", "row": {"status": "ACTIVE"}}
        self.assertEqual(audit.state_for(rec), "ACTIVE")


    def test_structured_json_trace_resolves_subject_and_resource(self):
        records = audit.load_evidence()
        matching = [
            rec for rec in records
            if rec["resource_id"] == "audit_record_4902"
            and rec["system_id"] == "security_service"
        ]
        self.assertTrue(matching)
        self.assertTrue(any(
            rec["row"].get("subject_ref") == "user_61"
            and rec["row"].get("rows") == "1"
            for rec in matching
        ))

    def test_object_storage_resource_uses_attachment_policy(self):
        self.assertEqual(audit.system_from("", "delivery_confirmation object_19"), "object_storage")
        self.assertEqual(audit.resource_category("object_storage", {"resource_id": "object_19"},
                                                 "delivery_correction_attachment.pdf"),
                         "SUPPORT_ATTACHMENT")

    def test_same_time_evidence_prefers_structured_readback(self):
        log = {"kind": "log", "row": {"http_status": "404"},
               "source": "z.log", "evidence_id": "e2"}
        sql = {"kind": "sql", "row": {"resource_id": "account_1"},
               "source": "a.sql", "evidence_id": "e1"}
        self.assertGreater(audit.evidence_authority(sql), audit.evidence_authority(log))

    def test_authoritative_catalog_link_resolves_email_alias(self):
        _, _, by_user, email_users = audit.identity_index()
        self.assertIn("user_11", email_users.get("haruka.s1838@zoho.com", set()))
        self.assertIn("haruka.s1838@zoho.com", by_user.get("user_11", set()))

    def test_unique_activity_locator_refuses_ambiguous_resources(self):
        request = {"reported_at": "2026-08-27T08:54:00Z"}
        one = [{
            "event_type": "ANONYMIZE_RECORD", "target_system": "analytics_platform",
            "resource_id": "analytics_1234", "event_time": "2026-08-27T08:47:00Z",
        }]
        self.assertEqual(
            audit.unique_activity_resource(request, {"ANONYMIZE_RECORD"},
                                           "analytics_platform", 15, one),
            "analytics_1234",
        )
        two = one + [{
            "event_type": "ANONYMIZE_RECORD", "target_system": "analytics_platform",
            "resource_id": "analytics_5678", "event_time": "2026-08-27T08:48:00Z",
        }]
        self.assertIsNone(
            audit.unique_activity_resource(request, {"ANONYMIZE_RECORD"},
                                           "analytics_platform", 15, two),
        )

    def test_identity_link_propagates_to_time_separated_readback_without_backdating_state(self):
        cutoff = audit.parse_time("2026-09-15T12:00:00Z")
        history = [
            {
                "resource_id": "account_7421", "system_id": "account_service",
                "category": "USER_PROFILE",
                "row": {"resource_id": "account_7421", "status_code": 404, "profile": None},
                "time": audit.parse_time("2026-09-15T09:00:00Z"),
                "evidence_id": "evidence_old", "kind": "json", "source": "readback.json",
            },
            {
                "resource_id": "account_7421", "system_id": "account_service",
                "category": "USER_PROFILE",
                "row": {"resource_id": "account_7421", "customer_reference": "user_7421",
                        "account_status": "ACTIVE"},
                "time": audit.parse_time("2026-09-17T12:00:00Z"),
                "evidence_id": "evidence_future", "kind": "json", "source": "snapshot.json",
            },
            {
                "resource_id": "account_9999", "system_id": "account_service",
                "category": "USER_PROFILE",
                "row": {"resource_id": "account_9999", "status_code": 404},
                "time": audit.parse_time("2026-09-15T09:00:00Z"),
                "evidence_id": "evidence_other", "kind": "json", "source": "readback.json",
            },
        ]
        relevant, future = audit.evidence_for_identity(
            history, {"user_7421"}, "user_7421", cutoff
        )
        self.assertIn("evidence_old", {r["evidence_id"] for r in relevant})
        self.assertIn("evidence_future", {r["evidence_id"] for r in future})
        self.assertNotIn("evidence_other", {r["evidence_id"] for r in relevant})
        self.assertEqual(audit.state_for(relevant[0]), "ABSENT")

    def test_structured_absence_fields_override_generic_present_default(self):
        rec = {
            "category": "USER_PROFILE",
            "row": {
                "resource_id": "account_example",
                "rows": "0",
                "http_status": "404",
                "_raw": "profile_lookup_completed",
            },
        }
        self.assertEqual(audit.state_for(rec), "ABSENT")


    def test_authoritative_backup_catalog_evidence_wins_when_state_agrees(self):
        requests = audit.read_csv(audit.DATA / "sample_deletion_requests.csv")
        request = next(r for r in requests if r["case_id"] == "case_09")
        identities, audits, by_user, email_users = audit.identity_index()
        status, steps = audit.audit_case(request, audit.load_evidence(), by_user,
                                         email_users, identities, audits)
        finding = next(s for s in steps if s["operation"] == "REPORT_RESTORE_RISK")
        self.assertEqual(finding["evidence_id"], "evidence_93")

    def test_already_redacted_support_record_keeps_verification_step(self):
        requests = audit.read_csv(audit.DATA / "sample_deletion_requests.csv")
        request = next(r for r in requests if r["case_id"] == "case_26")
        identities, audits, by_user, email_users = audit.identity_index()
        status, steps = audit.audit_case(request, audit.load_evidence(), by_user,
                                         email_users, identities, audits)
        support_steps = [s for s in steps if s["resource_id"] == "support_4715"]
        self.assertEqual(len(support_steps), 1)
        self.assertEqual(support_steps[0]["operation"], "VERIFY_RECORD_REDACTED")
        self.assertEqual(support_steps[0]["state"], "REDACTED")


if __name__ == "__main__":
    unittest.main()
