
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
import cv2
import uuid
import os
import json
import hashlib
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, KeepTogether
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

# TensorFlow imports (optional)
try:
    import tensorflow as tf
    from tensorflow.keras.models import load_model, Model
    from tensorflow.keras.preprocessing.image import img_to_array, load_img
    from tensorflow.keras.applications.resnet50 import preprocess_input
    TF_AVAILABLE = True
except ImportError:
    print("TensorFlow not found. Custom model inference will be disabled.")
    TF_AVAILABLE = False

import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Configure Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GENAI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables")
else:
    genai.configure(api_key=GENAI_API_KEY)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

UPLOAD_DIR = "uploads"
REPORT_DIR = "reports"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# Load Custom Model if available
CUSTOM_MODEL = None
CLASS_INDICES = {}
CACHE_FILE = os.path.join(os.path.dirname(__file__), "image_cache.json")

def read_image_robust(path):
    try:
        # Robustly read image on Windows (supports Unicode/spaces)
        # using numpy fromfile and cv2.imdecode
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception as e:
        print(f"Error reading image {path}: {e}")
        return None

def compute_image_hash(image_bytes):
    return hashlib.sha256(image_bytes).hexdigest()

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

if TF_AVAILABLE:
    MODEL_PATH = os.path.join("model", "damage_model.h5")
    INDICES_PATH = os.path.join("model", "class_indices.json")
    if os.path.exists(MODEL_PATH) and os.path.exists(INDICES_PATH):
        try:
            print(f"Loading custom model from {MODEL_PATH}...")
            CUSTOM_MODEL = load_model(MODEL_PATH)
            # import json # Removed
            with open(INDICES_PATH, "r") as f:
                CLASS_INDICES = json.load(f)
            # Invert indices: {0: 'crack', ...}
            CLASS_INDICES = {v: k for k, v in CLASS_INDICES.items()}
            print(f"Model loaded with classes: {list(CLASS_INDICES.values())}")
        except Exception as e:
            print(f"Error loading custom model: {e}")
            CUSTOM_MODEL = None
    else:
        print("Custom model not found (run train_model.py to create one).")

