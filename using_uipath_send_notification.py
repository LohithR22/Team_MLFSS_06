import subprocess
def send_notification(recipient):
    uipath_exe = r"C:\Program Files\UiPath\Studio\UiRobot.exe"
    uipath_pkg = r"C:\Users\Shreyank_SH\Documents\UiPath\Published\sendsms.1.0.4.nupkg"

    # recipient = "+917899374579"
    json_input = f'{{"phoneNumber": "{recipient}"}}'  # ✅ Proper JSON


    result = subprocess.run([
        uipath_exe,
        "execute",
        "--file", uipath_pkg,
        "--input", json_input
    ], capture_output=True, text=True)
    # print("Return code:", result.returncode)
    # print("STDOUT:", result.stdout)
    # print("STDERR:", result.stderr)

send_notification("+918618476530")