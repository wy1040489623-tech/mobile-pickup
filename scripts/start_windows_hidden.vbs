Set fso = CreateObject("Scripting.FileSystemObject")
Set ws = CreateObject("WScript.Shell")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
base = fso.GetParentFolderName(scriptDir)
bat = scriptDir & "\start_windows.bat"
ready = fso.FileExists(base & "\.venv\Scripts\python.exe") And fso.FileExists(base & "\.venv\.deps-ok")

args = ""
For i = 0 To WScript.Arguments.Count - 1
  args = args & " """ & WScript.Arguments(i) & """"
Next

If ready Then
  ws.Run """" & bat & """" & args, 0, False
Else
  ws.Run """" & bat & """" & args, 1, False
End If