app = FastAPI(title="BuildSenseAI Backend (Mock Model)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def detect_damage_with_gemini(image_path):
    if not GENAI_API_KEY:
        # Fallback to mock if no key
        return mock_detect_crack(image_path)
        
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-preview-09-2025')
        img = read_image_robust(image_path)
        if img is None:
            raise ValueError("Failed to read image with read_image_robust")

        success, encoded_image = cv2.imencode('.jpg', img)
        if not success:
            raise ValueError("Could not encode image")
            
        import PIL.Image
        # Convert BGR (OpenCV) to RGB (PIL)
        pil_img = PIL.Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # Load Price Database
        try:
            db_dir = os.path.join(os.path.dirname(__file__), "price_database")
            # import json # Removed
            with open(os.path.join(db_dir, "materials.json"), "r") as f:
                materials_db = json.load(f)
            with open(os.path.join(db_dir, "labour_rates.json"), "r") as f:
                labour_db = json.load(f)
            with open(os.path.join(db_dir, "equipment_rent.json"), "r") as f:
                equipment_db = json.load(f)
            with open(os.path.join(db_dir, "constants.json"), "r") as f:
                constants_db = json.load(f)
        except Exception as e:
            print(f"Error loading price database: {e}")
            # Fallback empty or default if needed, but better to fail or warn
            materials_db = []
            labour_db = []
            equipment_db = []
            constants_db = {}

        prompt = f"""
        You are an AI structural damage analysis system.
        Your output for the SAME image must ALWAYS remain IDENTICAL.

        =============================
             CORE BEHAVIOR RULES
        =============================

        1. INSPECTION CACHE (MANDATORY)
           - For every uploaded image, internally generate a stable, deterministic 
             “image signature” based on:
               • corner geometry
               • crack angle
               • crack width pattern
               • pixel intensity edges
           - If the image signature matches a previously processed image,
             THEN REPEAT THE EXACT SAME REPORT, SAME TEXT, SAME COST,
             SAME MATERIAL LIST, SAME TIMELINE — WORD-BY-WORD.

        2. ACCURACY RULE (99%)
           - Only detect REAL cracks or damage.
           - Never detect fake/mistaken patterns.
           - No false positives.

        3. NO DAMAGE DETECTED – TERMINATION RULE (MANDATORY)
           If the uploaded image shows NO visible damage (no cracks, no spalling, no leakage, no corrosion, no structural or non-structural defect):
           
           a. In "repair_recommendation_steps", write ONLY:
              1. Continue regular aesthetic and structural monitoring for future defects.
              2. Ensure electrical fittings remain securely installed and sealed against dust/moisture.

           b. Immediately AFTER point 2, you MUST write/include this exact line in the description or summary:
              "In this uploaded image, no damage is detected; therefore, the estimated repair cost is Nil (₹0)."

           c. CRITICAL STOP CONDITION:
              • DO NOT generate any estimation table
              • DO NOT generate subtotals
              • DO NOT generate final estimate section
              • DO NOT generate final recommendations
              • DO NOT generate limitations
              • DO NOT generate post-repair status
              
              RETURN EMPTY LISTS/NULLS FOR ALL SUBSEQUENT SECTIONS TO SIGNAL TERMINATION.

        4. NO RANDOMNESS
           - Disable all creativity, variation, rephrasing.
           - Do NOT modify wording between analyses.
           - Do NOT change quantities or cost once assigned to an image signature.

        5. FIXED COST ENGINE & GUIDELINES (India 2024-2025 Rates)
           - For the same image → same damage type → same severity →
             therefore SAME material qty → SAME labour → SAME final cost.
           - USE THESE REALISTIC MARKET RATES AS GUIDELINES (Do not exceed unreasonably):
             • Wall crack repair: ₹60–₹120 per sq.ft
             • Spalling repair: ₹150–₹350 per sq.ft
             • Waterproofing: ₹40–₹70 per sq.ft
             • Concrete patching: ₹200–₹350 per sq.ft
           - Overheads = {constants_db.get('max_overheads_percent', 8)}%
           - Contingency = {constants_db.get('max_contingency_percent', 3)}%

        6. FIXED OUTPUT FORMAT
           Output MUST always be identical in structure.

        7. IF SAME IMAGE IS RE-UPLOADED:
           - DO NOT re-analyze.
           - Fetch the previously locked output using the image fingerprint.
           - Return the EXACT same report (same sentences, same numbers).

        8. IF NEW IMAGE IS DIFFERENT:
           - Perform fresh analysis.
           - Generate a new fingerprint.
           - Lock new report + new cost permanently for that fingerprint.

        9. CONFIDENCE & LIMITATIONS
           - Provide a "confidence_score" (0.00 to 1.00) based on image clarity and damage visibility.
           - Provide a "confidence_explanation" (2-3 bullet points) explaining why this score was given.
           - Include a "limitations" section listing strictly:
             • Image-based assessment only
             • No subsurface or structural testing
             • Results depend on image quality

        ====================================================
        ### PRICE DATABASE
        
        **MATERIALS:**
        {json.dumps(materials_db, indent=2)}
        
        **LABOUR RATES:**
        {json.dumps(labour_db, indent=2)}
        
        **EQUIPMENT RENT:**
        {json.dumps(equipment_db, indent=2)}
        
        **WEATHER WINDOWS:**
        {json.dumps(constants_db.get('weather_windows', []), indent=2)}
        ====================================================
        
        Return a JSON object with the following structure (ensure all text is concise and fits in tables):
        {{
            "damage_summary": {{
                "damage_type": "string",
                "severity": "string (Low/Medium/High)",
                "root_cause": "string (Short)",
                "technical_assessment": "string (Detailed findings)",
                "safety_impact": "string (Short)",
                "remaining_life_before_repair": "string",
                "urgency_reason": "string (Short)",
                "bbox": [x, y, w, h] (default [0,0,0,0])
            }},
            "detailed_assessment": {{
                "damage_name": "string",
                "severity_level": "string (Low/Medium/High)",
                "location": "string (approx based on image)",
                "description": "string (2-3 lines)",
                "risk_level": "string (Low/Medium/High)",
                "action_required": "string (Immediate / Within 30 days / Monitor)"
            }},
            "repair_recommendation_steps": [
                "string (Step 1)", "string (Step 2)"
            ],
            "labour_details": [
                {{
                    "type": "string (Must match Labour Type in DB)",
                    "count": int,
                    "cost_per_day": int (Must match Rate in DB),
                    "total_days": int,
                    "total_cost": int
                }}
            ],
            "materials_required": [
                {{
                    "name": "string (Must match Material in DB)",
                    "quantity": "string",
                    "unit": "string (Must match Unit in DB)",
                    "market_rate": int (Must match Rate in DB),
                    "total_cost": int
                }}
            ],
            "tools_equipment": [
                {{
                    "name": "string (Must match Equipment in DB)",
                    "rent_per_day": int (Must match Rent in DB),
                    "total_days": int,
                    "total_cost": int
                }}
            ],
            "weather_suitability": {{
                "ideal_weather": "string (Temp/Humidity from DB)",
                "recommended_window": "string (Start-End from DB)",
                "rain_probability": "string (from DB)",
                "temperature": "string (from DB)",
                "humidity": "string (from DB)",
                "work_efficiency": "string",
                "reason_best_dates": "string (Short)",
                "days_to_avoid": "string (Short)"
            }},
            "total_cost_summary": {{
                "total_material_cost": int,
                "total_labour_cost": int,
                "equipment_cost": int,
                "overheads": int,
                "contingency": int,
                "final_estimate": int
            }},
            "timeline_and_schedule": {{
                 "estimated_duration_days": int,
                 "work_schedule_summary": "string"
            }},
            "post_repair_life_expectancy": {{
                "expected_remaining_life": "string",
                "warranty_period": "string",
                "maintenance_recommendation": "string (Short)",
                "improvement_summary": "string (Short)",
                "estimated_structure_age_after_repair": "string (e.g., 'Equivalent to a 5-year old structure')",
                "life_extension_years": "string (e.g., '+15 Years')"
            }},
            "final_recommendations": {{
                "structural_risk": "string (Short, clear advice)",
                "repair_urgency": "string (Short, clear advice)",
                "future_prevention_steps": "string (Short, clear advice)"
            }},
            "limitations": [
                "string (Bullet 1)", "string (Bullet 2)"
            ],
            "confidence_explanation": [
                 "string (Reason 1)", "string (Reason 2)"
            ]
        }} 
        
        Only return the JSON.
        """
        
        response = model.generate_content([prompt, pil_img])
        
        # Parse JSON from response
        # import json # Removed
        import re
        
        text = response.text
        # Extract JSON block if present
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                result = json.loads(json_str)
            except json.JSONDecodeError:
                 # Fallback if JSON is malformed
                result = {
                    "damage_summary": {
                        "damage_type": "Error parsing response",
                        "severity": "Unknown",
                        "bbox": [0,0,0,0],
                        "description": text
                    }
                }
        else:
            # Fallback
            result = {
                "damage_summary": {
                    "damage_type": "unknown",
                    "severity": "0.0",
                    "bbox": [0,0,0,0],
                    "description": text
                }
            }
            
        # Map new structure to old keys for backward compatibility if needed by frontend
        # The frontend likely uses: damage_type, severity, description, recommendation, bbox
        damage_summary = result.get("damage_summary", {})
        result["damage_type"] = damage_summary.get("damage_type", "unknown")
        
        # Convert severity string to float if possible for compatibility, or keep as string
        sev_str = damage_summary.get("severity", "0.0")
        try:
            if isinstance(sev_str, (int, float)):
                result["severity"] = float(sev_str)
            elif "high" in sev_str.lower():
                result["severity"] = 0.9
            elif "medium" in sev_str.lower():
                result["severity"] = 0.5
            else:
                result["severity"] = 0.2
        except:
            result["severity"] = 0.0

        result["description"] = damage_summary.get("root_cause", "") + ". " + damage_summary.get("urgency_reason", "")
        result["recommendation"] = "See detailed remediation report."
        result["bbox"] = damage_summary.get("bbox", [0,0,0,0])
            
        # Ensure bbox is present and valid
        if "bbox" not in result:
            result["bbox"] = [0,0,0,0]
            
        # Add edge_ratio for compatibility with existing frontend if needed, or just 0
        result["edge_ratio"] = 0.0
        
        # Ensure confidence is set from model or default to realistic value
        if "confidence" not in result:
             # Use model's score if available in damage_summary, else realistic default
            result["confidence"] = float(damage_summary.get("confidence_score", 0.88))
            
        # Ensure explanation and limitations are present
        if "confidence_explanation" not in result:
            result["confidence_explanation"] = result.get("damage_summary", {}).get("confidence_explanation", ["Analysis based on visible patterns."])
            
        if "limitations" not in result:
            result["limitations"] = result.get("damage_summary", {}).get("limitations", ["Image-based assessment only."])
            
        # --- POST-PROCESSING GEMINI RESULT TO ENFORCE REALISM RULES ---
        try:
             # 1. Action Wording (Low Severity)
             # "Action Recommended" instead of "Required" if severity <= 0.3
             sev = result.get("severity", 0.0)
             if sev <= 0.3:
                 da = result.get("detailed_assessment", {})
                 act = da.get("action_required", "")
                 if act:
                     da["action_required"] = act.replace("Required", "Recommended").replace("required", "recommended")
                     
             # 2. Drill Logic
             # Remove drill if not (epoxy/injection in steps AND severity > 0.3)
             tools = result.get("tools_equipment", [])
             steps = result.get("repair_recommendation_steps", [])
             steps_str = " ".join([str(s).lower() for s in steps])
             is_epoxy_repair = "epoxy" in steps_str or "injection" in steps_str
             
             if not (is_epoxy_repair and sev > 0.3):
                 # Remove drill
                 result["tools_equipment"] = [t for t in tools if "drill" not in t.get("name", "").lower()]
                 
             # 3. Prevention Text Cleanup
             # Deduplicate sentences
             fr = result.get("final_recommendations", {})
             prev = fr.get("future_prevention_steps", "")
             if prev and isinstance(prev, str):
                 seen = set()
                 clean_sentences = []
                 # split by period but keep period? simplistic split
                 sentences = [s.strip() for s in prev.split('.') if s.strip()]
                 for s in sentences:
                     if s not in seen:
                         seen.add(s)
                         clean_sentences.append(s)
                 if clean_sentences:
                     fr["future_prevention_steps"] = ". ".join(clean_sentences) + "."
        except Exception as e:
            print(f"Post-processing warning: {e}")

        return result
        
    except Exception as e:
        print(f"Gemini Error: {e}")
        import traceback
        traceback.print_exc()
        # If Gemini fails, use Mock but ENRICH it so PDF generation works
        print("Falling back to Mock + Enrichment...")
        basic_result = mock_detect_crack(image_path)
        return enrich_report_data(basic_result)

def detect_damage_with_resnet(image_path):
    if not CUSTOM_MODEL or not TF_AVAILABLE:
        return None
        
    try:
        # Preprocess
        img = load_img(image_path, target_size=(224, 224))
        x = img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)

        # Predict
        preds = CUSTOM_MODEL.predict(x)
        class_idx = np.argmax(preds[0])
        confidence = float(preds[0][class_idx])
        damage_type = CLASS_INDICES.get(class_idx, "Unknown")
        
        # Heuristic severity based on confidence or other metrics (could be improved)
        severity = 0.5 + (confidence - 0.5) if confidence > 0.5 else 0.3
        if "normal" in damage_type.lower() or "no_damage" in damage_type.lower():
            severity = 0.0
            
        # BBox - ResNet classification doesn't give bbox. 
        # We can use the mock's contour finding to at least highlight something relevant
        img_cv = read_image_robust(image_path)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5,5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            c = max(contours, key=cv2.contourArea)
            x_box,y_box,w,h = cv2.boundingRect(c)
            bbox = [int(x_box), int(y_box), int(w), int(h)]
            edge_ratio = edges.sum() / 255.0 / (edges.shape[0]*edges.shape[1])
        else:
            bbox = [0,0,0,0]
            edge_ratio = 0.0

        return {
            "damage_type": damage_type, 
            "severity": float(round(severity, 2)), 
            "confidence": float(round(confidence, 2)), 
            "bbox": bbox, 
            "edge_ratio": float(round(edge_ratio, 6)),
            "source": "ResNet50"
        }

    except Exception as e:
        print(f"ResNet Inference Error: {e}")
        return None

