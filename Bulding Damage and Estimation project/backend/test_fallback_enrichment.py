from main import enrich_report_data, generate_remediation_pdf
import os
import json

# Simulate a basic ResNet result
basic_result = {
    "damage_type": "crack", 
    "severity": 0.6, 
    "confidence": 0.85, 
    "bbox": [10, 10, 100, 100], 
    "edge_ratio": 0.05,
    "source": "ResNet50"
}

print("Enriching basic result...")
full_result = enrich_report_data(basic_result)
print(json.dumps(full_result, indent=2))

# Verify key fields exist
required_keys = ["materials_required", "labour_details", "total_cost_summary", "repair_recommendation_steps"]
missing = [k for k in required_keys if k not in full_result or not full_result[k]]

if missing:
    print(f"FAILED: Missing keys {missing}")
else:
    print("SUCCESS: Full report structure generated.")
    
# Generate PDF to ensure no crashes
mock_record = {
    "inspection_id": "TEST_FALLBACK_ENRICH",
    "image_filename": "test.jpg", 
    "timestamp": "2025-12-09T10:00:00",
    "result": full_result
}

try:
    generate_remediation_pdf(mock_record, "test_fallback_report.pdf")
    if os.path.exists("test_fallback_report.pdf"):
        print("SUCCESS: PDF generated from enriched data.")
    else:
        print("FAILED: PDF not created.")
except Exception as e:
    print(f"PDF Generation Failed: {e}")
