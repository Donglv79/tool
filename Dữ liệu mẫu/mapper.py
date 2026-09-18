import json
import uuid

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, filepath):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def dedupe_list(lst):
    return list(dict.fromkeys(lst))

def convert_type(val):
    if val is None:
        return None
    # Try converting to int if possible, or float, else string
    try:
        return int(val)
    except ValueError:
        try:
            return float(val)
        except ValueError:
            return val

def format_sentence(text):
    text = text.strip()
    if not text:
        return text
    return text[0].upper() + text[1:]

def main():
    input_data = load_json('input_that.json')
    visits = input_data.get('visits', [])
    
    # Sort visits by date descending
    visits.sort(key=lambda x: x.get('visit_date', ''), reverse=True)
    
    # Summary Info
    visit_count = len(visits)
    specialties = dedupe_list([v.get('specialty') for v in visits if v.get('specialty')])
    latest_visit_date = visits[0].get('visit_date', '') if visits else ''
    
    # Section 1: Tiền sử nền
    past_medical_history = []
    family_history = []
    obstetric_history = []
    menstrual_history = []
    
    for v in visits:
        hist = v.get('history', {})
        pmh = hist.get('past_medical_history')
        if pmh and pmh not in [i['content'] for i in past_medical_history]:
            past_medical_history.append({"content": pmh, "since": ""})
            
        fh = hist.get('family_history')
        if fh and fh not in family_history:
            family_history.append(fh)
            
        spec = v.get('specialty', '')
        if 'sản' in spec.lower():
            oh = hist.get('obstetric_history')
            if oh and oh not in obstetric_history:
                obstetric_history.append(oh)
            mh = hist.get('menstrual_history')
            if mh and mh not in menstrual_history:
                menstrual_history.append(mh)
                
    # Section 2: Thuốc đang sử dụng
    by_prescription = []
    self_reported = []
    
    if visits:
        latest_visit = visits[0]
        # byPrescription
        for p in latest_visit.get('prescriptions', []):
            for item in p.get('items', []):
                by_prescription.append({
                    "name": item.get('name', ''),
                    "dosage": item.get('dosage_instruction', ''),
                    "frequency": "", 
                    "prescribedDate": p.get('prescribed_date', ''),
                    "prescriptionCode": p.get('prescription_code', ''),
                    "specialty": p.get('specialty', ''),
                    "durationEndDate": item.get('stop_date') if item.get('stop_date') else None
                })
        
        # selfReported
        hist = latest_visit.get('history', {})
        if hist.get('medication_status') == True:
            for med in hist.get('current_medications', []):
                self_reported.append({
                    "name": med.get('name', ''),
                    "dosage": med.get('dosage', ''),
                    "route": med.get('route', ''),
                    "askedDate": latest_visit.get('visit_date', '')
                })

    # Section 3: Tình trạng bệnh nhân
    latest_by_specialty = []
    seen_specs = set()
    for v in visits:
        spec = v.get('specialty', '')
        if spec not in seen_specs:
            seen_specs.add(spec)
            vitals = v.get('vitals', {})
            diags = v.get('diagnosis', {})
            dp = diags.get('diagnosis_primary', [])
            dc = diags.get('diagnosis_comorbidities', [])
            
            all_diags = []
            for d in dp + dc:
                all_diags.append({
                    "code": d.get('code', ''),
                    "name": d.get('name', ''),
                    "description": d.get('description', '') or ""
                })
                
            plan = v.get('plan', {})
            treatment = []
            if plan.get('prescription') and plan.get('prescription') != 'Không':
                treatment.append(plan.get('prescription'))
            if plan.get('treatment_plan'):
                treatment.append(plan.get('treatment_plan'))
                
            advice = []
            if plan.get('doctor_advice'):
                advice.extend([format_sentence(a) for a in plan.get('doctor_advice').split(";") if a.strip()])
            
            latest_by_specialty.append({
                "visitDate": v.get('visit_date', ''),
                "specialty": spec,
                "vitalSigns": {
                    "pulse": convert_type(vitals.get('pulse')),
                    "temperature": convert_type(vitals.get('temperature')),
                    "bloodPressure": vitals.get('blood_pressure', ''),
                    "spo2": convert_type(vitals.get('spo2')),
                    "respiratoryRate": convert_type(vitals.get('respiratory_rate')),
                    "weight": convert_type(vitals.get('weight_kg')),
                    "height": convert_type(vitals.get('height_cm')),
                    "bmi": convert_type(vitals.get('bmi'))
                },
                "clinicalFindings": "",
                "specialtyFindings": {},
                "abnormalResults": [],
                "diagnoses": all_diags,
                "treatment": treatment,
                "advice": advice,
                "trends": []
            })
            
    # Section 4: Việc cần theo dõi tiếp
    followup_items = []
    followups = []
    if visits:
        latest_plan = visits[0].get('plan', {})
        if latest_plan.get('doctor_advice'):
            followup_items.extend([format_sentence(a) for a in latest_plan.get('doctor_advice').split(";") if a.strip()])
        if latest_plan.get('followup_date'):
            followups.append({
                "specialty": visits[0].get('specialty', ''),
                "date": latest_plan.get('followup_date'),
                "valid": True,
                "note": ""
            })
            
    sections = [
        {
            "order": 1,
            "title": "Tiền sử nền",
            "items": past_medical_history,
            "familyHistory": family_history,
            "obstetricHistory": " | ".join(obstetric_history),
            "menstrualHistory": " | ".join(menstrual_history)
        },
        {
            "order": 2,
            "title": "Thuốc đang sử dụng",
            "byPrescription": by_prescription,
            "selfReported": self_reported
        },
        {
            "order": 3,
            "title": "Tình trạng bệnh nhân",
            "latestBySpecialty": latest_by_specialty
        },
        {
            "order": 4,
            "title": "Việc cần theo dõi tiếp",
            "followUpItems": followup_items,
            "followUp": followups
        }
    ]
    
    # Timeline
    timeline = []
    for v in visits:
        diags = v.get('diagnosis', {})
        dp = diags.get('diagnosis_primary', [])
        dc = diags.get('diagnosis_comorbidities', [])
        all_diags = []
        for d in dp + dc:
            all_diags.append({
                "code": d.get('code', ''),
                "name": d.get('name', ''),
                "description": d.get('description', '') or ""
            })
            
        plan = v.get('plan', {})
        treatment = []
        if plan.get('treatment_plan'):
            treatment.append(plan.get('treatment_plan'))
            
        presc_names = []
        for p in v.get('prescriptions', []):
            for item in p.get('items', []):
                presc_names.append(item.get('name', ''))
                
        advice = []
        if plan.get('doctor_advice'):
            advice.extend([format_sentence(a) for a in plan.get('doctor_advice').split(";") if a.strip()])
            
        timeline.append({
            "visitDate": v.get('visit_date', ''),
            "specialty": v.get('specialty', ''),
            "visitCode": v.get('visit_code', ''),
            "summary": "",
            "details": {
                "clinical": "",
                "paraclinical": [],
                "diagnosis": all_diags,
                "treatment": treatment,
                "prescription": presc_names,
                "specialtyFindings": {},
                "changesFromPrevious": [],
                "advice": advice
            }
        })
        
    output = {
        "request_id": input_data.get('request_id', str(uuid.uuid4())),
        "data": {
            "summary": {
                "visitCount": visit_count,
                "latestVisitDate": latest_visit_date,
                "specialties": specialties,
                "oneLiner": "",
                "alerts": [],
                "sections": sections
            },
            "timeline": timeline
        },
        "errors": {}
    }
    
    save_json(output, 'output_thayt.json')
    print("Mapping completed successfully.")

if __name__ == '__main__':
    main()
