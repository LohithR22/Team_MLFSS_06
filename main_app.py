from medicine_finder.src.app import get_medicine_recommendations
import json

# Your main application logic...
print("Starting the main application...")

# 1. Define your inputs
lat = 12.91
lon = 77.51
meds_to_find = ["Paracetamol", "Pan D", "CoughRelief", "Aspirin"]

# 2. Call the function
print("Calling medicine finder...")
json_result_string = get_medicine_recommendations(
    source_lat=lat,
    source_lon=lon,
    medicine_names=meds_to_find,
    top_k=5 # This is optional, defaults to 5
)

# 3. Use the result
print("--- Results ---")
result = json.loads(json_result_string)
print(json.dumps(result, indent=2))
print("-----------------")