def mock_detect_crack(image_path):
    # Simple heuristic: edge density -> crack severity; largest contour bbox as location
    img = read_image_robust(image_path)
    if img is None:
        raise ValueError("Cannot read image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edge_ratio = edges.sum() / 255.0 / (edges.shape[0]*edges.shape[1])
    # severity 0-1 scaled edge_ratio
    severity = min(1.0, edge_ratio * 5.0)
    # find contours for bbox
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # take largest contour
        c = max(contours, key=cv2.contourArea)
        x,y,w,h = cv2.boundingRect(c)
        bbox = [int(x), int(y), int(w), int(h)]
    else:
        bbox = [0,0,0,0]
    # damage type heuristic
    damage_type = "crack" if severity > 0.05 else "normal"
    confidence = float(min(0.99, 0.5 + severity*0.5))
    return {"damage_type": damage_type, "severity": float(round(severity,3)), "confidence": confidence, "bbox": bbox, "edge_ratio": float(round(edge_ratio,6))}

def enrich_report_data(basic_result):
    """
    Takes a basic result (damage_type, severity, bbox) and enriches it
    with full report details using the local price database.
    """
    try:
        damage_type = basic_result.get("damage_type", "unknown").lower()
        severity = basic_result.get("severity", 0.5)
        
        # Load Price Database
        db_dir = os.path.join(os.path.dirname(__file__), "price_database")
        try:
            with open(os.path.join(db_dir, "materials.json"), "r") as f:
                materials_db = json.load(f)
            with open(os.path.join(db_dir, "labour_rates.json"), "r") as f:
                labour_db = json.load(f)
            with open(os.path.join(db_dir, "equipment_rent.json"), "r") as f:
                equipment_db = json.load(f)
            with open(os.path.join(db_dir, "constants.json"), "r") as f:
                constants_db = json.load(f)
        except Exception as e:
            print(f"Error loading price DB in enrichment: {e}")
            return basic_result

        # Defaults / Placeholders
        # If "crack", we want a specific set of logic
        
        # 1. Damage Summary & Detailed Assessment
        if "crack" in damage_type:
            summary_root_cause = "Thermal expansion or structural settling."
            summary_tech = "Linear discontinuity observed on surface."
            summary_safety = "Moderate. Monitor for expansion."
            
            det_desc = "Visible cracking pattern indicating potential stress concentration or material shrinkage."
            det_action = "Seal with epoxy injection or polymer mortar within 30 days."
            repair_steps = [
                "Clean the crack surface thoroughly to remove loose debris.",
                "Install injection ports along the crack length.",
                "Seal the surface between ports with epoxy paste.",
                "Inject low-viscosity epoxy resin starting from the bottom port.",
                "Allow curing for 24-48 hours and remove ports.",
                "Finish the surface to match existing texture."
            ]
        # Check for No Damage / Normal
        elif "normal" in damage_type or "no_damage" in damage_type or severity < 0.1:
            damage_type = "No Damage Detected"
            summary_root_cause = "No visible defects."
            summary_tech = "Surface appears intact."
            summary_safety = "Safe."
            
            det_desc = "In this uploaded image, no damage is detected; therefore, the estimated repair cost is Nil (₹0)."
            det_action = "Routine maintenance only."
            repair_steps = [
                "Continue regular aesthetic and structural monitoring for future defects.", 
                "Ensure electrical fittings remain securely installed and sealed against dust/moisture."
            ]
            
            # Force severity to low for consistency
            severity = 0.0

        elif "spall" in damage_type or "corrosion" in damage_type:
             summary_root_cause = "Rebar corrosion due to moisture ingress."
             summary_tech = "Concrete causing Delamination and exposed reinforcement."
             summary_safety = "High. Risk of falling debris."
             
             det_desc = "Spalling of concrete cover exposing corroded reinforcement bars."
             det_action = "Immediate structural repair required."
             repair_steps = [
                "Chip away loose concrete to expose rebar.",
                "Clean rust from rebar using wire brush or sandblasting.",
                "Apply anti-corrosive coating to the rebar.",
                "Apply bonding agent to the concrete surface.",
                "Patch with high-strength non-shrink grout.",
                "Cure and finish to match profile."
             ]
        else:
            # Generic fallback
            summary_root_cause = "Age-related degradation or external impact."
            summary_tech = "Surface irregularity detected."
            summary_safety = "Low to Medium."
            
            det_desc = f"Detected {damage_type} requiring assessment."
            det_action = "Conduct on-site inspection." if severity > 0.3 else "Conduct on-site inspection (Recommended)."
            repair_steps = ["Clean area.", "inspect depth.", "Apply appropriate filler.", "Paint."]

        # Refine Action Wording (Point 2)
        if severity <= 0.3:
            det_action = det_action.replace("Required", "Recommended").replace("required", "recommended")

        # Enrich basic result
        enriched = basic_result.copy()
        
        # Ensure bbox is list
        if "bbox" not in enriched: enriched["bbox"] = [0,0,0,0]
        
        # Risk Level Consistency (Point 4)
        risk_lvl = "High" if severity > 0.7 else "Medium" if severity > 0.3 else "Low"
        
        enriched["damage_summary"] = {
            "damage_type": damage_type.title(),
            "severity": "High" if severity > 0.7 else "Medium" if severity > 0.3 else "Low",
            "root_cause": summary_root_cause,
            "technical_assessment": summary_tech,
            "safety_impact": summary_safety,
            "remaining_life_before_repair": "6-12 Months" if severity < 0.5 else "1-3 Months",
            "urgency_reason": "Prevent moisture ingress and further deterioration",
            "bbox": enriched["bbox"]
        }
        
        # Location Label Sanity (Point 5)
        loc_label = "Vertical Wall Element (Est.)"
        if "wall" not in damage_type and "crack" not in damage_type:
            loc_label = "Building Envelope (Est.)"
            
        enriched["detailed_assessment"] = {
            "damage_name": damage_type.title(),
            "severity_level": "High" if severity > 0.7 else "Medium" if severity > 0.3 else "Low",
            "location": loc_label,
            "description": det_desc,
            "risk_level": risk_lvl,
            "action_required": det_action
        }
        
        enriched["repair_recommendation_steps"] = repair_steps
        
        # Cost Logic (Simplified Heuristic)
        # Assume area based on severity (just a multiplier for now since bbox size isn't real world units)
        multiplier = 1 + severity 
        
        # If No Damage, Force Costs to 0
        if severity == 0.0 or damage_type == "No Damage Detected":
            multiplier = 0
            
        # Materials
        # Materials Logic - Fixed for new DB format
        mats = []
        
        # Optimization: If no damage, skip detailed list generation
        if multiplier == 0:
            candidate_mats = []
        else:
            filtered_materials = []
            
            # Determine strict damage context
            is_roof_damage = "roof" in damage_type
        is_wall_damage = "crack" in damage_type or "spall" in damage_type or "wall" in damage_type
        
        # Handle if materials_db is matched as dict (wrapper) or list
        raw_materials = materials_db.get("materials", []) if isinstance(materials_db, dict) else materials_db
        
        for m in raw_materials:
            # Support both "item" (new db) and "name" (old code expectation) keys
            raw_name = m.get("item", m.get("name", "Unknown"))
            rate = m.get("price_with_gst", m.get("rate", 100))
            
            # Extract Unit from Name if present e.g. "Cement (50kg)"
            if "(" in raw_name:
                parts = raw_name.split("(")
                name_clean = parts[0].strip()
                unit_clean = parts[1].strip(")")
            else:
                name_clean = raw_name
                unit_clean = m.get("unit", "unit")
                
            m_lower = name_clean.lower()
            
            # Filter Rules
            if is_wall_damage and ("roof" in m_lower or "tile" in m_lower):
                continue
            if is_roof_damage and ("plaster" in m_lower or "paint" in m_lower or "putty" in m_lower):
                 continue
                 
            # Standardization for Candidate List
            m_obj = {
                "name": name_clean,
                "unit": unit_clean,
                "rate": rate,
                "category": "general" # Fallback since DB lacks category
            }
            
            # Selection Heuristics
            if "cement" in m_lower or "grout" in m_lower or "repair" in m_lower or "paint" in m_lower:
                 filtered_materials.append(m_obj)
        
        candidate_mats = filtered_materials
        if not candidate_mats: 
            # Fallback if filter removed everything
            candidate_mats = [{
                "name": raw_materials[0].get("item", "Generic Material"), 
                "unit": "unit", 
                "rate": 100
            }]
        
        total_mat_cost = 0
        # Select top 3 relevant materials
        for m_cand in candidate_mats[:3]:
            qty = int(5 * multiplier)
            cost = qty * m_cand["rate"]
            total_mat_cost += cost
            mats.append({
                "name": m_cand["name"],
                "quantity": str(qty),
                "unit": m_cand["unit"],
                "market_rate": m_cand["rate"],
                "total_cost": cost
            })
        enriched["materials_required"] = mats
        
        # Labour
        # Find skilled mason/helper
        labs = []
        if multiplier > 0:
            candidate_labs = [l for l in labour_db if "mason" in l["type"].lower() or "helper" in l["type"].lower()]
            if not candidate_labs: candidate_labs = labour_db[:1]        
            total_lab_cost = 0
            days = int(2 * multiplier)
            for l in candidate_labs:
                count = 1
                cost = count * days * l["rate_per_day"]
                total_lab_cost += cost
                labs.append({
                    "type": l["type"],
                    "count": count,
                    "cost_per_day": l["rate_per_day"],
                    "total_days": days,
                    "total_cost": cost
                })
        else:
            total_lab_cost = 0

        enriched["labour_details"] = labs
        
        # Equipment
        eqs = []
        if multiplier > 0:
            candidate_eq = [e for e in equipment_db if "drill" in e["name"].lower() or "scaffold" in e["name"].lower()]
            total_eq_cost = 0
            for e in candidate_eq:
                d = days
                cost = d * e["rent_per_day"]
                total_eq_cost += cost
                eqs.append({
                    "name": e["name"],
                    "rent_per_day": e["rent_per_day"],
                    "total_days": d,
                    "total_cost": cost
                })
        else:
            total_eq_cost = 0

        enriched["tools_equipment"] = eqs

        # Drilling Machine Usage (Point 1)
        # Include a drilling machine only when epoxy injection is explicitly part of the repair process AND severity > 0.3.
        is_epoxy_repair = any("epoxy" in s.lower() or "injection" in s.lower() for s in repair_steps)
        if not (is_epoxy_repair and severity > 0.3):
             # Remove drill if it exists
             enriched["tools_equipment"] = [e for e in enriched["tools_equipment"] if "drill" not in e["name"].lower()]
        
        # Weather
        windows = constants_db.get("weather_windows", [])
        best_window = windows[0] if windows else {}
        enriched["weather_suitability"] = {
            "ideal_weather": best_window.get("temp", "20-30C"),
            "recommended_window": f"{best_window.get('start')} to {best_window.get('end')}",
            "rain_probability": best_window.get("rain_prob", "Low"),
            "work_efficiency": "High during dry season",
            "reason_best_dates": "Low humidity ensures better curing.",
            "days_to_avoid": "Heavy rain days"
        }
        
        # Totals
        overheads_pct = constants_db.get("max_overheads_percent", 8)
        contingency_pct = constants_db.get("max_contingency_percent", 3)
        
        subtotal = total_mat_cost + total_lab_cost + total_eq_cost
        overheads = int(subtotal * overheads_pct / 100)
        contingency = int(subtotal * contingency_pct / 100)
        final = subtotal + overheads + contingency
        
        enriched["total_cost_summary"] = {
            "total_material_cost": total_mat_cost,
            "total_labour_cost": total_lab_cost,
            "equipment_cost": total_eq_cost,
            "overheads": overheads,
            "contingency": contingency,
            "final_estimate": final,
            "disclaimer": "Cost estimates are indicative and normalized using Indian market labor and material benchmarks."
        }
        
        # Post Repair
        enriched["post_repair_life_expectancy"] = {
             "estimated_structure_age_after_repair": "Restored to functional condition",
             "life_extension_years": "Appears to extend life by +5 to 10 Years",
             "warranty_period": "1 Year on workmanship (Suggested)",
             "maintenance_recommendation": "Annual inspection recommended.",
             "improvement_summary": "Structural integrity appears restored and further propagation arrested."
        }
        
        # Text Cleanup (Point 6)
        prevention = "Maintain drainage and seal surface cracks periodically."
        enriched["final_recommendations"] = {
            "structural_risk": "Reduced risk after repair (Subject to verification).",
            "repair_urgency": " Recommended within 1 month.",
            "future_prevention_steps": prevention
        }
        
        # Ensure limitations exist in enriched
        if "limitations" not in enriched:
            enriched["limitations"] = basic_result.get("limitations", [
                "Image-based assessment only",
                "No subsurface or structural testing",
                "Results depend on image quality"
            ])
            
        # Ensure confidence explanation
        if "confidence_explanation" not in enriched:
            enriched["confidence_explanation"] = basic_result.get("confidence_explanation", ["Analysis based on visible surface patterns."])
        
        return enriched

    except Exception as e:
        print(f"Enrichment Error: {e}")
        # Return basic result if enrichment fails to avoid total failure
        return basic_result

@app.post("/api/inspect/upload")
async def upload_image(file: UploadFile = File(...)):
    try:
        print("DEBUG: >>> RECEIVED UPLOAD REQUEST <<<")
        print(f"DEBUG: Filename: {file.filename}, Content-Type: {file.content_type}")
        contents = await file.read()
        print(f"DEBUG: Read {len(contents)} bytes")
        img_id = str(uuid.uuid4())[:8]
        filename = f"{img_id}_{file.filename}"
        path = os.path.join(UPLOAD_DIR, filename)
        with open(path, "wb") as f:
            f.write(contents)

            
        # Deterministic Hashing & Caching
        img_hash = compute_image_hash(contents)
        print(f"DEBUG: Computed hash {img_hash}")
        cache = load_cache()
        print(f"DEBUG: Loaded cache with {len(cache)} entries")
        
        if img_hash in cache:
            print(f"Cache HIT for hash: {img_hash}")
            result = cache[img_hash]
            # Create a new record reusing the result but unique inspection ID
            inspection_id = str(uuid.uuid4())[:10]
            timestamp = datetime.utcnow().isoformat()
            record = {
                "inspection_id": inspection_id,
                "image_filename": filename,
                "timestamp": timestamp,
                "result": result
            }
            rec_path = os.path.join(UPLOAD_DIR, inspection_id + ".json")
            with open(rec_path, "w") as rf:
                json.dump(record, rf, indent=2)
            return JSONResponse({"status":"success", "inspection": record, "cached": True})
            
        # Try Custom Model First
        result = detect_damage_with_resnet(path)
        
        # Enrich Result if from ResNet
        if result:
            print("Enriching ResNet result...")
            result = enrich_report_data(result)
        
        # If no custom model or it failed, fall back to Gemini
        if not result:
            print("Using Gemini/Mock for detection...")
            print("DEBUG: Calling detect_damage_with_gemini")
            result = detect_damage_with_gemini(path)
            print("DEBUG: Returned from detect_damage_with_gemini")
        else:
            print(f"Used ResNet model: {result['damage_type']}")
        
        # Save to Cache
        cache[img_hash] = result
        save_cache(cache)
        
        inspection_id = str(uuid.uuid4())[:10]
        timestamp = datetime.utcnow().isoformat()
        # save record JSON
        record = {
            "inspection_id": inspection_id,
            "image_filename": filename,
            "timestamp": timestamp,
            "result": result
        }
        rec_path = os.path.join(UPLOAD_DIR, inspection_id + ".json")
        # import json # Removed
        with open(rec_path, "w") as rf:
            json.dump(record, rf, indent=2)
        return JSONResponse({"status":"success","inspection": record})
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"UPLOAD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_damage_pdf(inspection_record, out_path):
    doc = SimpleDocTemplate(out_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = styles["Title"]
    story.append(Paragraph("BuildSenseAI - Damage Report", title_style))
    story.append(Spacer(1, 12))

    # Inspection Details
    res = inspection_record['result']
    data = [
        ["Inspection ID", inspection_record.get('inspection_id', 'N/A')],
        ["Timestamp (UTC)", inspection_record.get('timestamp', 'N/A')],
        ["Image File", inspection_record.get('image_filename', 'N/A')],
        ["Detected Damage Type", res.get('damage_type', 'N/A')],
        ["Severity (0-1)", str(res.get('severity', 'N/A'))],
        ["Confidence", f"{res.get('confidence', 'N/A')} ({res.get('confidence_explanation', ['AI Estimate'])[0]})"],
        ["Damage Localization", "Approximate / Global" if str(res.get('bbox','')) == "[0, 0, 0, 0]" else str(res.get('bbox', 'N/A'))],
        ["Edge Ratio", str(res.get('edge_ratio', 'N/A'))]
    ]

    table = Table(data, colWidths=[2.5*inch, 4*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('BACKGROUND', (1, 0), (1, -1), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # Notes removed as per user request

    # Image
    img_path = os.path.join(UPLOAD_DIR, inspection_record['image_filename'])
    try:
        # Resize image to fit page width while maintaining aspect ratio
        from reportlab.lib.utils import ImageReader
        img_reader = ImageReader(img_path)
        iw, ih = img_reader.getSize()
        aspect = ih / float(iw)
        width = 6 * inch
        height = width * aspect
        
        # Check if height is too large for page
        if height > 5 * inch:
            height = 5 * inch
            width = height / aspect

        img = Image(img_path, width=width, height=height)
        story.append(img)
    except Exception as e:
        story.append(Paragraph(f"Could not embed image: {str(e)}", styles["Normal"]))

    doc.build(story)

def generate_remediation_pdf(inspection_record, out_path):
    # Standard A4 size: 8.27 x 11.69 inches
    # Margins: 0.5 inch all around -> Usable width approx 7.27 inches
    doc = SimpleDocTemplate(
        out_path, 
        pagesize=A4,
        rightMargin=0.5*inch, 
        leftMargin=0.5*inch, 
        topMargin=0.5*inch, 
        bottomMargin=0.5*inch
    )
    styles = getSampleStyleSheet()
    
    # Custom Styles - STRICT BLACK AND WHITE
    # Heading Styles
    styles["Heading2"].textColor = colors.black
    styles["Heading2"].fontSize = 14
    styles["Heading2"].spaceAfter = 10
    styles["Heading2"].keepWithNext = True
    styles["Heading2"].fontName = 'Helvetica-Bold'

    styles["Heading3"].textColor = colors.black
    styles["Heading3"].fontSize = 12
    styles["Heading3"].keepWithNext = True
    styles["Heading3"].spaceAfter = 6
    styles["Heading3"].fontName = 'Helvetica-Bold'
    
    # Table Text Styles
    styles.add(ParagraphStyle(name='TableText', parent=styles['Normal'], fontSize=10, leading=12, textColor=colors.black))
    styles.add(ParagraphStyle(name='TableTextBold', parent=styles['Normal'], fontSize=10, leading=12, fontName='Helvetica-Bold', textColor=colors.black))
    
    # Helper to wrap text in Paragraph for tables (auto-wrap)
    def p(text, style=styles['TableText']):
        if text is None:
            text = "N/A"
        return Paragraph(str(text), style)

    def p_bold(text, style=styles['TableTextBold']):
        if text is None:
            text = "N/A"
        return Paragraph(str(text), style)
    
    story = []

    # 1. Title
    title_style = styles["Title"]
    title_style.textColor = colors.black
    story.append(Paragraph("BuildSenseAI - Structural Damage & Estimation Report", title_style))
    story.append(Spacer(1, 12))

    # 2. Inspection ID
    story.append(Paragraph(f"<b>Inspection ID:</b> {inspection_record['inspection_id']}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # 3. Image Section
    img_filename = inspection_record.get('image_filename')
    if img_filename:
        img_path = os.path.join(UPLOAD_DIR, img_filename)
        try:
            # Resize image to fit page width while maintaining aspect ratio
            img_reader = ImageReader(img_path)
            iw, ih = img_reader.getSize()
            aspect = ih / float(iw)
            
            # Max width constrained by margins (approx 7 inches usable)
            max_width = 7 * inch
            max_height = 5 * inch 

            width = max_width
            height = width * aspect
            
            # Check if height is too large for page
            if height > max_height:
                height = max_height
                width = height / aspect

            img = Image(img_path, width=width, height=height)
            story.append(img)
            story.append(Spacer(1, 12))
        except Exception as e:
            story.append(Paragraph(f"Image not available: {str(e)}", styles["Normal"]))
            story.append(Spacer(1, 12))
    
    res = inspection_record['result']

    # 4. Inspection Technical Details Table
    tech_section = []
    tech_section.append(Paragraph("Inspection Technical Details", styles["Heading3"]))
    
    tech_data = [
        [p_bold("Attribute"), p_bold("Value")],
        [p("Detected Damage Type"), p(res.get('damage_type', 'N/A'))],
        [p("Severity (0-1)"), p(res.get('severity', 'N/A'))],
        [p("Confidence"), p(f"{res.get('confidence', 'N/A')} ({res.get('confidence_explanation', ['AI Estimate'])[0]})")], 
        [p("Damage Localization"), p("Approximate / Global" if str(res.get('bbox','')) == "[0, 0, 0, 0]" else str(res.get('bbox', [0,0,0,0])))],
    ]
    # Usable width ~7.2in. Col widths: 2.5 + 4.7 = 7.2
    t_tech = Table(tech_data, colWidths=[2.5*inch, 4.7*inch])
    t_tech.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke), # Light grey header row
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black), # Black grid
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
    ]))
    tech_section.append(t_tech)
    tech_section.append(Spacer(1, 12))
    story.append(KeepTogether(tech_section))
    
    # Check if new format data is available
    if "damage_summary" in res and isinstance(res["damage_summary"], dict):
        ds = res["damage_summary"]
        det = res.get("detailed_assessment", {})
        
        # 5. Damage Summary
        summary_section = []
        summary_section.append(Paragraph("1. Damage Summary", styles["Heading2"]))
        # Bullet points:
        damage_list = [
            f"<b>Damage Found:</b> {ds.get('damage_type', 'N/A')}",
            f"<b>Severity:</b> {ds.get('severity', 'N/A')}",
            f"<b>Possible Root Cause:</b> {ds.get('root_cause', 'N/A')}",
        ]
        for item in damage_list:
             summary_section.append(Paragraph(f"• {item}", styles["Normal"]))
        summary_section.append(Spacer(1, 12))
        story.append(KeepTogether(summary_section))

        # 6. Detailed Damage Assessment
        detailed_section = []
        detailed_section.append(Paragraph("2. Detailed Damage Assessment", styles["Heading2"]))
        
        dd_data = [
            [p_bold("Attribute"), p_bold("Details")],
            [p("Damage Name"), p(det.get('damage_name', ds.get('damage_type', 'N/A')))],
            [p("Severity Level"), p(det.get('severity_level', ds.get('severity', 'N/A')))],
            [p("Location"), p(det.get('location', 'See Image'))],
            [p("Description"), p(det.get('description', ds.get('technical_assessment', 'N/A')))],
            [p("Risk Level"), p(det.get('risk_level', 'N/A'))],
            [p("Action Required"), p(det.get('action_required', 'N/A'))]
        ]
        
        t_dd = Table(dd_data, colWidths=[2*inch, 5.2*inch])
        t_dd.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.whitesmoke),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ]))
        detailed_section.append(t_dd)
        detailed_section.append(Spacer(1, 12))
        story.append(KeepTogether(detailed_section))

        # 7. Recommended Repair Work
        repair_section = []
        repair_section.append(Paragraph("3. Recommended Repair Work (Realistic India 2024-2025 Rates)", styles["Heading2"]))
        
        # 3.1 Repair Steps
        repair_section.append(Paragraph("<b>Repair Steps & Labor:</b>", styles["Normal"]))
        steps = res.get("repair_recommendation_steps", [])
        if steps:
            for i, step in enumerate(steps, 1):
                repair_section.append(Paragraph(f"{i}. {step}", styles["Normal"]))
        else:
            repair_section.append(Paragraph("No specific steps provided.", styles["Normal"]))
        repair_section.append(Spacer(1, 6))
        
        # --- STRICT TERMINATION FOR NO DAMAGE ---
        # Check for strict "Nil" string or No Damage type
        # User requested: "In this uploaded image, no damage is detected; therefore, the estimated repair cost is Nil (₹0)."
        termination_string = "In this uploaded image, no damage is detected; therefore, the estimated repair cost is Nil (₹0)."
        is_no_damage = (
            "No Damage" in res.get("damage_type", "") or 
            res.get("severity", 0.0) == 0.0 or
            termination_string in res.get("detailed_assessment", {}).get("description", "")
        )
        
        if is_no_damage:
            # Append the termination line exactly in BOLD
            repair_section.append(Paragraph(f"<b>{termination_string}</b>", styles["Normal"]))
            repair_section.append(Spacer(1, 12))
            story.append(KeepTogether(repair_section))
            
            # STOP GENERATION HERE - No further tables or text
            doc.build(story)
            return

        story.append(KeepTogether(repair_section))

        # 8. Cost Estimate Table
        cost_section = []
        cost_section.append(Paragraph("<b>Detailed Cost Estimate:</b>", styles["Normal"]))
        cost_section.append(Spacer(1, 6))
        
        # Materials Table
        # Cols: Material, Qty, Unit, Rate, Total
        mat_header = [
            p_bold("Material"), 
            p_bold("Qty"), 
            p_bold("Unit"), 
            p_bold("Rate"), 
            p_bold("Total")
        ]
        mat_data = [mat_header]
        
        for item in res.get("materials_required", []):
            mat_data.append([
                p(item.get("name", "")),
                p(str(item.get("quantity", ""))),
                p(item.get("unit", "")),
                p(f"Rs. {item.get('market_rate', 0)}"),
                p(f"Rs. {item.get('total_cost', 0)}")
            ])
            
        # Add a sub-header row for Totals logic if we want to combine tables, 
        # but sticking to one big table including Lab/Eq/Total is cleaner or separated.
        # Let's add Labour and Equipment rows with section headers inside the table for consistency with "Sample" usually having one big cost table
        
        # Labour Header
        mat_data.append([p_bold("LABOUR"), "", "", "", ""])
        for item in res.get("labour_details", []):
             mat_data.append([
                p(f"{item.get('type','')} ({item.get('count',0)} people x {item.get('total_days',0)} days)"),
                "",
                "Days",
                p(f"Rs. {item.get('cost_per_day', 0)}"),
                p(f"Rs. {item.get('total_cost', 0)}")
            ])

        # Equipment Header
        mat_data.append([p_bold("EQUIPMENT & TOOLS"), "", "", "", ""])
        for item in res.get("tools_equipment", []):
             mat_data.append([
                p(f"{item.get('name','')}", styles['TableText']),
                p(str(item.get('total_days',0))),
                "Days",
                p(f"Rs. {item.get('rent_per_day', 0)}"),
                p(f"Rs. {item.get('total_cost', 0)}")
            ])
            
        # Summary Rows
        tc = res.get("total_cost_summary", {})
        mat_data.append([p_bold("Subtotal Materials"), "", "", "", p(f"Rs. {tc.get('total_material_cost', 0):,}")])
        mat_data.append([p_bold("Subtotal Labour"), "", "", "", p(f"Rs. {tc.get('total_labour_cost', 0):,}")])
        mat_data.append([p_bold("Overheads"), "", "", "", p(f"Rs. {tc.get('overheads', 0):,}")])
        mat_data.append([p_bold("Contingency"), "", "", "", p(f"Rs. {tc.get('contingency', 0):,}")])
        mat_data.append([p_bold("FINAL ESTIMATE"), "", "", "", p_bold(f"Rs. {tc.get('final_estimate', 0):,}")])

        t_cost = Table(mat_data, colWidths=[2.7*inch, 0.8*inch, 0.8*inch, 1.3*inch, 1.4*inch])
        t_cost.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke), # Header
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            # Bold for headers within table (Labour, Equipment)
            ('BACKGROUND', (0, len(res.get("materials_required", []))+1), (-1, len(res.get("materials_required", []))+1), colors.whitesmoke),
        ]))

        cost_section.append(t_cost)
        cost_section.append(Spacer(1, 6))
        # DISCLAIMER
        cost_section.append(Paragraph(f"<i>*{tc.get('disclaimer', 'Indicative costs only.')}</i>", styles["TableText"]))
        cost_section.append(Spacer(1, 12))
        story.append(KeepTogether(cost_section))
        
        # 9. Final Recommendations
        final_section = []
        final_section.append(Paragraph("4. Final Recommendations", styles["Heading2"]))
        fr = res.get("final_recommendations", {})
        
        final_section.append(Paragraph(f"<b>Structural Risk:</b> {fr.get('structural_risk', 'N/A')}", styles["Normal"]))
        final_section.append(Paragraph(f"<b>Repair Urgency:</b> {fr.get('repair_urgency', 'N/A')}", styles["Normal"]))
        final_section.append(Paragraph(f"<b>Future Prevention:</b> {fr.get('future_prevention_steps', 'N/A')}", styles["Normal"]))
        final_section.append(Paragraph(f"<b>Future Prevention:</b> {fr.get('future_prevention_steps', 'N/A')}", styles["Normal"]))
        story.append(KeepTogether(final_section))

        # LIMITATIONS SECTION
        lim_section = []
        lim_section.append(Spacer(1, 12))
        lim_section.append(Paragraph("Limitations of Assessment", styles["Heading2"]))
        limitations = res.get("limitations", ["Image-based assessment only"])
        for lim in limitations:
            lim_section.append(Paragraph(f"• {lim}", styles["Normal"]))
        story.append(KeepTogether(lim_section))
        
        # 10. Post-Repair Status & Life Expectancy
        age_section = []
        age_section.append(Spacer(1, 12))
        age_section.append(Paragraph("5. Post-Repair Structural Status & Life Expectancy", styles["Heading2"]))
        
        pr = res.get("post_repair_life_expectancy", {})
        
        age_data = [
            [p_bold("Projected Status After Repair"), p_bold("Value")], # Header
            [p("Effective Building Age"), p(pr.get('estimated_structure_age_after_repair', 'N/A'))],
            [p("Life Extension"), p(pr.get('life_extension_years', 'N/A'))],
            [p("Warranty Period"), p(pr.get('warranty_period', 'N/A'))],
            [p("Future Maintenance"), p(pr.get('maintenance_recommendation', 'N/A'))]
        ]
        
        t_age = Table(age_data, colWidths=[3*inch, 4.2*inch])
        t_age.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke), # Header Row
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ]))

        age_section.append(t_age)
        age_section.append(Spacer(1, 12))
        age_section.append(Paragraph(f"<b>Improvement Summary:</b> {pr.get('improvement_summary', '')}", styles["Normal"]))
        age_section.append(Spacer(1, 12))
        story.append(KeepTogether(age_section))

        # 11. Weather Constraints
        weather_section = []
        weather_section.append(Paragraph("Weather Constraints", styles["Heading3"]))
        ws = res.get("weather_suitability", {})
        weather_section.append(Paragraph(f"<b>Rec. Window:</b> {ws.get('recommended_window', '')}", styles["Normal"]))
        weather_section.append(Paragraph(f"<b>Ideal Conditions:</b> {ws.get('ideal_weather', '')}", styles["Normal"]))
        story.append(KeepTogether(weather_section))
    else:
        # Fallback for old data format - Keep minimal just in case
        story.append(Paragraph("Legacy Data Format - Please re-analyze image for full report.", styles["Normal"]))

    doc.build(story)

