' 同步用量.vbs —— 完全静默运行一次官方积分同步（不弹任何窗口）
' 双击即可；运行日志见 sync_log.txt，结果见 official_daily.json
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
script = fso.BuildPath(base, "sync_usage.py")
' 第 3 个参数 0 = 隐藏窗口；False = 不等待，立即返回
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
