
import os
import sys
import json

# Add current directory to path so we can import main
sys.path.append(os.getcwd())

try:
    from main import enrich_report_data
except ImportError:
    print("Could not import enrich_report_data. Make sure this script is in backend/ folder.")
    sys.exit(1)

# Mock input for Low Severity Crack (Should NOT have Drill, Should be "Recommended")
mock_input = {
    "damage_type": "crack",
    "severity": 0.2, # Low Severity
    "confidence": 0.85,
    "bbox": [10, 10, 100, 100],
    "edge_ratio": 0.05
}

print("Testing enrich_report_data with Low Severity (0.2)...")
try:
    result = enrich_report_data(mock_input)
    
    if "damage_summary" in result:
        print("SUCCESS: Enrichment added 'damage_summary'")
        
        # Verify Action Wording (Point 2)
        action = result["detailed_assessment"]["action_required"]
        print(f"Action Wording: '{action}'")
        if "Recommended" in action:
            print("PASS: Action uses 'Recommended' for low severity.")
        else:
            print("FAIL: Action should use 'Recommended'.")
            
        # Verify Drill Exclusion (Point 1)
        # For crack, repair steps include "injection" (implying potential epoxy), 
        # but severity 0.2 < 0.3, so Drill should be REMOVED.
        equipment = result.get("tools_equipment", [])
        has_drill = any("drill" in e["name"].lower() for e in equipment)
        print(f"Has Drill: {has_drill}")
        if not has_drill:
            print("PASS: Drill excluded correctly for low severity.")
        else:
            print("FAIL: Drill should be excluded.")

        # Verify Materials Naming (Point 3)
        mats = result.get("materials_required", [])
        print("Materials:", json.dumps(mats, indent=2))
        
    else:
        print("FAILURE: Result returned without 'damage_summary'.")
        
except Exception as e:
    print(f"CRITICAL EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
