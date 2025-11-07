# Axiom: Your Intelligent Pharmacy Assistant

Axiom is a comprehensive mobile application designed to bridge the gap between patients and pharmacies. It provides a seamless experience for finding medicines, comparing prices, and securing the best options for your health needs, whether online or at a nearby store.

## ✨ Features

-   **Smart Prescription Analysis**: Upload a photo of your prescription or type in medicine names. Our OCR and Vision Language Models (VLMs) accurately extract the required medicines.
-   **Online & Offline Search**:
    -   **Online**: Scrapes data from multiple online pharmacies (like Apollo, Tata 1mg) to find the best prices and availability for your medicines.
    -   **Offline**: Checks the real-time inventory of local pharmacies who have partnered with us.
-   **Alternative Medicine Suggestions**: Leveraging a sophisticated RAG (Retrieval-Augmented Generation) architecture, the app suggests up to 4 safe and effective alternative medicines if your primary choice is unavailable, preventing LLM hallucinations.
-   **Interactive Map**: Visualizes nearby pharmacies on a map:
    -   **Green**: Closest pharmacy with the exact medicine available.
    -   **Yellow**: Pharmacy has a recommended alternative medicine.
    -   **Red**: Medicine is not available.
-   **Jan Aushadhi Kendra**: Prioritizes showing availability at Jan Aushadhi Kendras, ensuring you have access to the most affordable government-provided options.
-   **Flexible Fulfillment**: Choose to either pick up your medicine directly from the store or have it delivered to your doorstep.
-   **Automated Delivery**: For delivery orders, the system automatically assigns a driver, calculates the travel distance, and computes the delivery cost.
-   **Wellness & Healthcare Hub**: Provides users with information about free healthcare and medicine programs.
-   **Automated Notifications (UiPath)**:
    -   Sends a "Thank You" message to users after a transaction.
    -   In case of a rare or emergency medication requirement, it instantly alerts all registered vendors about the urgent need.

## ⚙️ How It Works (Architecture)

Axiom is built on a modern, multi-component architecture:

1.  **Frontend**: A React Native (Expo) application provides a cross-platform, user-friendly interface for mobile devices.
2.  **Backend**: A hybrid backend serves the application's needs:
    -   **Node.js (Express)**: Handles user authentication, file uploads (prescriptions), and general API requests.
    -   **Python (Flask/FastAPI)**: Powers the core intelligence of the app. This includes the OCR/VLM processing, web scraping, the RAG-based recommendation engine, and the pharmacy search logic.
3.  **Database**: An SQLite database (`axiom.db`) stores vendor inventory, user data, and other application-critical information.
4.  **RAG Engine**: We use `sentence-transformers` and `FAISS` to create a powerful retrieval system. This RAG architecture queries our data corpus (including vendor inventories) to provide accurate, context-aware alternative medicine suggestions, grounding the LLM's responses in factual data.
5.  **Mapping**: The `folium` library in Python is used to generate and display the interactive map of pharmacies.
6.  **Automation**: `UiPath` is integrated to handle automated SMS notifications for both user engagement and emergency alerts to vendors.

## 🛠️ Tech Stack

-   **Frontend**: React Native, Expo, React Navigation
-   **Backend**: Python (Flask/FastAPI), Node.js, Express.js
-   **Database**: SQLite
-   **AI/ML**:
    -   **OCR/VLM**: Custom implementation for prescription analysis.
    -   **RAG**: Sentence-Transformers, FAISS
-   **Web Scraping**: `requests`, `BeautifulSoup` (or similar)
-   **Mapping**: `folium`
-   **Automation**: UiPath

## 🚀 Getting Started

### Prerequisites

-   Node.js and npm
-   Python 3.x and pip
-   Expo Go app on your mobile device (for testing)
-   UiPath Orchestrator and Robot (for automation features)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd Team_MLFSS_06
    ```

2.  **Setup the Backend (Python):**
    ```bash
    cd axiom-expo-2/server
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Setup the Backend (Node.js):**
    ```bash
    # In the axiom-expo-2/server directory
    npm install
    ```

4.  **Setup the Frontend (React Native):**
    ```bash
    cd ../  # Go back to axiom-expo-2
    npm install
    ```

5.  **Environment Variables:**
    -   Create a `.env` file inside the `axiom-expo-2/server` directory.
    -   Add any necessary API keys or configuration variables (e.g., for UiPath, Google Maps, etc.).

### Running the Application

1.  **Start the Python Backend:**
    ```bash
    # In axiom-expo-2/server
    # Ensure your virtual environment is activated
    python main_app.py # Or your main Python server file
    ```

2.  **Start the Node.js Backend:**
    ```bash
    # In a new terminal, in axiom-expo-2/server
    npm run dev
    ```

3.  **Start the Frontend Application:**
    ```bash
    # In a new terminal, in axiom-expo-2
    npm start
    ```
    -   This will open the Metro Bundler. Scan the QR code with the Expo Go app on your phone.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a pull request.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
