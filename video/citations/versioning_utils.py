from copy import deepcopy
from datetime import datetime
from typing import List, Dict, Any, Optional

from django.utils import timezone
from django.db.models import Q

from video.models import (
    Citation,
    CitationVersioning,
    CitationEditLog,
    CitationsWithUpdatedAddress,
    CitationsWithTransferOfLiabilty,
    CitationsWithEditFine,
    sup_metadata,
)

FINAL_STATES = ["PIH", "CE", "X"]


def resolve_media(citation: Citation) -> dict:
    """
    Resolve media type and media id from citation.
    Exactly one of video/image/tattile should exist.
    """
    if citation.video_id:
        return {
            "media_type": "video",
            "media_id": f"V-{citation.video_id}",
        }
    if citation.image_id:
        return {
            "media_type": "image",
            "media_id": f"I-{citation.image_id}",
        }
    if citation.tattile_id:
        return {
            "media_type": "tattile",
            "media_id": f"T-{citation.tattile_id}",
        }
    return {
        "media_type": None,
        "media_id": None,
    }

def build_base_snapshot_from_citation(citation: Citation) -> dict:
    person = citation.person
    vehicle = citation.vehicle
    fine = citation.fine
    location = citation.location
    media = resolve_media(citation)
    station = citation.station

    return {
        "citationId": citation.id,
        "citationID": citation.citationID,
        "status": citation.current_citation_status,

        # ✅ MEDIA
        "media": media,

        "station": {
            "station_id": station.id if station else None,
            "station_name": station.name if station else None,
        },

        # ✅ LOCATION
        "location": {
            "location_code": location.LOCATION_CODE if location else None,
            "location_name": location.location_name if location else None,
        },

        "person": {
            "id": person.id if person else None,
            "first_name": person.first_name if person else None,
            "last_name": person.last_name if person else None,
            "address": person.address if person else None,
            "city": person.city if person else None,
            "state": person.state if person else None,
            "zip": person.zip if person else None,
            "phone_number": person.phone_number if person else None,
        },
        "vehicle": {
            "id": vehicle.id if vehicle else None,
            "plate": vehicle.plate if vehicle else None,
            "state": vehicle.lic_state.ab if (vehicle and vehicle.lic_state) else None,
            "vin": vehicle.vin if vehicle else None,
        },
        "fine": {
            "id": fine.id if fine else None,
            "amount": float(fine.fine) if fine else None,
        },
        "speed": citation.speed,
        "posted_speed": citation.posted_speed,
        "captured_date": citation.captured_date.isoformat() if citation.captured_date else None,
        "created_at": citation.datetime.isoformat() if citation.datetime else None,
    }


def get_sup_metadata_for_citation(citation: Citation):
    return sup_metadata.objects.filter(citation_id=citation.id).first()


def get_approved_datetime(citation: Citation):
    """
    Prefer supervisor metadata timeApp, fallback to edited_at or created datetime.
    """
    sup_meta = get_sup_metadata_for_citation(citation)
    if sup_meta and sup_meta.timeApp:
        return sup_meta.timeApp
    if citation.citation_edited_at:
        return citation.citation_edited_at
    return citation.datetime


