"""
Wrapper script to call medicine finder from Node.js server.
Accepts JSON input via command line argument and outputs JSON result.
"""
import sys
import json
from medicine_finder.src.app import get_medicine_recommendations

if __name__ == "__main__":
    try:
        if len(sys.argv) < 2:
            sys.stderr.write("Error: Missing JSON input argument\n")
            sys.exit(1)
        
        # Parse input JSON
        input_data = json.loads(sys.argv[1])
        source_lat = float(input_data.get("source_lat"))
        source_lon = float(input_data.get("source_lon"))
        medicine_names = input_data.get("medicine_names", [])
        top_k = int(input_data.get("top_k", 5))
        
        if not medicine_names:
            sys.stderr.write("Error: medicine_names array is required\n")
            sys.exit(1)
        
        # Call the medicine finder
        result_json = get_medicine_recommendations(
            source_lat=source_lat,
            source_lon=source_lon,
            medicine_names=medicine_names,
            top_k=top_k
        )
        
        # Output the result
        print(result_json)
        
    except Exception as e:
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

