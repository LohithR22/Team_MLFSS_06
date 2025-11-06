import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
import warnings
warnings.filterwarnings("ignore")

def extract_medicines(image_path, output_dir=None):
    # Load .env
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found in .env file!")

    genai.configure(api_key=api_key)

    # Use Gemini model - gemini-2.5-flash
    model = genai.GenerativeModel("gemini-2.5-flash")
    # Load the image
    image = Image.open(image_path)

    prompt = """
    You are an expert medical OCR assistant specialized in reading handwritten prescriptions.

    Your task:
    1. Carefully analyze the uploaded image.
    2. Identify and extract only the names of prescribed medicines.
    3. Ignore any details about dosage, frequency, duration, instructions, doctor names, or patient information.

    Output requirements:
    - Return the final result strictly in valid JSON.
    - Include only a single key named "medicines".
    - The value of "medicines" must be an array of strings, each representing one medicine name.

    Example of the exact expected format:
    "medicines": ["Paracetamol", "Amoxicillin", "Pantoprazole"]

    Notes:
    - Do not include any explanations, markdown, or extra text outside the JSON.
    - If no medicine names are detected, return an empty list:
    """
    response = model.generate_content([prompt, image], generation_config={"temperature": 0.1})

    # Ensure the response is text only
    if not response.text:
        raise ValueError("Empty response from Gemini API")
    response_text = response.text.strip()
    # Remove markdown code blocks if present
    if response_text.startswith("```"):
        response_text = response_text.split("```", 2)[-1]
    if response_text.endswith("```"):
        response_text = response_text.rsplit("```", 1)[0]
    response_text = response_text.strip()

    # Convert response_text to JSON and store it in a file
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        # Try to extract JSON from the response if it's wrapped in text
        # Find the first { and try to match balanced braces to extract JSON
        start_idx = response_text.find('{')
        if start_idx != -1:
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(response_text)):
                if response_text[i] == '{':
                    brace_count += 1
                elif response_text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            if brace_count == 0:
                try:
                    data = json.loads(response_text[start_idx:end_idx])
                except json.JSONDecodeError:
                    raise ValueError(f"Failed to parse JSON from response: {response_text[:200]}... Error: {e}")
            else:
                raise ValueError(f"Failed to parse JSON from response: {response_text[:200]}... Error: {e}")
        else:
            raise ValueError(f"Failed to parse JSON from response: {response_text[:200]}... Error: {e}")
    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    output_file_path = os.path.join(output_dir, f"medicines_{ts}.json")
    with open(output_file_path, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, indent=4, ensure_ascii=False)

    # Print JSON to stdout so the caller can parse, or print file path if needed
    # Primary: print JSON for direct consumption
    print(json.dumps(data))

if __name__ == "__main__":
    with open("ocr_debug.log", "a") as f:
        f.write(str(sys.argv) + "\n")

    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python ocr.py <image_path> [output_dir]\n")
        sys.exit(1)
    image_arg = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) >= 3 else None
    try:
        extract_medicines(image_arg, out_dir)
    except Exception as e:
        # Surface error to caller
        sys.stderr.write(str(e) + "\n")
        sys.exit(2)