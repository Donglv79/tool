import uuid
import re
import difflib
from typing import Dict, Any, List
from datetime import datetime, timedelta

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

def calculate_duration_end_date(prescribed_date_str, duration_str):
    if not prescribed_date_str or not duration_str:
        return ""
    try:
        p_date = parse_date(prescribed_date_str)
        if p_date == datetime.min:
            return ""
        
        match = re.search(r'(\d+)\s*(ngày|day)', str(duration_str).lower())
        if match:
            days = int(match.group(1))
            end_date = p_date + timedelta(days=days)
            return end_date.strftime("%Y-%m-%d")
            
        if str(duration_str).isdigit():
            end_date = p_date + timedelta(days=int(duration_str))
            return end_date.strftime("%Y-%m-%d")
    except Exception:
        pass
    return ""

def format_sentence(text):
    text = text.strip()
    if not text:
        return text
    return text[0].upper() + text[1:]

def deduplicate_diagnoses(diags):
    unique_diags = []
    for d in diags:
        code = d.get("code") or ""
        code = code.strip()
        name = d.get("name") or ""
        name = name.strip().lower()
        
        is_duplicate = False
        for u in unique_diags:
            u_code = (u.get("code") or "").strip()
            u_name = (u.get("name") or "").strip().lower()
            
            if code and u_code and code == u_code:
                is_duplicate = True
                break
                
            if name and u_name:
                if name in u_name or u_name in name:
                    is_duplicate = True
                    break
                
                similarity = difflib.SequenceMatcher(None, name, u_name).ratio()
                if similarity > 0.8:
                    is_duplicate = True
                    break
                    
        if not is_duplicate:
            unique_diags.append(d)
    return unique_diags

