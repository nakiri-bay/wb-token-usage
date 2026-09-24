' auto_sync.vbs —— 静默启动自动同步守护（无窗口，后台常驻）
' 双击即可；停止见「停止自动同步.bat」；日志见 auto_sync_log.txt
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
script = fso.BuildPath(base, "auto_sync.py")
sh.Run """" & ResolvePythonW() & """ """ & script & """", 0, False

' 定位可用的 pythonw：优先每用户 Python 安装目录（不含用户名），回退到 PATH。
Function ResolvePythonW()
  Dim root, f, p
  On Error Resume Next
  root = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python")
  If fso.FolderExists(root) Then
    For Each f In fso.GetFolder(root).SubFolders
      p = fso.BuildPath(f.Path, "pythonw.exe")
      If fso.FileExists(p) Then
        ResolvePythonW = p
        Exit Function
      End If
    Next
  End If
  ResolvePythonW = "pythonw.exe"
End Function
