#!/usr/bin/env python3
"""Evidence-driven deletion audit for the Ghost Data Still Exists challenge.

Uses only Python's standard library. Run from repository root:
    python3 code/main.py
"""
from __future__ import annotations
import csv, json, re, sqlite3, io
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dataset"
EVIDENCE = DATA / "evidence"
OUT = ROOT / "output.csv"

PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
OP_ORDER = {
    "REPORT_REMAINING_RECORD": 0, "REPORT_EXPOSED_PII": 1,
    "REPORT_ACTIVE_DATA_FLOW": 2, "REPORT_RESTORE_RISK": 3,
    "DISABLE_DATA_FLOW": 0, "BLOCK_RESTORE": 1, "DELETE_RECORD": 2,
    "REDACT_RECORD": 3, "ANONYMIZE_RECORD": 4,
    "VERIFY_RECORD_ABSENT": 0, "VERIFY_RECORD_PRESENT": 1,
    "VERIFY_RECORD_REDACTED": 2, "VERIFY_RECORD_ANONYMIZED": 3,
    "VERIFY_DATA_FLOW_DISABLED": 4, "VERIFY_RESTORE_BLOCKED": 5,
}
EMAIL_RE = re.compile(r"[^@\s|,;<>]+@[^@\s|,;<>]+\.[^@\s|,;<>]+", re.I)
KV_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)=("[^"]*"|[^ ]+)')

