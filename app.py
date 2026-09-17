import json
import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from mapper import map_patient_data

app = FastAPI(title="Mapping Tool API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/process-json")
async def process_json(file: UploadFile = File(...)):
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Vui lòng upload file JSON hợp lệ.")
    
    try:
        content = await file.read()
        input_data = json.loads(content.decode("utf-8"))
        
        output_data = map_patient_data(input_data)
        
        return JSONResponse(content=output_data, headers={
            "Content-Disposition": f"attachment; filename=output_{file.filename}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-raw-json")
async def process_raw_json(data: dict):
    try:
        output_data = map_patient_data(data)
        return JSONResponse(content=output_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-excel")
async def process_excel(
    file: UploadFile = File(...), 
    json_column: str = Form("Input JSON")
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Vui lòng upload file Excel hợp lệ (.xlsx, .xls).")
    
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
        
        if json_column not in df.columns:
            raise HTTPException(status_code=400, detail=f"Không tìm thấy cột '{json_column}' trong file Excel.")
        
        output_jsons = []
        for index, row in df.iterrows():
            input_val = row[json_column]
            if pd.isna(input_val) or not isinstance(input_val, str):
                output_jsons.append("")
                continue
                
            try:
                input_data = json.loads(input_val)
                output_data = map_patient_data(input_data)
                output_jsons.append(json.dumps(output_data, ensure_ascii=False, indent=2))
            except Exception as ex:
                print(f"Row {index} error: {ex}")
                output_jsons.append(f"ERROR: {str(ex)}")
                
        df["Output JSON"] = output_jsons
        
        output_buffer = io.BytesIO()
        df.to_excel(output_buffer, index=False, engine='openpyxl')
        output_buffer.seek(0)
        
        return StreamingResponse(
            output_buffer, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=mapped_{file.filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Phục vụ các file tĩnh (Frontend)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
