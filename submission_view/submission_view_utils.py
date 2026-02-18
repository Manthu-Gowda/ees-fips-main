from video.models import DuncanSubmission, EvidenceCalibrationBin, Rejects
from datetime import datetime

from openai import OpenAI
from openai import RateLimitError
from decouple import config

OPENAI_API_KEY = config("OPENAI_API_KEY", default="")

def get_openai_client():
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=OPENAI_API_KEY)

def create_submission(data, state_ab, station_name):
    DuncanSubmission.objects.create(
        isSubmitted=data.get('isSubmitted'),
        isRejected=data.get('isRejected'),
        isReceived=data.get('isReceived'),
        video_id=data.get('videoId') if data.get('videoId') else None,
        image_id=data.get('imageId') if data.get('imageId') else None,
        station=station_name,
        submitted_date=data.get('submittedDate'),
        veh_state=state_ab,
        lic_plate=data.get('licensePlate').upper().replace(" ",""),
        isSent=data.get('isSent'),
        isApproved=data.get('isApproved'),
        isSkipped=data.get('isSkipped'),
        is_notfound = data.get('isNotFound'),
        is_sent_to_adjudication=data.get('isSendToAdjudicatorView'),
        is_unknown=data.get('isUnknown'),
        tattile_id=data.get('tattileId') if data.get('tattileId') else None
    )


def process_media_rejection(model, media_id, is_rejected, reject_id):
    media_data = model.objects.filter(id=media_id).first()
    if media_data:
        media_data.isSubmitted = False
        # media_data.isSkipped = False
        media_data.isRejected = is_rejected
        media_data.reject_id = reject_id if is_rejected else None
        media_data.save()
        

# def process_tattile_media_rejection(model, media_id, is_rejected, reject_id):
#     media_data = model.objects.filter(id=media_id).first()
#     if media_data:
#         media_data.is_submitted = False
#         media_data.is_rejected = is_rejected
#         media_data.reject_id = reject_id if is_rejected else None
#         media_data.save()

def process_tattile_media_rejection(
    model,
    media_id,
    is_rejected,
    reject_id,
    license_plate,
    state_ab,
    station_name,
    camera_date,
    camera_time,
):
    media_data = model.objects.filter(id=media_id).first()
    tattile_obj = model.objects.get(id=media_id)
    reject_data = Rejects.objects.get(id=reject_id)
    if reject_data.description == "Evidence Calibration" or reject_data.id == reject_id:
        media_id = model.objects.get(id=media_id)
        current_date = datetime.now()
        EvidenceCalibrationBin.objects.create(
            license_plate=license_plate,
            vehicle_state=state_ab,
            submitted_date=current_date,
            station=station_name,
            note="",
            tattile=tattile_obj,
            image=None,
            video=None,
            camera_date=camera_date,
            camera_time=camera_time,
        )
    if media_data:
        media_data.is_submitted = False
        media_data.is_rejected = is_rejected
        media_data.reject_id = reject_id if is_rejected else None
        media_data.save()

import json

import re


def extract_json(text: str) -> dict:
    # Remove ```json ... ``` or ``` ... ```
    cleaned = re.sub(r"```(?:json)?", "", text)
    cleaned = cleaned.replace("```", "").strip()
    return json.loads(cleaned)


def classify_vehicle_owner(first_name: str, last_name: str) -> dict:
    prompt = f"""
You are a strict classification engine for US vehicle owner names.

Your task is to classify the owner into exactly ONE of the following categories:
- GOVERNMENT
- EMERGENCY
- PRIVATE_FIRE_SAFETY
- NON_GOVERNMENT
- UNCERTAIN

You MUST follow the rules exactly.
Do NOT be conservative.
Do NOT explain excessively.

================================
GLOBAL OVERRIDE RULES (CRITICAL)
================================

1. COMPANY OVERRIDE (GOVERNMENT ONLY)
If the name contains ANY private company suffix
(INC, LLC, LTD, CORP, LP, CO, COMPANY, HOLDINGS),
the owner is NOT a GOVERNMENT entity.
(This rule does NOT block EMERGENCY classification.)

2. PRIVATE FIRE / SAFETY SERVICE RULE
If the name refers to fire or safety SERVICES
(protection, prevention, investigation, safety, security),
classify as PRIVATE_FIRE_SAFETY.

EXCEPTION:
If the name explicitly indicates a public agency
(e.g., FIRE DEPARTMENT, CITY FIRE, COUNTY FIRE),
classify as EMERGENCY.

3. MEDICAL EMERGENCY SERVICE RULE
If the name indicates emergency medical care or transport
(ambulance, EMS, paramedic, medic, life support, ICU,
emergency medical, emergency medical transport),
classify as EMERGENCY regardless of company suffix.

================================
EMERGENCY SERVICE IDENTIFICATION
================================

Classify as EMERGENCY if the name clearly indicates:
- Law enforcement or policing
- Fire suppression or rescue
- Emergency medical response or transport
- Search, rescue, or disaster response
- Emergency management or public safety operations

A private company suffix does NOT remove EMERGENCY status.

================================
GOVERNMENT (NON-EMERGENCY)
================================

Classify as GOVERNMENT ONLY if:
- The name indicates a public authority or department
- AND none of the emergency indicators apply
- AND no private company suffix is present

================================
NON-GOVERNMENT
================================

Private entities or individuals that are NOT emergency
and NOT private fire/safety services.

================================
UNCERTAIN
================================

Use ONLY if there are ZERO clear indicators.

================================
PRIORITY ORDER (HIGHEST → LOWEST)
================================

1. PRIVATE_FIRE_SAFETY
2. EMERGENCY
3. GOVERNMENT
4. NON_GOVERNMENT
5. UNCERTAIN

================================
OUTPUT REQUIREMENTS (STRICT)
================================

Output MUST be raw JSON only.
Output MUST contain EXACTLY these three fields:

- classification: one of the allowed categories
- reason: a brief factual justification (1 sentence)
- confidence: a number between 0.00 and 1.00

Rules for confidence:
- 0.90 to 1.00 → explicit, unambiguous indicator
- 0.70 to 0.89 → strong but inferred indicator
- 0.50 to 0.69 → weak but sufficient indicator
- NEVER output below 0.50 unless classification is UNCERTAIN

Do NOT include markdown.
Do NOT include extra fields.
- Output MUST be raw JSON only
- Do NOT wrap output in ```json or ``` blocks


Input:
First Name: {first_name}
Last Name: {last_name}

Output JSON format:
{{
  "classification": "<GOVERNMENT | EMERGENCY | PRIVATE_FIRE_SAFETY | NON_GOVERNMENT | UNCERTAIN>",
  "confidence": <number between 0.0 and 1.0>,
  "reason": "<short reason>"
}}
"""

    try:
        client = get_openai_client()

        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=150,
        )
        #  Correct extraction for openai 2.x
        output_text = response.output[0].content[0].text
        return extract_json(output_text)
    except RateLimitError:
        #  Let the view decide what to do
        raise
    except Exception as e:
        return {
            "classification": "UNCERTAIN",
            "confidence": 0.0,
            "reason": f"Error during classification: {str(e)}",
            "action": "MANUAL_REVIEW",
            "source": "GPT-4.1-mini",
        }