@app.get("/api/inspect/result/{inspection_id}")
def get_inspection_result(inspection_id: str):
    rec_path = os.path.join(UPLOAD_DIR, inspection_id + ".json")
    if not os.path.exists(rec_path):
        raise HTTPException(status_code=404, detail="Inspection not found")
    import json
    with open(rec_path, "r") as f:
        record = json.load(f)
    return JSONResponse({"inspection": record})

@app.get("/api/report/damage/{inspection_id}")
def damage_report(inspection_id: str):
    rec_path = os.path.join(UPLOAD_DIR, inspection_id + ".json")
    if not os.path.exists(rec_path):
        raise HTTPException(status_code=404, detail="Inspection not found")
    import json
    with open(rec_path, "r") as f:
        record = json.load(f)
    out_pdf = os.path.join(REPORT_DIR, f"{inspection_id}_damage.pdf")
    generate_damage_pdf(record, out_pdf)
    return FileResponse(out_pdf, media_type='application/pdf', filename=os.path.basename(out_pdf))

@app.get("/api/report/remedy/{inspection_id}")
def remedy_report(inspection_id: str):
    rec_path = os.path.join(UPLOAD_DIR, inspection_id + ".json")
    if not os.path.exists(rec_path):
        raise HTTPException(status_code=404, detail="Inspection not found")
    import json
    with open(rec_path, "r") as f:
        record = json.load(f)
    out_pdf = os.path.join(REPORT_DIR, f"{inspection_id}_remedy.pdf")
    generate_remediation_pdf(record, out_pdf)
    return FileResponse(out_pdf, media_type='application/pdf', filename=os.path.basename(out_pdf))

