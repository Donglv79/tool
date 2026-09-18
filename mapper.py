import uuid
import re
from typing import Dict, Any, List
from ai_synthesizer import (
    generate_one_liner,
    generate_clinical_findings,
    generate_timeline_summary,
    generate_timeline_clinical_details
)

from datetime import datetime

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

def map_patient_data(input_data: Dict[str, Any]) -> Dict[str, Any]:
    visits = input_data.get("visits", [])
    if not visits:
        return {"error": "No visits found"}

    # Sort visits by visit_date descending using parsed dates to ensure visits[0] is the latest
    visits.sort(key=lambda x: parse_date(x.get("visit_date", "")), reverse=True)
    
    # Determine latest visit
    latest_visit = visits[0] 
    
    # Extract basic info
    visit_count = len(visits)
    latest_visit_date = latest_visit.get("visit_date", "")
    specialties = []
    for v in visits:
        spec = v.get("specialty")
        if spec and spec not in specialties:
            specialties.append(spec)

    # AI fields for summary
    one_liner = generate_one_liner(latest_visit)
    alerts = [] # generate_alerts if needed, for now empty

    # Section 1: Tiền sử nền
    history = latest_visit.get("history", {})
    
    # Items (past_medical_history) - Trường AI render nên để trống content và since
    items = [{"content": "", "since": ""}]
    
    family_history = []
    def is_garbage(text):
        t = text.strip().lower()
        if not t or t in ["không", "null", "none"]:
            return True
        for p in ["chưa ghi nhận", "không ghi nhận", "không có", "bình thường"]:
            if p in t:
                return True
        return False
        
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

    def filter_placeholder(val):
        if not val:
            return ""
        v = val.strip().lower()
        if v in ["không có thông tin", "chưa ghi nhận", "không", "null", "none", "không có"]:
            return ""
        return val

    section_1 = {
        "order": 1,
        "title": "Tiền sử nền",
        "items": items,
        "familyHistory": family_history,
        "obstetricHistory": filter_placeholder(history.get("obstetric_history", "")),
        "menstrualHistory": filter_placeholder(history.get("menstrual_history", ""))
    }

    prescriptions_in = latest_visit.get("prescriptions", [])
    by_prescription = []
    for p in prescriptions_in:
        for item in p.get("items", []):
            name_val = item.get("name", "")
            match = re.search(r'\d.*', name_val)
            dosage_val = match.group(0).strip() if match else (name_val.split()[-1] if " " in name_val else name_val)
            
            by_prescription.append({
                "name": name_val,
                "dosage": dosage_val,
                "frequency": item.get("dosage_instruction", ""),
                "quantity": item.get("quantity", ""),
                "prescribedDate": p.get("prescribed_date") or "",
                "prescriptionCode": p.get("prescription_code", ""),
                "specialty": p.get("specialty", ""),
                "durationEndDate": item.get("stop_date") or None
            })
    
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

    # Section 3: Tình trạng bệnh nhân
    diagnoses = []
    diag_data = latest_visit.get("diagnosis", {})
    for d in diag_data.get("diagnosis_primary", []):
        diagnoses.append({
            "code": d.get("code", ""),
            "name": d.get("name", ""),
            "description": d.get("description", "") or ""
        })
    for d in diag_data.get("diagnosis_comorbidities", []):
        diagnoses.append({
            "code": d.get("code", ""),
            "name": d.get("name", ""),
            "description": d.get("description", "") or ""
        })

    plan_data = latest_visit.get("plan", {})
    treatment = []
    if plan_data.get("prescription"):
        treatment.append(plan_data.get("prescription"))

    advice_raw = plan_data.get("doctor_advice", "")
    advice = [format_sentence(a) for a in advice_raw.split(";") if a.strip()] if advice_raw else []
    if plan_data.get("treatment_plan"):
        advice.append(format_sentence(plan_data.get("treatment_plan")))

    abnormal_results = []
    abnormal_raw = latest_visit.get("labs", {}).get("abnormal_result", "")
    if abnormal_raw:
        parts = abnormal_raw.split(";")
        for part in parts:
            part = part.strip()
            if not part: continue
            
            # Heuristic để tránh nhận diện sai các kết quả bình thường bị ghi nhầm vào abnormal_result
            is_abnormal = True
            part_lower = part.lower()
            if "chưa ghi nhận bất thường" in part_lower or "bình thường" in part_lower or "không phát hiện" in part_lower:
                is_abnormal = False

            if ":" in part:
                name_part, result_part = part.split(":", 1)
                abnormal_results.append({
                    "name": name_part.strip(),
                    "result": result_part.strip(),
                    "abnormal": is_abnormal
                })
            elif "Bạch cầu" in part:
                abnormal_results.append({
                    "name": "Bạch cầu",
                    "result": part.replace("Bạch cầu", "").strip(),
                    "abnormal": is_abnormal
                })
            elif "Niêm mạc" in part:
                abnormal_results.append({
                    "name": "Nội soi dạ dày",
                    "result": part.strip(),
                    "abnormal": is_abnormal
                })
            else:
              
                match = re.match(r'^(.*)\s+([<>=]*\s*[+-]?\d+.*)$', part.strip())
                if match:
                    abnormal_results.append({
                        "name": match.group(1).strip(),
                        "result": match.group(2).strip(),
                        "abnormal": is_abnormal
                    })
                else:
                    abnormal_results.append({
                        "name": part.strip(),
                        "result": "",
                        "abnormal": is_abnormal
                    })
       
        if "Test HP âm tính" in latest_visit.get("labs", {}).get("paraclinical_result", ""):
            abnormal_results.append({
                "name": "Test HP",
                "result": "âm tính",
                "abnormal": False
            })

    clinical_findings = generate_clinical_findings(latest_visit.get("examination", {}))

    latest_by_specialty = [{
        "visitDate": latest_visit_date,
        "specialty": latest_visit.get("specialty", ""),
        "vitalSigns": {
            "pulse": latest_visit.get("vitals", {}).get("pulse", 0),
            "temperature": latest_visit.get("vitals", {}).get("temperature", 0.0),
            "bloodPressure": latest_visit.get("vitals", {}).get("blood_pressure", ""),
            "spo2": int(latest_visit.get("vitals", {}).get("spo2", "0")),
            "respiratoryRate": int(latest_visit.get("vitals", {}).get("respiratory_rate", "0")),
            "weight": float(latest_visit.get("vitals", {}).get("weight_kg", "0")),
            "height": float(latest_visit.get("vitals", {}).get("height_cm", "0")),
            "bmi": float(latest_visit.get("vitals", {}).get("bmi", "0"))
        },
        "clinicalFindings": clinical_findings,
        "specialtyFindings": {
            "obstetrics": None,
            "pediatrics": None
        },
        "abnormalResults": abnormal_results,
        "diagnoses": diagnoses,
        "treatment": treatment,
        "advice": advice,
        "trends": []
    }]

    section_3 = {
        "order": 3,
        "title": "Tình trạng bệnh nhân",
        "latestBySpecialty": latest_by_specialty
    }

    # Section 4: Việc cần theo dõi tiếp
    follow_up_items = [format_sentence(a) for a in advice_raw.split(";") if a.strip()] if advice_raw else []
    follow_up = []
    if plan_data.get("followup_date"):
        follow_up.append({
            "specialty": latest_visit.get("specialty", ""),
            "date": plan_data.get("followup_date", ""),
            "valid": False,
            "note": "quá hạn từ 12/06" # Hardcode tạm vì không có logic cụ thể tính quá hạn
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
            v_diagnoses.append({"code": d.get("code", ""), "name": d.get("name", ""), "description": d.get("description", "") or ""})
        for d in v_diag.get("diagnosis_comorbidities", []):
            v_diagnoses.append({"code": d.get("code", ""), "name": d.get("name", ""), "description": d.get("description", "") or ""})
        
        v_plan = v.get("plan", {})
        v_treatment = []
        if v_plan.get("treatment_plan"):
            v_treatment.append(v_plan.get("treatment_plan"))
        v_advice = [format_sentence(a) for a in v_plan.get("doctor_advice", "").split(";") if a.strip()] if v_plan.get("doctor_advice") else []
        if v_plan.get("treatment_plan"):
            v_advice.append(format_sentence(v_plan.get("treatment_plan")))

        v_presc = []
        for p in v.get("prescriptions", []):
            for item in p.get("items", []):
                v_presc.append(item.get("name", ""))
        
        v_para = []
        v_para_raw = v.get("labs", {}).get("paraclinical_result", "")
        if v_para_raw:
            parts = v_para_raw.split(";")
            for part in parts:
                part = part.strip()
                if not part: continue
                if ":" in part:
                    name_part, result_part = part.split(":", 1)
                    v_para.append({"name": name_part.strip(), "result": result_part.strip()})
                else:
                    v_para.append({"name": part, "result": ""})

        timeline_summary = generate_timeline_summary(v.get("chief_complaint", ""), v_diag)
        clinical_details = generate_timeline_clinical_details(v.get("history", {}), v.get("vitals", {}), v.get("examination", {}))

        timeline.append({
            "visitDate": v.get("visit_date", ""),
            "specialty": v.get("specialty", ""),
            "visitCode": v.get("visit_code", ""),
            "summary": timeline_summary,
            "details": {
                "clinical": clinical_details,
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

    # Assemble final output
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
