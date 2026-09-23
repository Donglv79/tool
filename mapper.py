import difflib
import re
import uuid
from datetime import datetime
from typing import Any, Dict


AI_LIST = "dt: list"
AI_STR = "dt: str"

GARBAGE_VALUES = {"không", "null", "none", "[]", "{}"}
GARBAGE_PHRASES = (
    "chưa ghi nhận",
    "không ghi nhận",
    "không có",
    "bình thường",
    "không có thông tin",
    "không ghi nhận bất thường",
    "chưa ghi nhận bất thường",
    "không bất thường",
)


def parse_date(date_str):
    if not date_str:
        return datetime.min
    if 'T' in date_str:
        date_str = date_str.split('T')[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return datetime.min


def format_sentence(text):
    text = text.strip()
    if not text:
        return text
    return text[0].upper() + text[1:]


def _is_garbage(data):
    if not data:
        return True

    if isinstance(data, dict):
        return all(_is_garbage(value) for value in data.values())

    if isinstance(data, list):
        return all(_is_garbage(value) for value in data)

    text = str(data).strip().lower()
    if text in GARBAGE_VALUES or text in GARBAGE_PHRASES:
        return True

    return any(
        phrase in text and len(text) <= len(phrase) + 15
        for phrase in GARBAGE_PHRASES
    )


def deduplicate_diagnoses(diags):
    unique_diags = []
    for d in diags:
        code = d.get("code") or ""
        code = code.strip()
        name = d.get("name") or ""
        name = name.strip().lower()
        desc = d.get("description")
        
        is_duplicate = False
        for u in unique_diags:
            u_code = (u.get("code") or "").strip()
            u_name = (u.get("name") or "").strip().lower()
            
            is_match = False
            if code and u_code and code == u_code:
                is_match = True
            elif name and u_name:
                if name in u_name or u_name in name:
                    is_match = True
                elif difflib.SequenceMatcher(None, name, u_name).ratio() > 0.8:
                    is_match = True
                    
            if is_match:
                is_duplicate = True
                if (u.get("description") is None or u.get("description") == "") and desc:
                    u["description"] = desc
                break
                    
        if not is_duplicate:
            unique_diags.append(d)
    return unique_diags


def _build_diagnoses(diagnosis):
    diagnoses = []
    for key in ("diagnosis_primary", "diagnosis_comorbidities"):
        for item in diagnosis.get(key, []):
            description = item.get("description")
            diagnoses.append({
                "code": item.get("code", ""),
                "name": item.get("name", ""),
                "description": description if description else None,
            })
    return deduplicate_diagnoses(diagnoses)


def _build_treatment(plan):
    treatment = []
    for part in (plan.get("treatment_plan") or "").split(";"):
        part = part.strip()
        if part and not _is_garbage(part):
            treatment.append(format_sentence(part))
    return treatment


def _is_active_prescription_item(item, now):
    stop_date = item.get("stop_date")
    if not stop_date:
        return False
    stop_date_obj = parse_date(stop_date)
    return stop_date_obj != datetime.min and stop_date_obj >= now


def _has_active_prescription(visit, now):
    return any(
        _is_active_prescription_item(item, now)
        for prescription in visit.get("prescriptions", [])
        for item in prescription.get("items", [])
    )


def _build_prescription_summaries(visit):
    summaries = []
    for prescription in visit.get("prescriptions", []):
        for item in prescription.get("items", []):
            name = str(item.get("name") or "").strip()
            if not name:
                continue

            parts = [name]
            frequency = _abbreviate_frequency(
                _extract_frequency_for_timeline(item.get("dosage_instruction"))
            )
            if frequency:
                parts.append(frequency)

            duration = item.get("duration")
            if duration:
                parts.append(f"({duration})")

            summaries.append(" ".join(parts))
    return summaries


def _extract_frequency_for_timeline(instruction):
    """Bỏ nhãn route/prefix và route-code khỏi dosage instruction."""
    text = str(instruction or "").strip()
    if not text:
        return ""

    route_words = (
        r"uống|tiêm|bôi|hít|nhỏ|ngậm|truyền|"
        r"dùng ngoài|ngoài da|po|iv|im|sc|sq|sl|oral|topical"
    )
    text = re.sub(
        rf"^\s*đường\s*dùng\s*:\s*(?:{route_words})\s*[,;|:-]?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*[,;|]\s*(?:PO|IV|IM|SC|SQ|SL|ORAL|TOPICAL)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text.strip()


def _abbreviate_frequency(instruction):
    """Rút dosage instruction thành tag tần suất ngắn cho timeline."""
    text = str(instruction or "").strip().lower()
    if not text:
        return ""

    explicit = re.search(r"(?<!\d)(\d+)\s*lần\s*/\s*ngày\b", text)
    if not explicit:
        explicit = re.search(r"\bngày\s+(\d+)\s*lần\b", text)
    if explicit:
        return f"x{explicit.group(1)}/ngày"

    every_hours = re.search(r"\bmỗi\s+(\d+)\s*giờ\b", text)
    if every_hours:
        hours = int(every_hours.group(1))
        if hours and 24 % hours == 0:
            return f"x{24 // hours}/ngày"

    for period in ("sáng", "trưa", "chiều", "tối"):
        if re.search(rf"\bbuổi\s+{period}\b", text):
            return f"x1/{period}"

    if re.search(r"/\s*ngày\b", text):
        return "x1/ngày"

    return ""


def _parse_paraclinical_results(value):
    """Chuẩn hóa paraclinical_result thành [{name, result}]."""
    if _is_garbage(value):
        return []

    if isinstance(value, list):
        results = []
        for item in value:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            result = str(item.get("result") or "").strip()
            if name and result:
                results.append({"name": name, "result": result})
        return results

    if not isinstance(value, str):
        return []

    results = []
    for part in value.split(";"):
        part = part.strip()
        if not part:
            continue

        if ":" in part:
            name, result = part.split(":", 1)
            name, result = name.strip(), result.strip()
        else:
            match = re.match(
                r"^(?P<name>.+?)\s+(?P<result>[+-]?\d+(?:[.,]\d+)?(?:\s*%|\s+.*)?)$",
                part,
            )
            if not match:
                continue
            name = match.group("name").strip()
            result = match.group("result").strip()

        if name and result:
            results.append({"name": name, "result": result})
    return results


def _compute_trends(current_visit, all_visits):
    """So sánh chỉ số giữa lượt hiện tại và lượt trước liền kề cùng specialty (Non-AI, No.57-62)."""
    specialty = current_visit.get("specialty", "")
    current_date = parse_date(current_visit.get("visit_date", ""))
    
    # Tìm lượt trước cùng specialty (lượt liền kề)
    prev_visit = None
    for v in all_visits:
        if v.get("specialty") == specialty and v is not current_visit:
            v_date = parse_date(v.get("visit_date", ""))
            if v_date < current_date and v_date != datetime.min:
                if prev_visit is None or v_date > parse_date(prev_visit.get("visit_date", "")):
                    prev_visit = v
                    
    if prev_visit is None:
        return []
    
    trends = []
    
    # 1. Sinh hiệu
    vital_map = {
        "blood_pressure": "Huyết áp",
        "weight_kg": "Cân nặng"
    }
    
    cur_vitals = current_visit.get("vitals", {})
    prev_vitals = prev_visit.get("vitals", {})
    
    for key, label in vital_map.items():
        cur_val = cur_vitals.get(key)
        prev_val = prev_vitals.get(key)
        
        if cur_val is None or prev_val is None:
            continue
        cur_str = str(cur_val).strip()
        prev_str = str(prev_val).strip()
        if not cur_str or cur_str in ["0", "0.0", ""] or not prev_str or prev_str in ["0", "0.0", ""]:
            continue
        
        if cur_str != prev_str:
            trends.append({
                "name": label,
                "from": prev_str,
                "fromDate": prev_visit.get("visit_date", ""),
                "to": cur_str,
                "toDate": current_visit.get("visit_date", "")
            })
            
    # 2. Cận lâm sàng
    cur_labs = current_visit.get("labs") or {}
    prev_labs = prev_visit.get("labs") or {}
    cur_para = _parse_paraclinical_results(cur_labs.get("paraclinical_result"))
    prev_para = _parse_paraclinical_results(prev_labs.get("paraclinical_result"))

    for current_result in cur_para:
        current_name = current_result["name"]
        current_value = current_result["result"]
        for previous_result in prev_para:
            previous_name = previous_result["name"]
            previous_value = previous_result["result"]

            if previous_name.casefold() == current_name.casefold() and previous_value:
                if current_value != previous_value:
                    trends.append({
                        "name": current_name,
                        "from": previous_value,
                        "fromDate": prev_visit.get("visit_date", ""),
                        "to": current_value,
                        "toDate": current_visit.get("visit_date", "")
                    })
                break

    return trends


def _extract_dosage_frequency(instruction):
    """Tách tần suất/cách dùng từ dosage_instruction (No.22). Theo yêu cầu mới, không tách mà lấy toàn bộ chuỗi."""
    if not instruction:
        return ""
    return instruction


def _extract_dosage_from_name(name):
    """Tách liều (hàm lượng) từ tên thuốc (No.21)."""
    if not name:
        return ""
    match = re.search(
        r"(\d+(?:[.,]\d+)?\s*(?:mcg|mg|ml|g|đơn vị|IU|UI))(?=$|[\s,;/()])",
        name,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()
    return ""


def _build_pediatrics(visit):
    """Map pediatrics từ examination fields, lấy mọi lúc không check specialty."""
    exam = visit.get("examination") or {}
    
    return {
        "nutrition": exam.get("nutrition_assessment") or exam.get("nutrition assessment") or "",
        "vaccination": exam.get("vaccination_assessment") or exam.get("vaccination assessment") or "",
        "motorDevelopment": exam.get("motor_development") or exam.get("motor development") or "",
        "mentalDevelopment": exam.get("mental_development") or exam.get("mental development") or ""
    }


def _build_obstetrics(visit):
    """Chỉ trả nội dung khám chuyên khoa cho lượt khám Sản; khoa khác trả None."""
    specialty = str(visit.get("specialty") or "").strip().casefold()
    if "sản" not in specialty:
        return None

    examination = visit.get("examination") or {}
    obstetrics = examination.get("specialty_examination")
    if not isinstance(obstetrics, str) or not obstetrics.strip():
        return None

    return obstetrics.strip()


def map_patient_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
    visits = input_data.get("visits", [])
    if not visits:
        return {"error": "No visits found"}

    visits.sort(key=lambda x: parse_date(x.get("visit_date", "")), reverse=True)
    latest_visit_date_str = visits[0].get("visit_date", "")
    latest_visits = [v for v in visits if v.get("visit_date", "") == latest_visit_date_str]
    latest_visit = visits[0]
    visit_count = len(visits)
    latest_visit_date = latest_visit.get("visit_date", "")
    
    specialties = []
    for v in visits:
        spec = v.get("specialty")
        if spec and spec not in specialties:
            specialties.append(spec)

    history = latest_visit.get("history", {})
    now = datetime.now()
    
    # ============================================================
    # 1. oneLiner (AI: Yes, No.5)
    # ============================================================
    one_liner = AI_STR
    
    # ============================================================
    # 2. alerts (AI: Yes, No.6-12 — toàn bộ object là AI)
    # ============================================================
    alerts = AI_LIST

    # ============================================================
    # 3. Section 1: Tiền sử nền
    # ============================================================
    # items (AI: Yes, No.15-16)
    items = AI_LIST
    
    # familyHistory (AI: Yes, No.17 — Dev confirm Y)
    family_history = AI_LIST

    # obstetricHistory (AI: Yes, No.18 — Dev confirm Y)
    # menstrualHistory (AI: Yes, No.19 — Dev confirm Y)
    section_1 = {
        "order": 1,
        "title": "Tiền sử nền",
        "items": items,
        "familyHistory": family_history,
        "obstetricHistory": AI_STR,
        "menstrualHistory": AI_STR
    }

    # ============================================================
    # 4. Section 2: Thuốc đang sử dụng
    # ============================================================
    # A. byPrescription (Non-AI, No.20-27)
    all_prescriptions = [
        prescription
        for visit in visits
        for prescription in visit.get("prescriptions", [])
    ]
    all_prescriptions.sort(key=lambda x: parse_date(x.get("prescribed_date", "")), reverse=True)
    latest_date_str = all_prescriptions[0].get("prescribed_date", "") if all_prescriptions else ""

    temp_items = []
    for p in all_prescriptions:
        prescribed_date = p.get("prescribed_date", "")
        is_latest = (prescribed_date == latest_date_str) and latest_date_str != ""
        
        for item in p.get("items", []):
            duration_end_date = item.get("stop_date")
            is_active = _is_active_prescription_item(item, now)
            
            if is_latest or is_active:
                instruction = item.get("dosage_instruction", "")
                name_val = item.get("name", "")
                dosage_extracted = _extract_dosage_from_name(name_val)
                frequency_extracted = _extract_dosage_frequency(instruction)
                
                mapped_item = {
                    "name": name_val,                                   # Non-AI (No.20): out = in
                    "dosage": dosage_extracted,                          # Non-AI (No.21): tách liều từ name
                    "frequency": frequency_extracted,                    # Non-AI (No.22): tách frequency từ dosage_instruction
                    "quantity": item.get("quantity", ""),                # Non-AI (No.23): out = in
                    "prescribedDate": prescribed_date,                  # Non-AI (No.24): out = in
                    "prescriptionCode": p.get("prescription_code", ""), # Non-AI (No.25): out = in
                    "specialty": p.get("specialty", ""),                 # Non-AI (No.26): out = in
                    "durationEndDate": duration_end_date                # Non-AI (No.27): tính toán
                }
                
                temp_items.append({
                    "is_active": is_active,
                    "date_obj": parse_date(prescribed_date),
                    "data": mapped_item
                })

    temp_items.sort(key=lambda x: (x["is_active"], x["date_obj"]), reverse=True)
    by_prescription = [x["data"] for x in temp_items]
    
    # B. selfReported (Non-AI, No.28-31)
    self_reported = [
        {
            "name": m.get("name", ""),
            "dosage": m.get("dosage", ""),
            "route": m.get("route", ""),
            "askedDate": latest_visit.get("visit_date", "")
        }
        for m in history.get("current_medications", [])
    ]

    section_2 = {
        "order": 2,
        "title": "Thuốc đang sử dụng",
        "byPrescription": by_prescription,
        "selfReported": self_reported
    }

    # ============================================================
    # 5. Section 3: Tình trạng bệnh nhân (latestBySpecialty)
    # ============================================================
    # Lọc visits: lượt mới nhất + lượt có thuốc còn hạn (Non-AI, No.32)
    selected_visits = latest_visits[:]
    for v in visits:
        if v not in selected_visits and _has_active_prescription(v, now):
            selected_visits.append(v)
            
    selected_visits.sort(key=lambda x: parse_date(x.get("visit_date", "")), reverse=True)

    latest_by_specialty = []
    for v_sel in selected_visits:
        diagnoses_sel = _build_diagnoses(v_sel.get("diagnosis", {}))

        # treatment (Non-AI, No.55): Tách hướng điều trị từ plan
        v_plan_sel = v_sel.get("plan", {})
        treatment_sel = _build_treatment(v_plan_sel)

        # advice (Non-AI, No.56): Giữ nguyên lời dặn từ doctor_advice
        advice_sel = []
        advice_text = str(v_plan_sel.get("doctor_advice", "")).strip()
        if advice_text and not _is_garbage(advice_text):
            advice_sel.append(format_sentence(advice_text))

        # vitalSigns (Non-AI, No.35-42)
        vitals = v_sel.get("vitals", {})
        pulse = vitals.get("pulse", 0)
        pulse = float(pulse) if str(pulse).replace(".", "", 1).isdigit() else 0

        latest_by_specialty.append({
            "visitDate": v_sel.get("visit_date", ""),
            "specialty": v_sel.get("specialty", ""),
            "vitalSigns": {
                "pulse": pulse,
                "temperature": float(vitals.get("temperature", "0") or 0),
                "bloodPressure": str(vitals.get("blood_pressure", "")),
                "spo2": int(vitals.get("spo2", "0") or 0),
                "respiratoryRate": int(vitals.get("respiratory_rate", "0") or 0),
                "weight": float(vitals.get("weight_kg", "0") or 0),
                "height": float(vitals.get("height_cm", "0") or 0),
                "bmi": float(vitals.get("bmi", "0") or 0)
            },
            "clinicalFindings": AI_STR,                         # AI (No.43)
            "specialtyFindings": {
                "obstetrics": _build_obstetrics(v_sel),        # Chỉ phiếu Sản; khoa khác trả null (No.44)
                "pediatrics": _build_pediatrics(v_sel)                  # Non-AI (No.45-48) hoặc None
            },
            "abnormalResults": AI_LIST,                         # AI (No.49-51)
            "diagnoses": diagnoses_sel,
            "treatment": treatment_sel,
            "advice": advice_sel,
            "trends": _compute_trends(v_sel, visits)                    # Non-AI (No.57-62)
        })

    section_3 = {
        "order": 3,
        "title": "Tình trạng bệnh nhân",
        "latestBySpecialty": latest_by_specialty
    }

    # ============================================================
    # 6. Section 4: Việc cần theo dõi tiếp
    # ============================================================
    # followUpItems (AI: Yes, No.63 — Dev confirm Y)
    follow_up_items = AI_LIST
    
    # followUp (Non-AI, No.64-68)
    follow_up = []
    for lv in selected_visits:
        lv_plan = lv.get("plan", {})
        if lv_plan.get("followup_date"):
            fu_date_str = lv_plan.get("followup_date", "")
            lv_visit_date_str = lv.get("visit_date", "")
            
            fu_date_obj = parse_date(fu_date_str)
            lv_date_obj = parse_date(lv_visit_date_str)
            
            fu_note = ""
            if fu_date_obj == datetime.min or lv_date_obj == datetime.min:
                fu_valid = False
                fu_note = "Không đủ dữ liệu xác định tính hợp lệ"
            elif fu_date_obj > lv_date_obj:
                fu_valid = True
                if fu_date_obj.date() < now.date():
                    fu_note = f"quá hạn từ {fu_date_obj.strftime('%d/%m')}"
            else:
                fu_valid = False
                fu_note = "Ngày hẹn không hợp lệ (trước hoặc bằng ngày khám)"
            
            # Khử trùng theo specialty + date
            is_duplicate = any(
                existing["specialty"] == lv.get("specialty", "")
                and existing["date"] == fu_date_str
                for existing in follow_up
            )
            if not is_duplicate:
                follow_up.append({
                    "specialty": lv.get("specialty", ""),
                    "date": fu_date_str,
                    "valid": fu_valid,
                    "note": fu_note
                })
    
    section_4 = {
        "order": 4,
        "title": "Việc cần theo dõi tiếp",
        "followUpItems": follow_up_items,
        "followUp": follow_up
    }

    # ============================================================
    # 7. Timeline (Lịch sử các lần khám)
    # ============================================================
    timeline = []
    for v in visits:
        # diagnosis (Non-AI, No.77-79)
        v_diagnoses = _build_diagnoses(v.get("diagnosis", {}))
        
        v_plan = v.get("plan", {})

        # treatment (Non-AI, No.80): Tách hướng điều trị, bảo toàn ý nguồn
        v_treatment = _build_treatment(v_plan)

        # prescription (Non-AI, No.81 — Dev confirm N): Tóm tắt đơn thuốc của chính lượt
        v_presc = _build_prescription_summaries(v)

        timeline.append({
            "visitDate": v.get("visit_date", ""),
            "specialty": v.get("specialty", ""),
            "visitCode": v.get("visit_code", ""),
            "summary": AI_STR,                                     # AI (No.73)
            "details": {
                "clinical": AI_STR,                                # AI (No.74)
                "paraclinical": AI_LIST,                           # AI (No.75-76)
                "diagnosis": v_diagnoses,                                   # Non-AI (No.77-79)
                "treatment": v_treatment,                                   # Non-AI (No.80)
                "prescription": v_presc,                                    # Non-AI (No.81)
                "specialtyFindings": {
                    "obstetrics": _build_obstetrics(v),            # Chỉ phiếu Sản; khoa khác trả null (No.82)
                    "pediatrics": _build_pediatrics(v)              # Non-AI (No.83-86)
                },
                "changesFromPrevious": AI_LIST,                     # AI (No.87)
                "advice": AI_LIST                                  # AI (No.88)
            }
        })

    output = {
        "request_id": input_data.get("request_id", str(uuid.uuid4())),
        "data": {
            "summary": {
                "visitCount": visit_count,
                "latestVisitDate": latest_visit_date,
                "specialties": specialties,
                "oneLiner": one_liner,
                "alerts": alerts,
                "sections": [section_1, section_2, section_3, section_4]
            },
            "timeline": timeline
        },
        "errors": {}
    }

    return output
