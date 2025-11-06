import subprocess
import json

def send_notification(medicine_name):
    uipath_exe = r"C:\Program Files\UiPath\Studio\UiRobot.exe"
    uipath_pkg = r"C:\Users\Shreyank_SH\Documents\UiPath\Published\sendsms_rare.1.0.1.4.nupkg"

    # ✅ Construct message text cleanly
    message_text = (
        f"Attention: Critical Medicine Request\n\n"
        f"Medicine: {medicine_name}\n\n"
        f"Action Required: Please verify stock availability and coordinate with your distribution network.\n\n"
        f"Your immediate assistance is greatly appreciated."
    )

    # ✅ Serialize properly to JSON (auto handles escaping)
    json_input = json.dumps({"messageText": message_text})

    result = subprocess.run([
        uipath_exe,
        "execute",
        "--file", uipath_pkg,
        "--input", json_input
    ], capture_output=True, text=True)

    print("Return code:", result.returncode)
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

send_notification("Penicillin")