def build_versions_for_citation(citation: Citation) -> List[Dict[str, Any]]:
    """
    Build chronological versions for a citation and return list ordered LATEST -> OLDEST
    Each version structure:
      {
        "version_number": int,      # oldest=1 ... newest=N
        "status": "OR"/"UA"/"TL"/"EF"/"CE"/"X"/"PIH"/"RTS",
        "subStatus": Optional[str],
        "approvedDate": isoformat or None,
        "pdf_s3_key": None,
        "snapshot": {...}
      }
    """
    # 1) Prepare base snapshot (uses current citation values as template)
    base_template = build_base_snapshot_from_citation(citation)

    # 2) Gather history rows (single DB hit per table)
    ua_rows = list(
        CitationsWithUpdatedAddress.objects.filter(citation=citation).order_by("datetime")
    )
    tl_rows = list(
        CitationsWithTransferOfLiabilty.objects.filter(citation=citation).order_by("datetime")
    )
    ef_rows = list(
        CitationsWithEditFine.objects.filter(citation=citation).order_by("datetime")
    )
    edit_logs = list(
        CitationEditLog.objects.filter(citation=citation).order_by("edited_at")
    )

    # Build a list of events with common shape { ts, type, obj }
    events = []

    for r in ua_rows:
        events.append({"ts": r.datetime, "type": "UA", "row": r})

    for r in tl_rows:
        events.append({"ts": r.datetime, "type": "TL", "row": r})

    for r in ef_rows:
        events.append({"ts": r.datetime, "type": "EF", "row": r})

    for lg in edit_logs:
        # include CE/X/PIH/RTS etc. we store the log row itself
        events.append({"ts": lg.edited_at, "type": "LOG", "row": lg})

    # Sort events ascending (oldest -> newest)
    events.sort(key=lambda x: x["ts"] or datetime.min.replace(tzinfo=timezone.utc))

    versions_chrono: List[Dict[str, Any]] = []

    # 3) Build OR snapshot (oldest) using earliest history when available
    # Priority: earliest UA.old_*  -> earliest TL.old_person -> earliest EF.old_fine -> fallback to citation.person
    or_snapshot = deepcopy(base_template)

    if ua_rows:
        first = ua_rows[0]
        or_snapshot["person"]["address"] = first.old_address or or_snapshot["person"]["address"]
        or_snapshot["person"]["city"] = first.old_city or or_snapshot["person"]["city"]
        or_snapshot["person"]["state"] = first.old_person_state or or_snapshot["person"]["state"]
        or_snapshot["person"]["zip"] = first.old_zip or or_snapshot["person"]["zip"]
    elif tl_rows:
        first = tl_rows[0]
        if first.old_person:
            op = first.old_person
            or_snapshot["person"]["id"] = op.id
            or_snapshot["person"]["first_name"] = op.first_name
            or_snapshot["person"]["last_name"] = op.last_name
            or_snapshot["person"]["address"] = op.address
            or_snapshot["person"]["city"] = op.city
            or_snapshot["person"]["state"] = op.state
            or_snapshot["person"]["zip"] = op.zip
            or_snapshot["person"]["phone_number"] = op.phone_number
    else:
        # No special history — assume citation.person is original (no edits)
        pass

    # OR approvedDate from sup_metadata.originalTimeApp if present (preferred)
    sup = get_sup_metadata_for_citation(citation)
    or_approved_iso = None
    if sup and sup.originalTimeApp:
        try:
            or_approved_iso = sup.originalTimeApp.isoformat()
        except Exception:
            or_approved_iso = None
    else:
        # fallback to citation.datetime
        try:
            or_approved_iso = citation.datetime.isoformat() if citation.datetime else None
        except Exception:
            or_approved_iso = None

    versions_chrono.append({
        "version_number": None,
        "status": "OR",
        "subStatus": None,
        "approvedDate": or_approved_iso,
        "pdf_s3_key": None,
        "snapshot": deepcopy(or_snapshot),
    })

    # 4) Iterate events in chronological order and apply to snapshot
    # current_snapshot always represents the state right after the last appended version
    current_snapshot = deepcopy(or_snapshot)

    for ev in events:
        et = ev["type"]
        row = ev["row"]
        ts = ev["ts"]

        if et == "UA":
            # Apply updated address fields
            current_snapshot = deepcopy(current_snapshot)
            current_snapshot["person"]["address"] = row.updated_address or current_snapshot["person"].get("address")
            current_snapshot["person"]["city"] = row.updated_city or current_snapshot["person"].get("city")
            current_snapshot["person"]["state"] = row.updated_person_state or current_snapshot["person"].get("state")
            current_snapshot["person"]["zip"] = row.updated_zip or current_snapshot["person"].get("zip")
            current_snapshot["status"] = "UA"

            versions_chrono.append({
                "version_number": None,
                "status": "UA",
                "subStatus": None,
                "approvedDate": (row.datetime.isoformat() if row.datetime else None),
                "pdf_s3_key": None,
                "snapshot": deepcopy(current_snapshot)
            })

        elif et == "TL":
            # Transfer of liability: replace person with new_person details
            current_snapshot = deepcopy(current_snapshot)
            nperson = row.new_person
            if nperson:
                current_snapshot["person"]["id"] = nperson.id
                current_snapshot["person"]["first_name"] = nperson.first_name
                current_snapshot["person"]["last_name"] = nperson.last_name
                current_snapshot["person"]["address"] = nperson.address
                current_snapshot["person"]["city"] = nperson.city
                current_snapshot["person"]["state"] = nperson.state
                current_snapshot["person"]["zip"] = nperson.zip
                current_snapshot["person"]["phone_number"] = nperson.phone_number
            current_snapshot["status"] = "TL"

            versions_chrono.append({
                "version_number": None,
                "status": "TL",
                "subStatus": None,
                "approvedDate": (row.datetime.isoformat() if row.datetime else None),
                "pdf_s3_key": None,
                "snapshot": deepcopy(current_snapshot)
            })

        elif et == "EF":
            # Edit fine: update fine.amount to new_fine
            current_snapshot = deepcopy(current_snapshot)
            # ef row may store new_fine as Decimal or numeric column
            try:
                # if model has new_fine field numeric (as in your model)
                current_snapshot["fine"]["amount"] = float(row.new_fine)
            except Exception:
                # fallback: if ef_row has different structure
                current_snapshot["fine"]["amount"] = row.new_fine if hasattr(row, "new_fine") else current_snapshot["fine"].get("amount")
            current_snapshot["status"] = "EF"

            versions_chrono.append({
                "version_number": None,
                "status": "EF",
                "subStatus": None,
                "approvedDate": (row.datetime.isoformat() if row.datetime else None),
                "pdf_s3_key": None,
                "snapshot": deepcopy(current_snapshot)
            })

        elif et == "LOG":
            # Handle CE, X, PID/PIH, RTS from edit logs
            log = row  # CitationEditLog instance
            st = log.current_citation_status
            prev = log.previous_citation_status

            # Only include log entries that indicate a change of status we care about
            if st in ("CE", "X", "PID", "PIH", "RTS"):
                current_snapshot = deepcopy(current_snapshot)
                current_snapshot["status"] = st

                sub = None
                if st == "CE":
                    # use citation's citation_error_type or log's extra
                    sub = getattr(log, "citation_error_type", None) or None
                if st == "X":
                    sub = getattr(log, "citation_dissmissal_type", None) or None

                versions_chrono.append({
                    "version_number": None,
                    "status": st,
                    "subStatus": sub,
                    "approvedDate": (log.edited_at.isoformat() if log.edited_at else None),
                    "pdf_s3_key": None,
                    "snapshot": deepcopy(current_snapshot)
                })
            else:
                # ignore other log types
                continue

        else:
            # unknown event type — ignore
            continue

    # 5) After applying all events, make sure the final snapshot (latest) reflects current citation fields
    # Merge vehicle/fine/speed from citation to ensure any fields not touched by events reflect current values
    latest_snapshot = deepcopy(current_snapshot)
    # update non-person fields from template (vehicle, fine maybe)
    latest_snapshot["vehicle"] = deepcopy(base_template["vehicle"])
    latest_snapshot["speed"] = base_template.get("speed")
    latest_snapshot["posted_speed"] = base_template.get("posted_speed")
    latest_snapshot["fine"] = deepcopy(base_template["fine"])
    latest_snapshot["created_at"] = base_template.get("created_at")
    latest_snapshot["captured_date"] = base_template.get("captured_date")
    # latest status should equal citation.current_citation_status
    latest_snapshot["status"] = citation.current_citation_status or latest_snapshot.get("status")

    # Determine latest approved date (prefer sup.timeApp)
    sup_latest = get_sup_metadata_for_citation(citation)
    latest_approved_iso = None
    if sup_latest and sup_latest.timeApp:
        latest_approved_iso = sup_latest.timeApp.isoformat()
    else:
        # fallback to last event ts or citation.citation_edited_at
        last_event_ts = None
        if events:
            last_event_ts = events[-1]["ts"]
        latest_approved_iso = (last_event_ts.isoformat() if last_event_ts else (citation.citation_edited_at.isoformat() if citation.citation_edited_at else (citation.datetime.isoformat() if citation.datetime else None)))

    # If the final versions_chrono last entry snapshot differs from latest_snapshot, append one final "current" version
    # Compare by simple heuristic: compare status or fine amount or person.address
    append_final = True
    if versions_chrono:
        last = versions_chrono[-1]
        last_snap = last.get("snapshot", {})
        if (last_snap.get("person", {}).get("address") == latest_snapshot.get("person", {}).get("address") and
            float(last_snap.get("fine", {}).get("amount") or 0) == float(latest_snapshot.get("fine", {}).get("amount") or 0) and
            last_snap.get("status") == latest_snapshot.get("status")):
            append_final = False

    if append_final:
        versions_chrono.append({
            "version_number": None,
            "status": latest_snapshot.get("status"),
            "subStatus": None,
            "approvedDate": latest_approved_iso,
            "pdf_s3_key": None,
            "snapshot": deepcopy(latest_snapshot)
        })

    # 6) Assign version_number oldest=1 .. newest=N
    total = len(versions_chrono)
    for idx, ent in enumerate(versions_chrono):
        ent["version_number"] = idx + 1

    # 7) Return list with LATEST first (reverse chronological)
    versions_output = list(reversed(versions_chrono))

    return versions_output

