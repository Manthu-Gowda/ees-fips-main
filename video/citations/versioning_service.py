from video.citations.versioning_utils import append_new_version, build_versions_for_citation, FINAL_STATES
from datetime import datetime
from video.models import CitationVersioning


# def update_citation_versioning_after_approval(citation):
#     """
#     Rebuild and update CitationVersioning whenever a citation is approved.
#     """
#     if citation.is_warning:
#         append_new_version(
#             citation=citation,
#             new_status="WARN-A",
#             snapshot_overrides={
#                 "status": "WARN-A",
#                 "fine": {
#                     "id": citation.fine.id,
#                     "amount": 0.0
#                 }
#             }
#         )
#         return
#     versions = build_versions_for_citation(citation)
#     if not versions:
#         return

#     latest = versions[0]

#     # Convert approvedDate string → datetime object
#     approved_str = latest.get("approvedDate")
#     approved_dt = None
#     if approved_str:
#         try:
#             approved_dt = datetime.fromisoformat(approved_str.replace("Z", "+00:00"))
#         except:
#             approved_dt = None

#     # Determine final status + subStatus
#     if latest.get("subStatus"):
#         final_status = f"{latest['status']}-{latest['subStatus']}"
#     else:
#         final_status = latest["status"]

#     # Determine whether this citation is editable
#     is_editable = latest["status"] not in FINAL_STATES

#     CitationVersioning.objects.update_or_create(
#         citation=citation,
#         defaults={
#             "versions": versions,
#             "current_version_number": latest["version_number"],
#             "latest_status": final_status,
#             "latest_approved_date": approved_dt,
#             "isAllowEdit": is_editable,
#         }
#     )

def update_citation_versioning_after_approval(citation):
    """
    Rebuild and update CitationVersioning whenever a citation is approved.
    """

    # ALWAYS build full versions first
    versions = build_versions_for_citation(citation)
    if not versions:
        return

    latest = versions[0]


    if citation.is_warning:
        latest["status"] = "WARN-A"
        latest["snapshot"]["status"] = "WARN-A"
        latest["snapshot"]["fine"] = {
            "id": citation.fine.id,
            "amount": 0.0
        }

    # Convert approvedDate string → datetime
    approved_str = latest.get("approvedDate")
    approved_dt = None
    if approved_str:
        try:
            approved_dt = datetime.fromisoformat(
                approved_str.replace("Z", "+00:00")
            )
        except:
            approved_dt = None

    final_status = latest["status"]
    is_editable = final_status not in FINAL_STATES

    CitationVersioning.objects.update_or_create(
        citation=citation,
        defaults={
            "versions": versions,
            "current_version_number": latest["version_number"],
            "latest_status": final_status,
            "latest_approved_date": approved_dt,
            "isAllowEdit": is_editable,
        }
    )