CHAT_SYSTEM_INSTRUCTION = """
You are **BuildSenseAI**, an elite structural engineering assistant designed to provide expert, clear, and actionable advice to users in India.

### Core Persona
- **Role**: Senior Structural Consultant & Construction Expert.
- **Tone**: Professional, encouraging, precise, and polite. (Like GitHub Copilot or ChatGPT).
- **Region**: India (Use IS Codes, Indian Market Rates in ₹, and local terminology).
- **Rule**: Start or end every response with: "Based on the visual assessment in the generated report..."

### Response Guidelines
1.  **Structure Your Answer**:
    -   **Introduction**: 1-2 sentences acknowledging the query.
    -   **Key Insight/Direct Answer**: Valid, high-level answer immediately.
    -   **Detailed Explanation**: Break down into steps, bullet points, or tables.
    -   **Technical Context**: Reference relevant IS Codes (e.g., IS 456 for concrete, IS 800 for steel) or engineering principles.
    -   **Practical Advice**: Material estimates, approximate costs (in ₹), or safety warnings.

2.  **Formatting is Critical**:
    -   Use **Bold** for emphasis.
    -   Use `Code Blocks` for formulas or specific data.
    -   Use *Tables* for comparisons (e.g., Cost vs. Quality) or breakdowns.
    -   Use Lists (numbered or bulleted) for readability.

3.  **Safety First**:
    -   Always warn if a situation sounds dangerous (e.g., deep structural cracks).
    -   Recommend professional on-site inspection for critical issues.

4.  **Do Not**:
    -   Do not hallucinate standards.
    -   Do not give medical or legal advice.
    -   Do not be verbose; keep it "Copilot-concise" but detailed enough to be useful.

### Example Interaction
**User**: "How do I fix a hairline crack in my plaster?"
**BuildSenseAI**:
"**Hairline cracks** in plaster are common and usually non-structural. Here is how you can fix them:

### Step-by-Step Repair
1.  **Preparation**: Widen the crack slightly using a scraper to create a 'V' notch.
2.  **Cleaning**: Remove loose debris and dust using a brush or vacuum.
3.  **Filling**: Apply a high-quality **shrink-free crack filler** (e.g., Dr. Fixit Crack-X or similar).
    - *Cost Estimate*: ₹500 - ₹1,000 for DIY materials.
4.  **Finishing**: Sand the surface smooth after 24 hours and repaint to match.

> **Note**: If the crack reappears or widens, consult a structural engineer as it may indicate underlying settlement.
*Reference*: IS 2402 (Code of Practice for External Renderings)."
"""

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    if not GENAI_API_KEY:
        return JSONResponse({"response": "Chatbot is not configured (missing API key)."})

    # List of models to try in order of preference
    # Expanded list for better availability
    models_to_try = [
        "gemini-2.5-flash-preview-09-2025",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-exp",
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-pro-latest"
    ]

    last_error = None
    import time

    for i, model_name in enumerate(models_to_try):
        try:
            print(f"Attempting to generate with model: {model_name}")
            model = genai.GenerativeModel(
                model_name,
                system_instruction=CHAT_SYSTEM_INSTRUCTION
            )
            chat = model.start_chat(history=[
                {"role": "user" if msg.role == "user" else "model", "parts": [msg.content]} 
                for msg in request.history
            ])
            
            response = chat.send_message(request.message)
            return JSONResponse({"response": response.text})
            
        except Exception as e:
            error_str = str(e)
            print(f"Model {model_name} failed: {error_str}")
            last_error = error_str
            
            # Continue if it's a quota error (429) or not found (404) or service unavailable (503)
            # Add a small delay before trying the next model
            time.sleep(1) 
            continue

    # If we exhaust all models
    if "429" in str(last_error) or "ResourceExhausted" in str(last_error):
         return JSONResponse({"response": "**All Models Busy**: The AI is currently experiencing very high load. We tried multiple models but all are busy. Please try again in 1-2 minutes."})
    
    return JSONResponse({"response": f"Error: All models failed. Last error: {last_error}"})

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