from copy import deepcopy
from datetime import datetime
from typing import Dict, Any

from django.utils import timezone
from django.db import transaction

from video.models import Citation, CitationVersioning, sup_metadata

FINAL_STATES = {"PIH", "CE", "X", "WARN-A"}


# ---------------------------------------------------
# Snapshot builder
# ---------------------------------------------------
def build_base_snapshot(citation: Citation) -> dict:
    person = citation.person
    vehicle = citation.vehicle
    fine = citation.fine

    return {
        "citationId": citation.id,
        "citationID": citation.citationID,
        "status": citation.current_citation_status,
        "person": {
            "id": person.id if person else None,
            "first_name": person.first_name if person else None,
            "last_name": person.last_name if person else None,
            "address": person.address if person else None,
            "city": person.city if person else None,
            "state": person.state if person else None,
            "zip": person.zip if person else None,
            "phone_number": person.phone_number if person else None,
        },
        "vehicle": {
            "id": vehicle.id if vehicle else None,
            "plate": vehicle.plate if vehicle else None,
            "state": vehicle.lic_state.ab if vehicle and vehicle.lic_state else None,
            "vin": vehicle.vin if vehicle else None,
        },
        "fine": {
            "id": fine.id if fine else None,
            "amount": float(fine.fine) if fine else None,
        },
        "speed": citation.speed,
        "posted_speed": citation.posted_speed,
        "captured_date": citation.captured_date.isoformat() if citation.captured_date else None,
        "created_at": citation.datetime.isoformat() if citation.datetime else None,
    }


