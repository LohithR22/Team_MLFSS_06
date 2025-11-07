import sys
import json
from janaushadhi_lookup import janaushadhi_lookup

if __name__ == "__main__":
    try:
        # Read medicine list from stdin or command line
        if len(sys.argv) > 1:
            medicine_list = json.loads(sys.argv[1])
        else:
            medicine_list = json.load(sys.stdin)
        
        # Default CSV path (relative to server directory)
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(script_dir, "Product List_6_11_2025 @ 15_1_15.csv")
        
        # Perform lookup
        df_results, jan_aushadhi_clinics = janaushadhi_lookup(medicine_list, csv_path)
        
        # Convert DataFrame to JSON-serializable format
        results = df_results.to_dict('records')
        
        # Prepare response
        response = {
            "prices": results,
            "clinics": jan_aushadhi_clinics
        }
        
        print(json.dumps(response))
    except Exception as e:
        error_response = {
            "error": str(e),
            "prices": [],
            "clinics": []
        }
        print(json.dumps(error_response))
        sys.exit(1)