def parse_time(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None

def norm(v):
    return str(v).strip().casefold() if v is not None else ""

def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def system_from(value, context=""):
    raw = str(value or "").casefold().strip()
    # Mixed-service exports place many service names in the parent object. Use
    # the concrete resource ID for this record before considering broad context.
    ids = re.findall(r"\b(account|search|analytics|support|export|backup|data_flow|audit_record|tombstone|marketing|email_delivery|cache|object)_\d+\b",
                     str(context or "").casefold())
    if ids:
        prefix = ids[-1]
        prefix_system = {
            "account": "account_service", "search": "search_service",
            "analytics": "analytics_platform", "support": "support_platform",
            "export": "export_service", "backup": "backup_service",
            "data_flow": "integration_service", "audit_record": "security_service",
            "tombstone": "identity_service", "marketing": "marketing_service",
            "email_delivery": "email_delivery_service", "cache": "cache_service",
        }.get(prefix)
        if prefix == "object":
            return "object_storage"
        if prefix_system:
            return prefix_system
    known = ("account_service", "search_service", "analytics_platform", "support_platform",
             "export_service", "integration_service", "backup_service", "security_service",
             "identity_service", "marketing_service", "email_delivery_service",
             "cache_service", "archive_service", "object_storage")
    if raw in known:
        return raw
    s = (raw + " " + str(context or "")).casefold()
    # Prefer the most specific service markers before broad words such as "account".
    for token, system in [
        ("email_delivery_service", "email_delivery_service"),
        ("analytics_platform", "analytics_platform"), ("customer_analytics", "analytics_platform"),
        ("product_telemetry", "analytics_platform"), ("telemetry", "analytics_platform"),
        ("search_service", "search_service"), ("customer_search", "search_service"),
        ("support_platform", "support_platform"), ("support_records", "support_platform"),
        ("integration_service", "integration_service"), ("connector", "integration_service"),
        ("backup_service", "backup_service"), ("backup", "backup_service"), ("restore", "backup_service"),
        ("security_service", "security_service"), ("security", "security_service"), ("audit_record", "security_service"),
        ("identity_service", "identity_service"), ("tombstone", "identity_service"),
        ("marketing_service", "marketing_service"), ("marketing", "marketing_service"),
        ("export_service", "export_service"), ("customer_exports", "export_service"), ("export", "export_service"),
        ("cache_service", "cache_service"), ("cache", "cache_service"),
        ("search", "search_service"), ("support", "support_platform"),
        ("profile", "account_service"), ("account_service", "account_service"), ("account", "account_service"),
        ("archive", "archive_service"),
    ]:
        if token in s:
            return system
    return "unknown_service"

def resource_category(system, row, context=""):
    txt = (str(context) + " " + " ".join(f"{k} {v}" for k,v in row.items())).casefold()
    # A contact-lookup/opt-in row is a direct contact identifier, not an analytics
    # profile; the policy requires deletion of the contact entry.
    event_name = str(row.get("event", "")).casefold()
    if system == "analytics_platform" and "contact_lookup" in event_name:
        return "SECONDARY_IDENTIFIER"
    explicit_category = str(row.get("category", row.get("data_category", ""))).strip().upper()
    valid_categories = {"USER_PROFILE", "SECONDARY_IDENTIFIER", "SEARCH_INDEX_ENTRY",
                        "CACHE_ENTRY", "SUPPORT_MESSAGE", "SUPPORT_ATTACHMENT",
                        "ANALYTICS_PROFILE", "PRODUCT_TELEMETRY", "USER_EXPORT",
                        "MARKETING_PROFILE", "EMAIL_DELIVERY_LOG", "SECURITY_AUDIT_LOG",
                        "LEGAL_HOLD_RECORD", "BACKUP_ARCHIVE", "ACCOUNT_TOMBSTONE", "DATA_FLOW"}
    if explicit_category in valid_categories:
        return explicit_category
    # Resource IDs are more specific than broad parent/table names in snapshot bundles.
    rid = str(row.get("resource_id", row.get("resourceId", ""))).casefold()
    prefix_categories = (
        ("tombstone_", "ACCOUNT_TOMBSTONE", "identity_service"),
        ("audit_record_", "SECURITY_AUDIT_LOG", "security_service"),
        ("data_flow_", "DATA_FLOW", "integration_service"),
        ("backup_", "BACKUP_ARCHIVE", "backup_service"),
        ("analytics_", "ANALYTICS_PROFILE", "analytics_platform"),
        ("search_", "SEARCH_INDEX_ENTRY", "search_service"),
        ("support_", "SUPPORT_MESSAGE", "support_platform"),
        ("export_", "USER_EXPORT", "export_service"),
        ("marketing_", "MARKETING_PROFILE", "marketing_service"),
        ("cache_", "CACHE_ENTRY", "cache_service"),
        ("object_", "SUPPORT_ATTACHMENT", "object_storage"),
        ("account_", "USER_PROFILE", "account_service"),
    )
    # A support resource explicitly described as an attachment follows the
    # attachment deletion rule even when its identifier uses the support_ prefix.
    if rid.startswith("support_") and "attachment" in txt:
        return "SUPPORT_ATTACHMENT"
    for prefix, category, prefix_system in prefix_categories:
        if rid.startswith(prefix):
            system = prefix_system
            return category
    # Exact system names prevent the generic root key "service_exports" from
    # misclassifying every connector as an export.
    if system == "integration_service": return "DATA_FLOW"
    if system == "identity_service": return "ACCOUNT_TOMBSTONE"
    if system == "email_delivery_service": return "EMAIL_DELIVERY_LOG"
    if system == "security_service": return "SECURITY_AUDIT_LOG"
    if system == "backup_service": return "BACKUP_ARCHIVE"
    if system == "analytics_platform": return "ANALYTICS_PROFILE"
    if system == "search_service": return "SEARCH_INDEX_ENTRY"
    if system == "support_platform":
        return "SUPPORT_ATTACHMENT" if "attachment" in txt else "SUPPORT_MESSAGE"
    if system == "export_service": return "USER_EXPORT"
    if system == "marketing_service": return "MARKETING_PROFILE"
    if system == "cache_service": return "CACHE_ENTRY"
    if system == "object_storage": return "SUPPORT_ATTACHMENT"
    if system == "account_service": return "USER_PROFILE"
    if "tombstone" in txt: return "ACCOUNT_TOMBSTONE"
    if "attachment" in txt: return "SUPPORT_ATTACHMENT"
    if "support" in txt: return "SUPPORT_MESSAGE"
    if "security" in txt or "audit_record" in txt: return "SECURITY_AUDIT_LOG"
    if "backup" in txt or "restore" in txt: return "BACKUP_ARCHIVE"
    if "analytics" in txt or "telemetry" in txt: return "ANALYTICS_PROFILE"
    if "search" in txt: return "SEARCH_INDEX_ENTRY"
    if "export" in txt: return "USER_EXPORT"
    if "marketing" in txt: return "MARKETING_PROFILE"
    if "delivery" in txt: return "EMAIL_DELIVERY_LOG"
    if "cache" in txt: return "CACHE_ENTRY"
    if "profile" in txt: return "USER_PROFILE"
    if "flow" in txt: return "DATA_FLOW"
    return "UNKNOWN"

def iter_dict_records(obj, context=""):
    """Yield dicts with resource ids, retaining a descriptive parent context."""
    if isinstance(obj, dict):
        metadata = " ".join(str(obj.get(k, "")) for k in
                            ("data_store", "collection", "origin_system", "system_id", "table_name", "service"))
        ctx = context + " " + " ".join(str(k) for k in obj.keys()) + " " + metadata
        if any(k in obj for k in ("resource_id", "resourceId")):
            yield obj, ctx
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                yield from iter_dict_records(v, ctx + " " + str(k))
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_dict_records(v, context)



_SYSTEM_ACTIVITY_CACHE = None

def system_activity_rows():
    """Load the activity ledger once; it is reused for identity and audit joins."""
    global _SYSTEM_ACTIVITY_CACHE
    if _SYSTEM_ACTIVITY_CACHE is None:
        _SYSTEM_ACTIVITY_CACHE = read_csv(DATA / "system_activity.csv")
    return _SYSTEM_ACTIVITY_CACHE


def load_identity_links():
    """Read explicit catalog links; links establish ownership, not record existence."""
    links = {}
    for row in system_activity_rows():
        if row.get("event_type") != "LINK_RESOURCE_IDENTITY":
            continue
        details = row.get("details", "")
        rid = row.get("resource_id", "")
        uid_match = re.search(r"\b(user_\d+)\b", details, re.I)
        emails = EMAIL_RE.findall(details)
        if not rid or not uid_match:
            continue
        links.setdefault(rid, []).append({
            "user_id": uid_match.group(1).casefold(),
            "email": norm(emails[0]) if emails else "",
            "activity_id": row.get("activity_id", ""),
            "event_time": parse_time(row.get("event_time")),
            "details": details,
        })
    return links


def load_evidence():
    manifest = {r["file_path"]: r for r in read_csv(DATA / "evidence_files.csv")}
    records = []
    for path in sorted(EVIDENCE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(DATA).as_posix()
        meta = manifest.get(rel, {})
        evidence_id = meta.get("file_id", "")
        captured = parse_time(meta.get("captured_at"))
        ext = path.suffix.lower()
        if ext == ".json":
            try:
                obj = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("snapshots"), list):
                for snap in obj["snapshots"]:
                    ds = str(snap.get("data_store", ""))
                    coll = str(snap.get("collection", ""))
                    if "account_service" in ds and "customer_profile" in coll:
                        st = parse_time(snap.get("captured_at")) or captured
                        records.append({"resource_id": "__snapshot__", "system_id": "account_service",
                                        "category": "USER_PROFILE", "row": {}, "context": coll + " " + rel,
                                        "evidence_id": evidence_id, "time": st, "source": rel, "kind": "snapshot"})
            for row, ctx in iter_dict_records(obj):
                rid = row.get("resource_id", row.get("resourceId"))
                if not rid: continue
                parent_system = row.get("data_store") or row.get("origin_system") or row.get("system_id")
                system = system_from(parent_system, ctx + " " + rel + " " + str(row.get("collection","")) + " " + str(rid))
                cat = resource_category(system, row, ctx + " " + rel)
                ts = parse_time(row.get("observed_at") or row.get("captured_at") or row.get("updated_at") or row.get("event_time")) or captured
                records.append({"resource_id": str(rid), "system_id": system, "category": cat,
                                "row": row, "context": ctx + " " + rel, "evidence_id": evidence_id,
                                "time": ts, "source": rel, "kind": "json"})
        elif ext == ".sql":
            # SQLite-compatible snapshots; run in isolated in-memory DB.
            con = sqlite3.connect(":memory:")
            try:
                con.executescript(path.read_text(encoding="utf-8", errors="replace"))
                tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                for table in tables:
                    if "customer_profile" in table.casefold():
                        records.append({"resource_id": "__snapshot__", "system_id": "account_service",
                                        "category": "USER_PROFILE", "row": {}, "context": table + " " + rel,
                                        "evidence_id": evidence_id, "time": captured, "source": rel, "kind": "snapshot"})
                for table in tables:
                    try:
                        cur = con.execute(f'SELECT * FROM "{table}"')
                        cols = [d[0] for d in cur.description]
                        for vals in cur.fetchall():
                            row = dict(zip(cols, vals))
                            # Nested record_json in replica snapshots.
                            if row.get("record_json"):
                                try:
                                    inner = json.loads(row["record_json"])
                                    row = {**row, **inner}
                                except Exception: pass
                            rid = row.get("resource_id")
                            if not rid: continue
                            system = system_from(row.get("origin_system") or row.get("data_store") or table, rel + " " + table + " " + str(rid))
                            cat = resource_category(system, row, table + " " + rel + " " + str(row.get("collection_name","")))
                            ts = captured or parse_time(row.get("updated_at") or row.get("captured_at"))
                            records.append({"resource_id": str(rid), "system_id": system, "category": cat,
                                            "row": row, "context": table + " " + rel, "evidence_id": evidence_id,
                                            "time": ts, "source": rel, "kind": "sql"})
                    except sqlite3.Error:
                        continue
            except sqlite3.Error:
                # Some evidence SQL contains dialect features; parse INSERT lines as fallback.
                pass
            finally:
                con.close()
        elif ext in (".log", ".txt", ".pdf", ".png", ".jpg", ".jpeg", ".webp"):
            text_blob = ""
            if ext in (".log", ".txt"):
                text_blob = path.read_text(encoding="utf-8", errors="replace")
            elif ext == ".pdf":
                try:
                    from pypdf import PdfReader
                    text_blob = "\\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
                except Exception:
                    text_blob = ""
            else:
                try:
                    from PIL import Image
                    import pytesseract
                    text_blob = pytesseract.image_to_string(Image.open(path))
                except Exception:
                    text_blob = ""
            if ext in (".pdf", ".png", ".jpg", ".jpeg", ".webp") and text_blob.strip():
                # OCR/PDF evidence often presents labels and values on separate lines.
                # When a document describes only a small number of resources, preserve
                # its resource/identifier association as a structured evidence record.
                doc_resources = sorted(set(re.findall(r"\b(?:account|search|support|export|backup|data_flow|analytics|audit_record|tombstone|cache|marketing|email_delivery|object)_\d+\b", text_blob, re.I)))
                doc_emails = sorted(set(norm(x) for x in EMAIL_RE.findall(text_blob)))
                if doc_resources:
                    # Do not discard multi-record documents. Associate each resource
                    # only with identifiers in its local text neighborhood; a document
                    # containing several users must not link every resource to every user.
                    lines = text_blob.splitlines()
                    for drid in doc_resources:
                        positions = [i for i, line in enumerate(lines)
                                     if re.search(r"\b" + re.escape(drid) + r"\b", line, re.I)]
                        snippets = []
                        for pos in positions:
                            snippets.extend(lines[max(0, pos-3):min(len(lines), pos+4)])
                        local_text = "\n".join(dict.fromkeys(snippets)) if snippets else text_blob
                        local_emails = sorted(set(norm(x) for x in EMAIL_RE.findall(local_text)))
                        local_user_ids = sorted(set(x.casefold() for x in
                            re.findall(r"\buser_\d+\b", local_text, re.I)))
                        ds = system_from("", rel + " " + drid)
                        dc = resource_category(ds, {"resource_id": drid}, rel + " " + local_text)
                        doc_row = {"resource_id": drid, "_raw": local_text}
                        if len(local_emails) == 1:
                            doc_row["email"] = local_emails[0]
                        if len(local_user_ids) == 1:
                            doc_row["user_id"] = local_user_ids[0]
                        records.append({"resource_id": drid, "system_id": ds, "category": dc,
                                        "row": doc_row, "context": local_text + " " + rel,
                                        "evidence_id": evidence_id, "time": captured, "source": rel, "kind": "document"})
            text_lines = text_blob.splitlines()
            def parse_event_line(line):
                # Support both key=value logs and timestamp-prefixed JSON events.
                # Return normalized event fields while leaving source text intact.
                json_start = line.find("{")
                if json_start >= 0:
                    try:
                        parsed = json.loads(line[json_start:])
                        if isinstance(parsed, dict):
                            return {str(k).casefold(): v for k, v in parsed.items()}
                    except Exception:
                        pass
                return {str(k).casefold(): v.strip('"') for k, v in KV_RE.findall(line)}
            trace_context = {}
            for raw_line in text_lines:
                raw_kv = parse_event_line(raw_line)
                trace_id = raw_kv.get("trace_id")
                if trace_id:
                    trace_context.setdefault(str(trace_id), {}).update(raw_kv)
            for line in text_lines:
                kv = parse_event_line(line)
                if kv.get("trace_id") is not None and str(kv["trace_id"]) in trace_context:
                    kv = {**trace_context[str(kv["trace_id"])], **kv}
                m = re.search(r'\b(resource_id|resource|target_resource)=([A-Za-z0-9_-]+)', line)
                rid = kv.get("resource_id") or kv.get("resource") or kv.get("target_resource")
                if not rid:
                    # Handover/catalog evidence uses pipe-separated fields and may
                    # identify a subject by internal user_id rather than email.
                    # Parse only rows whose resource field has a known resource-ID
                    # shape; this avoids treating arbitrary prose as records.
                    if "|" in line:
                        parts = [x.strip() for x in line.split("|")]
                        if (len(parts) >= 6 and
                            re.fullmatch(r"(?:account|search|support|export|backup|data_flow|analytics|audit_record|tombstone|cache|marketing|email_delivery|object)_\d+", parts[2], re.I)):
                            kv = {"event_time":parts[0].lstrip("- ").strip(), "system":parts[1],
                                  "resource_id":parts[2], "category":parts[3],
                                  "status":parts[4], "identifier":parts[5]}
                            rid = parts[2]
                if not rid: continue
                system = system_from(kv.get("service") or kv.get("system") or kv.get("target_system"), rel + " " + line)
                cat = resource_category(system, kv, rel + " " + line)
                ts = parse_time(kv.get("event_time") or kv.get("observed_at") or kv.get("timestamp")) or parse_time(line[:20]) or captured
                row = dict(kv)
                row["_raw"] = line
                records.append({"resource_id": str(rid), "system_id": system, "category": cat,
                                "row": row, "context": line + " " + rel, "evidence_id": evidence_id,
                                "time": ts, "source": rel, "kind": "log"})
        # PDFs/images are intentionally not parsed by default: text/SQL/JSON/log evidence
        # is machine-readable and OCR tooling is not a declared dependency.
    # Attach explicit catalog ownership links after extraction. These links establish
    # identity association, not record existence or deletion state.
    identity_links = load_identity_links()
    for record in records:
        record["identity_links"] = identity_links.get(record.get("resource_id", ""), [])
    # A narrowly scoped exception: the attachment catalog event explicitly says
    # it confirmed the storage object, not merely linked its identity. Treat that
    # event as a presence observation with its activity ID as provenance.
    for rid, links in identity_links.items():
        for link in links:
            details = str(link.get("details", "")).casefold()
            if "attachment catalog confirmed" not in details:
                continue
            records.append({
                "resource_id": rid, "system_id": "object_storage",
                "category": "SUPPORT_ATTACHMENT",
                "row": {"resource_id": rid, "user_id": link.get("user_id"),
                        "email": link.get("email"), "status": "PRESENT",
                        "_raw": link.get("details", "")},
                "context": link.get("details", ""), "evidence_id": link.get("activity_id", ""),
                "time": link.get("event_time"), "source": "system_activity.csv",
                "kind": "catalog_link", "identity_links": links,
            })
    return records

def identity_index():
    identities = read_csv(DATA / "user_identities.csv")
    audits = read_csv(DATA / "user_audit_log.csv")
    by_user = {}
    email_users = {}
    for row in identities:
        uid = row["user_id"]
        by_user.setdefault(uid, set()).add(uid)
        for f in ("name","email","phone","email_hash"):
            if row.get(f): by_user[uid].add(row[f])
        if row.get("email"): email_users.setdefault(norm(row["email"]), set()).add(uid)
    for row in audits:
        uid = row["user_id"]
        by_user.setdefault(uid, set()).add(uid)
        if row.get("field_name") in ("email","phone","email_hash","name"):
            for f in ("old_value","new_value"):
                if row.get(f): by_user[uid].add(row[f])
            if row.get("field_name") == "email":
                for f in ("old_value","new_value"):
                    if row.get(f): email_users.setdefault(norm(row[f]), set()).add(uid)
    # The data catalog is an authoritative resource-to-user mapping source. Its
    # explicit links can resolve a request email even when the current identity
    # row has changed; keep these aliases scoped to the linked user ID.
    for links in load_identity_links().values():
        for link in links:
            uid = link.get("user_id", "")
            email = norm(link.get("email", ""))
            if not uid:
                continue
            by_user.setdefault(uid, set()).add(uid)
            if email:
                by_user[uid].add(email)
                email_users.setdefault(email, set()).add(uid)
    return identities, audits, by_user, email_users

def flatten_values(obj):
    out = []
    if isinstance(obj, dict):
        for k,v in obj.items():
            out.append((str(k).casefold(), v))
            out.extend(flatten_values(v))
    elif isinstance(obj, list):
        for v in obj: out.extend(flatten_values(v))
    return out

def record_matches(rec, identifiers, uid):
    row = rec["row"]
    # An explicit data-catalog ownership link can associate a resource even when
    # its own payload has already been anonymized. The link does not prove presence.
    for link in rec.get("identity_links", []):
        if norm(link.get("user_id")) == norm(uid):
            return True
        if link.get("email") and norm(link.get("email")) in identifiers:
            return True
    # Identity references have higher confidence than incidental textual overlap.
    for key, val in flatten_values(row):
        if val is None: continue
        sv = str(val).strip()
        if not sv: continue
        if key in ("customer_reference","user_id","subject_reference","subject_ref","subject_user_id","customer_id","owner_user_id"):
            if norm(sv) == norm(uid): return True
        if key in ("email","owner_email","customer_email","requester_email","subject_email",
                   "lookup_key","query","identifier","subject_key","match_key","correlation_key",
                   "matched_value","email_address","old_email","new_email"):
            if norm(sv) in identifiers: return True
        if key in ("phone","requester_phone","owner_phone","customer_phone","email_hash","hash",
                   "full_name","name","requester_name","subject_ref","subject_reference",
                   "owner_reference","customer_reference","subject_user_id","subject_ref"):
            if norm(sv) in identifiers: return True
    # Text logs can contain the lookup identifier in raw line.
    raw = str(row.get("_raw",""))
    return any(i and i in norm(raw) for i in identifiers if "@" in i)

def evidence_for_identity(evidence_records, identifiers, uid, audit_at):
    """Resolve a subject to resource IDs, then gather every time-valid observation
    for those exact resources.

    Ownership may be explicit in one snapshot while a separate readback for the
    same resource omits subject fields (for example, a 404 response). The subject
    link may identify which resource to inspect, but each observation is still
    split by its own timestamp so post-cutoff state never proves historical state.
    """
    resource_keys = set()
    direct_matches = []
    for rec in evidence_records:
        if not record_matches(rec, identifiers, uid):
            continue
        direct_matches.append(rec)
        rid = rec.get("resource_id")
        if rid and rid != "__snapshot__":
            resource_keys.add((rec.get("system_id"), str(rid)))

    relevant, future_relevant = [], []
    for rec in evidence_records:
        key = (rec.get("system_id"), str(rec.get("resource_id", "")))
        if rec not in direct_matches and key not in resource_keys:
            continue
        if rec.get("time") and audit_at and rec["time"] > audit_at:
            future_relevant.append(rec)
        else:
            relevant.append(rec)
    return relevant, future_relevant


def unique_activity_resource(req, event_types, target_system, window_minutes, activity_rows=None):
    """Return a resource only when one distinct target matches the request's
    reported_at window. Activity is used for resource discovery, never as proof
    of the resource's final state.
    """
    reported_at = parse_time(req.get("reported_at"))
    if not reported_at:
        return None
    rows = activity_rows if activity_rows is not None else system_activity_rows()
    candidates = set()
    for row in rows:
        if row.get("event_type") not in event_types:
            continue
        if row.get("target_system") != target_system:
            continue
        rid = str(row.get("resource_id", "")).strip()
        event_time = parse_time(row.get("event_time"))
        if not rid or not event_time:
            continue
        # The workflow operation should precede the reported completion claim.
        delta = (reported_at - event_time).total_seconds() / 60
        if 0 <= delta <= window_minutes:
            candidates.add(rid)
    return next(iter(candidates)) if len(candidates) == 1 else None


def row_field(row, names):
    for k,v in row.items():
        if str(k).casefold() in names and v is not None and str(v).strip() != "":
            return v
    return None

def has_pii(row, identifiers):
    fields = {str(k).casefold(): v for k,v in row.items()}
    pii_keys = {"email","owner_email","customer_email","requester_email","subject_email",
                "phone","requester_phone","owner_phone","email_hash","full_name","requester_name",
                "display_name","name","matched_value","lookup_key","subject_key","match_key",
                "correlation_key","identifier","old_email","new_email"}
    for k,v in fields.items():
        if k in pii_keys and v not in (None,"","null","NULL"):
            return True
    raw = str(fields.get("_raw","")).casefold()
    return any(i and i in raw for i in identifiers if "@" in i)

def active_bool(row):
    """Return true if any relevant flag explicitly permits/activates the risky path."""
    truthy = {"true", "1", "yes", "active", "enabled", "allowed", "eligible", "open"}
    for key, value in row.items():
        k = str(key).casefold()
        if k in {"enabled", "active", "restore_allowed", "restore_access",
                 "can_restore", "eligible", "restore_enabled", "sync_enabled",
                 "import_enabled", "connector_enabled"}:
            if str(value).strip().casefold() in truthy:
                return True
    return False

def state_for(rec):
    row = {str(k).casefold(): v for k,v in rec["row"].items()}
    raw = str(row.get("_raw","")).casefold()
    # Readback trace semantics: structured JSON logs often store these values as
    # fields, while plain-text logs expose the same values in `_raw`.
    rows_value = str(row.get("rows", "")).strip()
    http_status = str(row.get("http_status", row.get("status_code", ""))).strip()
    status_value = str(row.get("status", "")).strip().casefold()
    event_value = str(row.get("event", "")).strip().casefold()
    if (rows_value == "0" or http_status == "404" or "rows=0" in raw or
            "http_status=404" in raw or "not_found" in raw or
            "not_found" in status_value or status_value in {"absent", "not_found"}):
        return "ABSENT"
    if http_status == "404": return "ABSENT"
    if rec["category"] == "DATA_FLOW":
        active_status = str(row.get("status", "")).casefold() in {"active", "enabled", "running"}
        disabled_status = str(row.get("status", "")).casefold() in {"disabled", "stopped", "inactive"}
        return "ACTIVE" if active_bool(row) or active_status or "enabled=true" in raw else "DISABLED"
    if rec["category"] == "BACKUP_ARCHIVE":
        risk = (active_bool(row) or str(row.get("status", "")).casefold() in {"active", "eligible"} or
                "restore_allowed=true" in raw or
                ("eligible=true" in raw and "deletion_block=false" in raw) or
                "deletion_block=false" in raw or "restore_candidate_evaluated" in raw)
        blocked = ("restore_allowed=false" in raw or "deletion_block=true" in raw or
                   str(row.get("restore_allowed", "")).casefold() == "false")
        return "ACTIVE" if risk and not blocked else "BLOCKED"
    return "PRESENT"

def make_step(phase, system, resource, op, state, evidence=""):
    return {"step_no": 0, "phase": phase, "system_id": system or "unknown_service",
            "resource_id": str(resource), "operation": op, "state": state, "evidence_id": evidence or ""}

def is_nonrequest(text):
    t = norm(text)
    patterns = [
        r"do not close the account", r"please don.t delete", r"please don.t delete or change",
        r"i still use it", r"do not delete", r"not requesting deletion", r"not a deletion request",
        r"i did not request deletion", r"i did not ask.*delet", r"cancel.*deletion",
        r"no longer want.*delet", r"do not erase", r"don.t erase",
    ]
    return any(re.search(p, t) for p in patterns)

def evidence_authority(rec):
    """Deterministic tie-break for observations with identical timestamps.

    Prefer point-in-time structured captures and direct readback evidence over
    derived logs or document OCR. This ranking never lets an older observation
    override a newer one; it only resolves same-time duplicates.
    """
    kind = str(rec.get("kind", ""))
    row = rec.get("row", {})
    score = {"snapshot": 60, "sql": 55, "json": 50, "log": 40,
             "document": 25, "catalog_link": 58}.get(kind, 0)
    if any(str(k).casefold() in {"http_status", "status_code", "rows", "query_result"}
           for k in row):
        score += 8
    if any(str(k).casefold() in {"user_id", "subject_user_id", "owner_user_id",
                                  "subject_ref", "subject_reference", "customer_reference"}
           and v not in (None, "") for k, v in row.items()):
        score += 5
    if rec.get("identity_links"):
        score += 12
    # Stable lexical tie-break avoids filesystem iteration order changing output.
    return (score, str(rec.get("source", "")), str(rec.get("evidence_id", "")))


def audit_case(req, evidence_records, by_user, email_users, identities, audits):
    email = req["email"]
    if is_nonrequest(req.get("request_text","")):
        return "NOT_APPLICABLE", []
    users = set(email_users.get(norm(email), set()))
    # current identity email match fallback
    for row in identities:
        if norm(row.get("email")) == norm(email): users.add(row["user_id"])
    if not users:
        # Request addresses are intended to resolve through historical identities.
        return "INCOMPLETE", []
    if len(users) != 1:
        # Never silently choose one person when an address has multiple owners.
        # That could miss records belonging to the other identity.
        return "INCOMPLETE", []
    uid = next(iter(users))
    id_values = set(norm(x) for x in by_user.get(uid, set()) if x)
    id_values.add(norm(email))
    # Resolve the identity as it existed at the request time, and include old values.
    # Names/phones are used only for exact structured-field matches, not substring searches.
    audit_at = parse_time(req.get("audit_at"))
    # A subject may be explicit in one observation but absent from a separate
    # readback for the same resource. Join by exact (system, resource_id) after
    # identity resolution, while enforcing the cutoff per observation.
    relevant, future_relevant = evidence_for_identity(
        evidence_records, id_values, uid, audit_at
    )
    # A single anonymization operation immediately before the workflow's report
    # time can identify an otherwise de-identified analytics resource. The event
    # is only a locator: the resource's own at-cutoff readback still proves state.
    activity_linked_keys = set()
    analytics_candidate = unique_activity_resource(
        req, {"ANONYMIZE_RECORD"}, "analytics_platform", 15
    )
    if analytics_candidate:
        candidate_records = [
            r for r in evidence_records
            if r["system_id"] == "analytics_platform"
            and r["resource_id"] == analytics_candidate
            and (not r["time"] or not audit_at or r["time"] <= audit_at)
        ]
        if candidate_records:
            activity_linked_keys.add(("analytics_platform", analytics_candidate))
            relevant.extend(candidate_records)
    # Latest observation per resource and system. A later observation wins when
    # it changes the interpreted state; when two sources agree on state, prefer
    # the more authoritative structured/catalog source over a lower-authority log.
    # This avoids citing a noisy retry log when a catalog row independently
    # confirms the same resource state.
    latest = {}
    for rec in relevant:
        key = (rec["system_id"], rec["resource_id"])
        prev = latest.get(key)
        rec_time = rec["time"] or datetime.min.replace(tzinfo=timezone.utc)
        prev_time = (prev["time"] or datetime.min.replace(tzinfo=timezone.utc)) if prev else None
        if prev is None:
            latest[key] = rec
            continue
        rec_state, prev_state = state_for(rec), state_for(prev)
        if rec_state == prev_state and evidence_authority(rec) != evidence_authority(prev):
            if evidence_authority(rec) > evidence_authority(prev):
                latest[key] = rec
        elif rec_time > prev_time or (rec_time == prev_time and evidence_authority(rec) > evidence_authority(prev)):
            latest[key] = rec
    latest_records = list(latest.values())

    findings, remediation, verify = [], [], []
    account_absent_evidence = None
    account_resource = None

    # Search logs for explicit account absence checks even if the record has no PII fields.
    for rec in evidence_records:
        if rec["system_id"] != "account_service": continue
        if rec["time"] and audit_at and rec["time"] > audit_at: continue
        raw = str(rec["row"].get("_raw","")).casefold()
        lookup = norm(rec["row"].get("lookup_key") or rec["row"].get("query") or rec["row"].get("identifier") or "")
        if lookup in id_values and (("rows=0" in raw) or ("http_status=404" in raw) or state_for(rec) == "ABSENT"):
            account_absent_evidence = rec["evidence_id"]
            account_resource = rec["resource_id"]
    # The deletion worker's target resource is useful for choosing which account
    # to verify, but its result is never accepted as proof of absence. Only use a
    # tightly time-correlated account operation; this avoids guessing from unrelated
    # activity elsewhere in the same batch.
    account_activity_resource = None
    account_followup_candidate = unique_activity_resource(
        req, {"DELETE_RECORD"}, "account_service", 75
    )
    reported_at = parse_time(req.get("reported_at"))
    if reported_at:
        account_ops = []
        for activity in system_activity_rows():
            if activity.get("event_type") != "DELETE_RECORD":
                continue
            if activity.get("target_system") != "account_service":
                continue
            rid = activity.get("resource_id", "")
            event_time = parse_time(activity.get("event_time"))
            if not rid.startswith("account_") or not event_time:
                continue
            delta = abs((event_time - reported_at).total_seconds())
            if delta <= 600:
                account_ops.append((delta, rid))
        # Only use a timestamp-derived resource when the event is unambiguous.
        # Several deletion requests can share a reported_at batch; in that case
        # proximity alone is insufficient to assign an account to a person.
        distinct_resources = {rid for _, rid in account_ops}
        if len(account_ops) == 1 and len(distinct_resources) == 1:
            account_activity_resource = account_ops[0][1]

    # Use the most recent complete point-in-time account snapshot available at
    # audit_at, including SQL replica captures, not only JSON assurance bundles.
    account_snapshot = max(
        (r for r in evidence_records
         if r["system_id"] == "account_service" and r.get("kind") == "snapshot"
         and (not r["time"] or not audit_at or r["time"] <= audit_at)),
        key=lambda r: r["time"] or datetime.min.replace(tzinfo=timezone.utc),
        default=None,
    )
    # Determine issues in each latest observed record.
    for rec in latest_records:
        row = rec["row"]
        cat = rec["category"]
        system = rec["system_id"]
        rid = rec["resource_id"]
        state = state_for(rec)
        raw = str(row.get("_raw","")).casefold()
        pii = has_pii(row, id_values)
        # Don't treat an explicit 404/readback as present.
        if state == "ABSENT":
            if system == "account_service":
                account_absent_evidence = rec["evidence_id"]; account_resource = rid
            continue
        if cat in ("USER_PROFILE","SECONDARY_IDENTIFIER","SEARCH_INDEX_ENTRY","CACHE_ENTRY","USER_EXPORT","MARKETING_PROFILE","SUPPORT_ATTACHMENT"):
            findings.append(make_step("FINDING", system, rid, "REPORT_REMAINING_RECORD", "PRESENT", rec["evidence_id"]))
            remediation.append(make_step("REMEDIATION", system, rid, "DELETE_RECORD", "ABSENT"))
            verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_ABSENT", "ABSENT"))
        elif cat == "SUPPORT_MESSAGE":
            event = norm(row.get("event", ""))
            is_contact_index = rec.get("kind") == "log" and (
                "contact_query" in event or "legacy_contact_index" in norm(row.get("source", ""))
            )
            if is_contact_index:
                # A successful lookup in a legacy contact index proves the resource
                # remains addressable; it is not a shared-context conversation record.
                findings.append(make_step("FINDING", system, rid, "REPORT_REMAINING_RECORD", "PRESENT", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "DELETE_RECORD", "ABSENT"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_ABSENT", "ABSENT"))
            elif pii:
                findings.append(make_step("FINDING", system, rid, "REPORT_EXPOSED_PII", "PRESENT", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "REDACT_RECORD", "REDACTED"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_REDACTED", "REDACTED"))
            else:
                # A record can be correctly redacted and still be relevant to this
                # request because its structured subject/ownership reference linked it
                # to the user. Preserve a verification step rather than silently
                # dropping that retained record from the audit trail.
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_REDACTED", "REDACTED", rec["evidence_id"]))
            # A non-identifiable retained shared-context message is allowed, but
            # its redaction state should remain explicitly verifiable.
        elif cat in ("ANALYTICS_PROFILE","PRODUCT_TELEMETRY"):
            if pii or any(norm(row.get(k)) == norm(uid) for k in ("user_id","customer_reference")):
                findings.append(make_step("FINDING", system, rid, "REPORT_EXPOSED_PII", "PRESENT", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "ANONYMIZE_RECORD", "ANONYMIZED"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED"))
            elif state == "PRESENT":
                # Identified only by its subject reference: still attributable unless fields were stripped.
                if any(norm(v) == norm(uid) for v in row.values() if v is not None):
                    findings.append(make_step("FINDING", system, rid, "REPORT_EXPOSED_PII", "PRESENT", rec["evidence_id"]))
                    remediation.append(make_step("REMEDIATION", system, rid, "ANONYMIZE_RECORD", "ANONYMIZED"))
                    verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED"))
                elif rec.get("identity_links") or (system, rid) in activity_linked_keys:
                    # An explicit catalog link, or a unique workflow operation
                    # immediately before reported_at, can locate this de-identified
                    # resource. The record itself must still show stripped fields.
                    verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED", rec["evidence_id"]))
        elif cat == "DATA_FLOW" or system == "integration_service":
            flow_status = str(row.get("status", "")).casefold()
            enabled = (active_bool(row) or flow_status in {"active", "enabled", "running"}
                       or state == "ACTIVE" or "enabled=true" in raw or "status=active" in raw)
            if enabled:
                findings.append(make_step("FINDING", system, rid, "REPORT_ACTIVE_DATA_FLOW", "ACTIVE", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "DISABLE_DATA_FLOW", "DISABLED"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_DATA_FLOW_DISABLED", "DISABLED"))
            else:
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_DATA_FLOW_DISABLED", "DISABLED", rec["evidence_id"]))
        elif cat == "BACKUP_ARCHIVE" or system == "backup_service":
            allowed = state_for(rec) == "ACTIVE"
            if allowed:
                findings.append(make_step("FINDING", system, rid, "REPORT_RESTORE_RISK", "ACTIVE", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "BLOCK_RESTORE", "BLOCKED"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RESTORE_BLOCKED", "BLOCKED"))
            else:
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RESTORE_BLOCKED", "BLOCKED", rec["evidence_id"]))
        elif cat == "SECURITY_AUDIT_LOG":
            verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_PRESENT", "PRESENT", rec["evidence_id"]))
        elif cat == "EMAIL_DELIVERY_LOG":
            if pii:
                findings.append(make_step("FINDING", system, rid, "REPORT_EXPOSED_PII", "PRESENT", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "REDACT_RECORD", "REDACTED"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_REDACTED", "REDACTED"))
        elif cat == "ACCOUNT_TOMBSTONE":
            if pii:
                findings.append(make_step("FINDING", system, rid, "REPORT_EXPOSED_PII", "PRESENT", rec["evidence_id"]))
                remediation.append(make_step("REMEDIATION", system, rid, "REDACT_RECORD", "REDACTED"))
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_REDACTED", "REDACTED"))
            else:
                verify.append(make_step("VERIFICATION", system, rid, "VERIFY_RECORD_REDACTED", "REDACTED", rec["evidence_id"]))

    # If account absence is explicitly verified, include it; if a live account record was found,
    # that finding already supplies the remediation/verification.
    account_found = any(
        r["system_id"] == "account_service" and r["category"] == "USER_PROFILE"
        and r["resource_id"] != "__snapshot__" and state_for(r) != "ABSENT"
        and (not account_snapshot or not r["time"] or not account_snapshot["time"] or r["time"] >= account_snapshot["time"])
        for r in latest_records
    )
    if not account_found and not account_absent_evidence and account_snapshot:
        account_absent_evidence = account_snapshot["evidence_id"]
        # Prefer an account resource ID explicitly linked to this user.
        linked_accounts = [
            r for r in evidence_records
            if r["system_id"] == "account_service"
            and any(norm(link.get("user_id")) == norm(uid) for link in r.get("identity_links", []))
            and (not r["time"] or not audit_at or r["time"] <= audit_at)
        ]
        # If a later point-in-time lookup identifies the account resource, use
        # that identifier only to target a proposed check, never as proof of state.
        future_accounts = [
            r for r in future_relevant
            if r["system_id"] == "account_service" and r["category"] == "USER_PROFILE"
            and r["resource_id"] != "__snapshot__"
        ]
        account_candidates = linked_accounts or future_accounts
        if account_candidates:
            account_resource = sorted(account_candidates, key=lambda r: r["resource_id"])[0]["resource_id"]
        elif account_activity_resource:
            account_resource = account_activity_resource
        else:
            account_resource = "account_unknown"
    if not account_found and account_absent_evidence:
        # In an incomplete case, a unique deletion-worker target can make the
        # follow-up check actionable, but the activity claim is not accepted as
        # evidence of absence. COMPLETE cases never use this time-only locator.
        if findings and (not account_resource or account_resource == "account_unknown") and account_followup_candidate:
            account_resource = account_followup_candidate
        verify.append(make_step("VERIFICATION", "account_service", account_resource or "account_unknown",
                                "VERIFY_RECORD_ABSENT", "ABSENT", account_absent_evidence))

    # Use post-cutoff evidence only to identify resources requiring future checks.
    # Its observed state is not treated as evidence for the earlier audit timestamp.
    if not any(x["phase"] == "FINDING" for x in findings):
        # A request can still be incomplete because required evidence is missing.
        pass
    existing_verify_keys = {
        (x["system_id"], x["resource_id"], x["operation"]) for x in verify
    }
    for rec in future_relevant:
        system, rid, cat = rec["system_id"], rec["resource_id"], rec["category"]
        if rid == "__snapshot__" or not rid:
            continue
        if cat in ("USER_PROFILE", "SECONDARY_IDENTIFIER", "SEARCH_INDEX_ENTRY",
                   "CACHE_ENTRY", "USER_EXPORT", "MARKETING_PROFILE", "SUPPORT_ATTACHMENT"):
            op, state = "VERIFY_RECORD_ABSENT", "ABSENT"
        elif cat in ("SUPPORT_MESSAGE",):
            op, state = "VERIFY_RECORD_REDACTED", "REDACTED"
        elif cat in ("ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"):
            op, state = "VERIFY_RECORD_ANONYMIZED", "ANONYMIZED"
        elif cat == "DATA_FLOW":
            op, state = "VERIFY_DATA_FLOW_DISABLED", "DISABLED"
        elif cat == "BACKUP_ARCHIVE":
            op, state = "VERIFY_RESTORE_BLOCKED", "BLOCKED"
        elif cat == "SECURITY_AUDIT_LOG":
            op, state = "VERIFY_RECORD_PRESENT", "PRESENT"
        elif cat == "ACCOUNT_TOMBSTONE":
            op, state = "VERIFY_RECORD_REDACTED", "REDACTED"
        else:
            continue
        key = (system, rid, op)
        if key not in existing_verify_keys:
            verify.append(make_step("VERIFICATION", system, rid, op, state, ""))
            existing_verify_keys.add(key)

    # Remove exact duplicate steps; then sort by the contract's operation ordering.
    def dedup(items):
        d={}
        for x in items:
            key=(x["phase"],x["system_id"],x["resource_id"],x["operation"],x["state"])
            if key not in d or (not d[key]["evidence_id"] and x["evidence_id"]):
                d[key]=x
        return list(d.values())
    findings, remediation, verify = map(dedup, (findings, remediation, verify))
    findings.sort(key=lambda x:(OP_ORDER.get(x["operation"],99),x["system_id"],x["resource_id"]))
    remediation.sort(key=lambda x:(OP_ORDER.get(x["operation"],99),x["system_id"],x["resource_id"]))
    verify.sort(key=lambda x:(OP_ORDER.get(x["operation"],99),x["system_id"],x["resource_id"]))
    # Findings are sufficient to establish INCOMPLETE. If no violation is observed,
    # completion requires an explicit account-absence check; when evidence is sparse,
    # the workflow claim is used only as a low-confidence fallback and never overrides
    # an observed violation.
    if findings:
        status = "INCOMPLETE"
    elif account_absent_evidence:
        status = "COMPLETE"
    else:
        # A workflow claim or a retained-record observation alone is not proof that
        # the primary account is absent. Missing proof must not be upgraded to COMPLETE.
        status = "INCOMPLETE"
    if status == "COMPLETE":
        verify = [s for s in verify if s["evidence_id"]]
        steps = verify
    else:
        # Verification in an incomplete case is proposed future work, not a
        # completed observation. The contract requires empty evidence references.
        for step in verify:
            step["evidence_id"] = ""
        steps = findings + remediation + verify
    for n, step in enumerate(steps, 1):
        step["step_no"] = n
    return status, steps

def main():
    requests = read_csv(DATA / "deletion_requests.csv")
    identities, audits, by_user, email_users = identity_index()
    evidence_records = load_evidence()
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case_id","deletion_status","steps_json"])
        writer.writeheader()
        for req in sorted(requests, key=lambda r: r["case_id"]):
            status, steps = audit_case(req, evidence_records, by_user, email_users, identities, audits)
            writer.writerow({"case_id":req["case_id"],"deletion_status":status,
                             "steps_json":json.dumps(steps, ensure_ascii=False, separators=(",",":"))})
    print(f"Wrote {OUT} with {len(requests)} cases using {len(evidence_records)} evidence records.")

if __name__ == "__main__":
    main()