# ---------------------------------------------------
# Approved datetime helpers
# ---------------------------------------------------
def get_latest_approved_date(citation: Citation):
    sup = sup_metadata.objects.filter(citation_id=citation.id).first()
    if sup and sup.timeApp:
        return sup.timeApp
    return citation.citation_edited_at or citation.datetime


# ---------------------------------------------------
# CORE: append new version
# ---------------------------------------------------
@transaction.atomic
def append_new_version(
    citation: Citation,
    new_status: str,
    snapshot_overrides: Dict[str, Any] | None = None,
    sub_status: str | None = None,
):
    """
    Append a new version for every edit.
    """

    cv, _ = CitationVersioning.objects.get_or_create(
        citation=citation,
        defaults={
            "versions": [],
            "current_version_number": 0,
            "latest_status": "OR",
            "latest_approved_date": None,
            "isAllowEdit": True,
        },
    )

    versions = cv.versions or []

    # Base snapshot = last snapshot OR fresh OR snapshot
    if versions:
        base_snapshot = deepcopy(versions[-1]["snapshot"])
    else:
        base_snapshot = build_base_snapshot(citation)
        base_snapshot["status"] = "OR"

    snapshot = deepcopy(base_snapshot)
    snapshot["status"] = new_status

    if snapshot_overrides:
        for key, value in snapshot_overrides.items():
            snapshot[key] = value

    # approved_dt = get_latest_approved_date(citation)
    approved_dt = datetime.now()
    version_number = len(versions) + 1

    versions.append({
        "version_number": version_number,
        "status": new_status,
        "subStatus": sub_status,
        "approvedDate": approved_dt.strftime("%B %d, %Y").replace(" 0", " "),
        "pdf_s3_key": None,
        "snapshot": snapshot,
    })

    cv.versions = versions
    cv.current_version_number = version_number
    cv.latest_status = new_status if not sub_status else f"{new_status}-{sub_status}"
    cv.latest_approved_date = approved_dt
    cv.isAllowEdit = new_status not in FINAL_STATES
    cv.save()

def get_last_snapshot(citation):
    cv = CitationVersioning.objects.filter(citation=citation).first()
    if cv and cv.versions:
        return cv.versions[-1]["snapshot"]
    return build_base_snapshot(citation)

from video.models import Citation, CitationVersioning


def get_snapshot_by_version(citation, version_number):
    cv = CitationVersioning.objects.filter(citation=citation).first()
    if not cv or not cv.versions:
        return None

    for v in cv.versions:
        if v.get("version_number") == version_number:
            return v
    return None


def get_latest_version_number(citation: Citation) -> int | None:
    cv = CitationVersioning.objects.filter(citation=citation).first()
    if not cv:
        return None
    return cv.current_version_number

def get_latest_fine_from_versioning(citation):
    if citation.is_warning:
        return 0.0
    else:
        return citation.fine_amount if citation.fine else None
    # cv = getattr(citation, "citation_versioning", None)
    # if not cv or not cv.versions:
    #     return citation.fine.fine

    # latest = cv.versions[-1]   
    # snapshot = latest.get("snapshot", {})

    # return snapshot.get("fine", {}).get("amount", citation.fine.fine)

from datetime import datetime

def format_us_date(value):
    """
    Converts date/datetime/string → 'January 6, 2026'
    """
    if not value:
        return None

    # If already formatted correctly, return as-is
    if isinstance(value, str) and "," in value:
        return value

    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", ""))
        return value.strftime("%B %d, %Y").replace(" 0", " ")
    except Exception:
        return value