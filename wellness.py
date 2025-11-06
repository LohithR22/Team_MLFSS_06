import requests
from bs4 import BeautifulSoup
import pandas as pd
import sys
import json
from datetime import datetime

# generate_hwc_report_cli()

# ==============================================================================
# HWC Reporter Application
# Fetches operational status of Ayushman Bharat Health and Wellness Centres (HWCs)
# and lists the guaranteed free services for the customer report.
# ==============================================================================

# --- Configuration ---
HWC_LOCATION_URL = "https://nhsrcindia.org/AB-HWCs-map-table"

# Static EML Data for RAG elaboration (Source: NHM/NHSRC guidelines documents)
HWC_EML_DETAILS = {
    "SHC_EML_COUNT": "Approx. 105 Free Essential Medicines",
    "PHC_EML_COUNT": "Approx. 171 Free Essential Medicines"
}
HWC_SERVICE_DETAILS = [
    "Comprehensive Primary Health Care (CPHC)",
    "Free essential medicines and diagnostic services (including 63 diagnostics at PHC level)",
    "Maternal and Child Health (MCH) services",
    "Screening and basic management for Non-Communicable Diseases (NCDs: Hypertension, Diabetes, 3 common Cancers)",
    "Geriatric care and Palliative care services",
    "Teleconsultation services (e-Sanjeevani) for specialist access",
    "Basic Oral and Eye Health Care"
]
# ---------------------


def scrape_hwc_data(url: str) -> pd.DataFrame | str:
    """Scrapes the table of operational HWCs by State/UT and returns a DataFrame or an error string."""
    try:
        # Increase timeout and add a simple header to mimic a browser request
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, timeout=20, headers=headers)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the table containing the HWC data
        table = soup.find('table')
        
        if not table:
            return "Error: Could not find the main data table on the NHSRC page."

        # Extract table data
        data = []
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all(['th', 'td'])
            cols = [col.get_text(strip=True) for col in cols]
            data.append(cols)

        # Convert to DataFrame (assuming the first row is the header)
        if len(data) > 1 and len(data[0]) > 1:
            df = pd.DataFrame(data[1:], columns=data[0])
            # Clean column names and data types
            df.columns = ['State', 'Operational HWCs']
            df['Operational HWCs'] = pd.to_numeric(df['Operational HWCs'].astype(str).str.replace(',', ''), errors='coerce')
            return df
        else:
            return "Error: Table structure is invalid or empty after extraction."

    except requests.exceptions.RequestException as e:
        return f"Error during scraping HWC data: {e}"


def generate_hwc_json_report(df_hwc: pd.DataFrame) -> dict:
    """Generates a structured JSON-ready dictionary for frontend consumption."""
    
    # Build structured JSON without summary section
    report_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "source_url": HWC_LOCATION_URL,
            "version": "1.0"
        },
        "service_packages": {
            "title": "Core Service Mandate (Free Healthcare & Wellness)",
            "description": "Essential, comprehensive primary care packages guaranteed free of cost at every operational Ayushman Arogya Mandir (HWC)",
            "cards": [
                {
                    "id": "free-medicines",
                    "title": "Free Essential Medicines",
                    "icon": "💊",
                    "details": [
                        {
                            "level": "Sub-Centre (SHC)",
                            "count": HWC_EML_DETAILS['SHC_EML_COUNT']
                        },
                        {
                            "level": "Primary Health Centre (PHC)",
                            "count": HWC_EML_DETAILS['PHC_EML_COUNT']
                        }
                    ]
                },
                {
                    "id": "diagnostics",
                    "title": "Free Diagnostic Services",
                    "icon": "🔬",
                    "description": "Up to 63 essential diagnostic tests including blood sugar, hemoglobin, etc."
                },
                {
                    "id": "services",
                    "title": "Comprehensive Health Services",
                    "icon": "🏥",
                    "services": [
                        {
                            "id": f"service-{idx}",
                            "name": service
                        }
                        for idx, service in enumerate(HWC_SERVICE_DETAILS, 1)
                    ]
                }
            ]
        },
        "state_wise_data": [
            {
                "state": row['State'],
                "operational_hwcs": int(row['Operational HWCs'])
            }
            for _, row in df_hwc.sort_values(by='Operational HWCs', ascending=False).iterrows()
        ],
        "official_links": [
            {
                "title": "HWC Operational Data",
                "url": HWC_LOCATION_URL,
                "description": "Live data on operational Health and Wellness Centres"
            },
            {
                "title": "Essential Medicine List Guidelines",
                "url": "https://qps.nhsrcindia.org/node/9906",
                "description": "NHSRC Essential Medicine List for HWC, SHC & PHC"
            },
            {
                "title": "Ayushman Bharat Digital Mission",
                "url": "https://abdm.gov.in/",
                "description": "Official ABDM Portal"
            }
        ]
    }
    
    return report_data


def save_json_report(data: dict, filename: str = "hwc_report.json"):
    """Saves the structured data to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # print(f"✅ Successfully saved report to: {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving JSON file: {e}", file=sys.stderr)
        return False


def generate_hwc_report_cli():
    """Main executable function for command line interface."""
    # 1. Scrape the data
    hwc_data_result = scrape_hwc_data(HWC_LOCATION_URL)

    # 2. Check for errors and generate report
    if isinstance(hwc_data_result, str):
        print(f"\n❌ FATAL ERROR: {hwc_data_result}", file=sys.stderr)
        print("Could not generate detailed report. Please check the network connection or the target website structure.")
        return
    
    # 3. Generate the JSON report
    json_report = generate_hwc_json_report(hwc_data_result)
    
    # 4. Save to file
    save_json_report(json_report, "hwc_report.json")
    
    # 5. Display summary
    # print("\n📈 Summary:")
    # print(f"   Total Operational HWCs: {json_report['summary']['total_operational_hwcs']:,}")
    # print(f"   States/UTs Covered: {json_report['summary']['total_states_uts']}")
    # print(f"   Top State: {json_report['summary']['top_5_states'][0]['state']} ({json_report['summary']['top_5_states'][0]['operational_hwcs']:,} HWCs)")

generate_hwc_report_cli()