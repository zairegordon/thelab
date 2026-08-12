Set WshShell = CreateObject("WScript.Shell")
appDir = "C:\Users\zaire\Downloads\football_tingz-main\football_tingz-main"
WshShell.CurrentDirectory = appDir

' Check if Flask is already running
Set objExec = WshShell.Exec("cmd /c netstat -ano | findstr :5000")
result = objExec.StdOut.ReadAll()
If InStr(result, "5000") > 0 Then
    WshShell.Run "http://127.0.0.1:5000", 1, False
    WScript.Quit
End If

' Start Flask silently in background
WshShell.Run "cmd /c cd /d """ & appDir & """ && .venv\Scripts\python.exe app.py", 0, False

' Poll until Flask is ready, then open browser
Do
    WScript.Sleep 1000
    Set objExec2 = WshShell.Exec("cmd /c netstat -ano | findstr :5000")
    check = objExec2.StdOut.ReadAll()
Loop While InStr(check, "5000") = 0

WshShell.Run "http://127.0.0.1:5000", 1, False
