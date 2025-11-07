import subprocess
def send_notification(recipient):
    uipath_exe = r"C:\Program Files\UiPath\Studio\UiRobot.exe"
    uipath_pkg = r"E:\Sem 7\axiom\axiom-expo-2\ui_path\sendsms_rare.1.0.4.nupkg"

    # recipient = "+917899374579"
    json_input = f'{{"phoneNumber": "{recipient}"}}'  # ✅ Proper JSON


    result = subprocess.run([
        uipath_exe,
        "execute",
        "--file", uipath_pkg,
        "--input", json_input
    ], capture_output=True, text=True)
    
    # Print results for debugging
    print(f"UiPath Return code: {result.returncode}")
    if result.stdout:
        print(f"UiPath STDOUT: {result.stdout}")
    if result.stderr:
        print(f"UiPath STDERR: {result.stderr}")
    
    # Raise error if UiPath execution failed
    if result.returncode != 0:
        raise Exception(f"UiPath execution failed with code {result.returncode}: {result.stderr}")

# send_notification("+918618476530")