def map_patient_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
    visits = input_data.get("visits", [])
    if not visits:
        return {"error": "No visits found"}

    visits.sort(key=lambda x: parse_date(x.get("visit_date", "")), reverse=True)
    latest_visit = visits[0] 
    visit_count = len(visits)
    latest_visit_date = latest_visit.get("visit_date", "")
    
    specialties = []
    for v in visits:
        spec = v.get("specialty")
        if spec and spec not in specialties:
            specialties.append(spec)

    # 1. oneLiner (AI: Yes)
    one_liner = "dt: str" 
    
    def is_garbage(text):
        t = str(text).strip().lower()
        if not t or t in ["không", "null", "none"]:
            return True
        for p in ["chưa ghi nhận", "không ghi nhận", "không có", "bình thường", "không có thông tin"]:
            if p in t:
                return True
        return False
        
    history = latest_visit.get("history", {})
    has_allergy = bool(history.get("allergy", "") and not is_garbage(history.get("allergy", "")))
    alerts = []
    if has_allergy:
        alerts.append({
            "type": "Allergy",
            "title": "Dị ứng",
            "description": "dt: str", # AI: Yes
            "identifiedDate": "",
            "conflict": False,
            "scopeNote": "dt: str" # AI: Không chắc chắn
        })

    # Section 1
    items = [{
        "content": "dt: str",
        "since": "dt: str"
    }]
    
    family_history = []
    for v in visits:
        v_hist = v.get("history", {})
        fh_raw = v_hist.get("family_history", "")
        if fh_raw and not is_garbage(fh_raw):
            for part in fh_raw.split(";"):
                if not is_garbage(part):
                    part = part.strip()
                    part = part[0].upper() + part[1:]
                    if part not in family_history:
                        family_history.append(part)

    section_1 = {
        "order": 1,
        "title": "Tiền sử nền",
        "items": items,
        "familyHistory": family_history,
        "obstetricHistory": "dt: str", 
        "menstrualHistory": "dt: str"  
    }

    # Section 2
    all_prescriptions = []
    for v in visits:
        for p in v.get("prescriptions", []):
            all_prescriptions.append(p)
            
    all_prescriptions.sort(key=lambda x: parse_date(x.get("prescribed_date", "")), reverse=True)
    latest_prescription = all_prescriptions[0] if all_prescriptions else None

    by_prescription = [{
        "name": "dt: str", 
        "dosage": "dt: str",
        "frequency": "dt: str",
        "quantity": "dt: str",
        "prescribedDate": "dt: str",
        "prescriptionCode": "dt: str",
        "specialty": "dt: str",
        "durationEndDate": "dt: str"
    }]
    
    current_meds = history.get("current_medications", [])
    self_reported = []
    for m in current_meds:
        self_reported.append({
            "name": m.get("name", ""),
            "dosage": m.get("dosage", ""),
            "route": m.get("route", ""),
            "askedDate": latest_visit.get("visit_date", "")
        })

    section_2 = {
        "order": 2,
        "title": "Thuốc đang sử dụng",
        "byPrescription": by_prescription,
        "selfReported": self_reported
    }

    # Section 3
    now = datetime.now()
    selected_visits = [latest_visit]
    for v in visits:
        if v in selected_visits:
            continue
        has_valid_prescription = False
        for p in v.get("prescriptions", []):
            for item in p.get("items", []):
                end_date_str = calculate_duration_end_date(p.get("prescribed_date", ""), item.get("duration", ""))
                if end_date_str:
                    end_date_obj = parse_date(end_date_str)
                    if end_date_obj != datetime.min and end_date_obj >= now:
                        has_valid_prescription = True
                        break
            if has_valid_prescription: break
        if has_valid_prescription:
            selected_visits.append(v)
            
    selected_visits.sort(key=lambda x: parse_date(x.get("visit_date", "")), reverse=True)

    latest_by_specialty = []
    for v_sel in selected_visits:
        v_diag_sel = v_sel.get("diagnosis", {})
        diagnoses_sel = []
        for d in v_diag_sel.get("diagnosis_primary", []):
            diagnoses_sel.append({
                "code": d.get("code", ""),
                "name": d.get("name", ""),
                "description": "dt: str"
            })
        for d in v_diag_sel.get("diagnosis_comorbidities", []):
            diagnoses_sel.append({
                "code": d.get("code", ""),
                "name": d.get("name", ""),
                "description": "dt: str"
            })
        diagnoses_sel = deduplicate_diagnoses(diagnoses_sel)

        v_plan_sel = v_sel.get("plan", {})
        treatment_sel = []
        if v_plan_sel.get("treatment_plan"):
            treatment_sel.append(v_plan_sel.get("treatment_plan"))

        advice_raw_sel = v_plan_sel.get("doctor_advice", "")
        advice_sel = [format_sentence(a) for a in advice_raw_sel.split(";") if a.strip()] if advice_raw_sel else []

        abnormal_results_sel = [{
            "name": "dt: str", 
            "result": "dt: str",
            "abnormal": "dt: bool"
        }]

        pulse = v_sel.get("vitals", {}).get("pulse", 0)
        pulse = float(pulse) if str(pulse).replace('.','',1).isdigit() else 0

        latest_by_specialty.append({
            "visitDate": v_sel.get("visit_date", ""),
            "specialty": v_sel.get("specialty", ""),
            "vitalSigns": {
                "pulse": pulse,
                "temperature": float(v_sel.get("vitals", {}).get("temperature", "0") or 0),
                "bloodPressure": str(v_sel.get("vitals", {}).get("blood_pressure", "")),
                "spo2": int(v_sel.get("vitals", {}).get("spo2", "0") or 0),
                "respiratoryRate": int(v_sel.get("vitals", {}).get("respiratory_rate", "0") or 0),
                "weight": float(v_sel.get("vitals", {}).get("weight_kg", "0") or 0),
                "height": float(v_sel.get("vitals", {}).get("height_cm", "0") or 0),
                "bmi": float(v_sel.get("vitals", {}).get("bmi", "0") or 0)
            },
            "clinicalFindings": "dt: str",
            "specialtyFindings": {
                "obstetrics": None, 
                "pediatrics": None
            },
            "abnormalResults": abnormal_results_sel,
            "diagnoses": diagnoses_sel,
            "treatment": treatment_sel,
            "advice": advice_sel,
            "trends": [{
                "name": "dt: str",
                "from": "dt: str",
                "fromDate": "dt: str",
                "to": "dt: str",
                "toDate": "dt: str"
            }]
        })

    section_3 = {
        "order": 3,
        "title": "Tình trạng bệnh nhân",
        "latestBySpecialty": latest_by_specialty
    }

    # Section 4
    plan_data = latest_visit.get("plan", {})
    follow_up_items = []
    if plan_data.get("doctor_advice"):
        advice_raw = plan_data.get("doctor_advice", "")
        spec = latest_visit.get("specialty", "")
        if spec:
            follow_up_items.append(f"{spec}: {format_sentence(advice_raw)}")
        else:
            follow_up_items.append(format_sentence(advice_raw))
    
    follow_up = []
    if plan_data.get("followup_date"):
        follow_up.append({
            "specialty": latest_visit.get("specialty", ""),
            "date": plan_data.get("followup_date", ""),
            "note": "" 
        })
    
    section_4 = {
        "order": 4,
        "title": "Việc cần theo dõi tiếp",
        "followUpItems": follow_up_items,
        "followUp": follow_up
    }

    # Timeline
    timeline = []
    for v in visits:
        v_diag = v.get("diagnosis", {})
        v_diagnoses = []
        for d in v_diag.get("diagnosis_primary", []):
            v_diagnoses.append({"code": d.get("code", ""), "name": d.get("name", ""), "description": "dt: str"}) 
        for d in v_diag.get("diagnosis_comorbidities", []):
            v_diagnoses.append({"code": d.get("code", ""), "name": d.get("name", ""), "description": "dt: str"}) 
        v_diagnoses = deduplicate_diagnoses(v_diagnoses)
        
        v_plan = v.get("plan", {})
        v_treatment = []
        if v_plan.get("treatment_plan"):
            v_treatment.append(v_plan.get("treatment_plan"))
        v_advice = [format_sentence(a) for a in v_plan.get("doctor_advice", "").split(";") if a.strip()] if v_plan.get("doctor_advice") else []

        v_presc = ["dt: str"]
        
        v_para = [{"name": "dt: str", "result": "dt: str"}]

        timeline.append({
            "visitDate": v.get("visit_date", ""),
            "specialty": v.get("specialty", ""),
            "visitCode": v.get("visit_code", ""),
            "summary": "dt: str",
            "details": {
                "clinical": "dt: str",
                "paraclinical": v_para,
                "diagnosis": v_diagnoses,
                "treatment": v_treatment,
                "prescription": v_presc,
                "specialtyFindings": {
                    "obstetrics": None, 
                    "pediatrics": None
                },
                "changesFromPrevious": [],
                "advice": v_advice
            }
        })

    output = {
        "request_id": str(uuid.uuid4()),
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
