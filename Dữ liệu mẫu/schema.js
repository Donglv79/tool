{
    "request_id": "string (UUID)",
    "data": {
        "summary": {
            "visitCount": "integer",
            "latestVisitDate": "string",
            "specialties": "string",
            "oneLiner": "string",
            "alerts": [
                {
                    "type": "string",
                    "title": "string",
                    "description": "string",
                    "identifiedDate": "string",
                    "conflict": "boolean",
                    "scopeNote": "string"
                }
            ],
            "sections": [
                {
                    "order": "integer",
                    "title": "string",
                    "items": [
                        {
                            "content": "string",
                            "since": "string (MM/YYYY)"
                        }
                    ],
                    "familyHistory": [
                        "string"
                    ],
                    "obstetricHistory": "string",
                    "menstrualHistory": "string"
                },
                {
                    "order": "integer",
                    "title": "string",
                    "byPrescription": [
                        {
                            "name": "string",
                            "dosage": "string",
                            "frequency": "string",
                            "quantity": "string",
                            "prescribedDate": "string (YYYY-MM-DD)",
                            "prescriptionCode": "string",
                            "specialty": "string",
                            "durationEndDate": "string"
                        }
                    ],
                    "selfReported": [
                        {
                            "name": "string",
                            "dosage": "string",
                            "route": "string",
                            "askedDate": "string (YYYY-MM-DD)"
                        }
                    ]
                },
                {
                    "order": "integer",
                    "title": "string",
                    "latestBySpecialty": [
                        {
                            "visitDate": "string (YYYY-MM-DD)",
                            "specialty": "string",
                            "vitalSigns": {
                                "pulse": "number",
                                "temperature": "number",
                                "bloodPressure": "string",
                                "spo2": "number",
                                "respiratoryRate": "number",
                                "weight": "number",
                                "height": "number",
                                "bmi": "number"
                            },
                            "clinicalFindings": "string",
                            "specialtyFindings": {
                                "obstetrics": "string",
                                "pediatrics": {
                                    "nutrition": "string",
                                    "vaccination": "string",
                                    "motorDevelopment": "string",
                                    "mentalDevelopment": "string"
                                }
                            },
                            "abnormalResults": [
                                {
                                    "name": "string",
                                    "result": "string",
                                    "abnormal": "boolean"
                                }
                            ],
                            "diagnoses": [
                                {
                                    "code": "string",
                                    "name": "string",
                                    "description": "string"
                                }
                            ],
                            "treatment": [
                                "string"
                            ],
                            "advice": [
                                "string"
                            ],
                            "trends": [
                                {
                                    "name": "string",
                                    "from": "string",
                                    "fromDate": "string (YYYY-MM-DD)",
                                    "to": "string",
                                    "toDate": "string (YYYY-MM-DD)"
                                }
                            ]
                        }
                    ]
                },
                {
                    "order": "integer",
                    "title": "string",
                    "followUpItems": [
                        "string"
                    ],
                    "followUp": [
                        {
                            "specialty": "string",
                            "date": "string (YYYY-MM-DD)",
                            "valid": "boolean",
                            "note": "string"
                        }
                    ]
                }
            ]
        },
        "timeline": [
            {
                "visitDate": "string (YYYY-MM-DD)",
                "specialty": "string",
                "visitCode": "string",
                "summary": "string",
                "details": {
                    "clinical": "string",
                    "paraclinical": [
                        {
                            "name": "string",
                            "result": "string"
                        }
                    ],
                    "diagnosis": [
                        {
                            "code": "string",
                            "name": "string",
                            "description": "string"
                        }
                    ],
                    "treatment": [
                        "string"
                    ],
                    "prescription": [
                        "string"
                    ],
                    "specialtyFindings": {
                        "obstetrics": "string",
                        "pediatrics": {
                            "nutrition": "string",
                            "vaccination": "string",
                            "motorDevelopment": "string",
                            "mentalDevelopment": "string"
                        }
                    },
                    "changesFromPrevious": [
                        "string"
                    ],
                    "advice": [
                        "string"
                    ]
                }
            }
        ]
    },
    "errors": {}
}