import os
import json
from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai
import warnings
warnings.filterwarnings("ignore")

def extract_medicines(image_path):
    # Load .env
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found in .env file!")

    genai.configure(api_key=api_key)

    # Use latest supported Gemini model
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
    response_text = response.text.strip()
    response_text = response_text.strip("```")

    # Convert response_text to JSON and store it in a file
    output_file_path = "medicines.json"  # Specify your desired output file path
    with open(output_file_path, 'w') as json_file:
        json.dump(json.loads(response_text), json_file, indent=4)  # Convert to JSON and write to file

    print(f"Medicines saved to {output_file_path}")

# Example usage
extract_medicines("4.jpg")  # Uncomment to use the function