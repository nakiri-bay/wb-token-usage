' auto_sync.vbs —— 静默启动「独立同步守护」（无窗口，后台常驻）
' 注意：桌宠（deskpet.py）已自带同步循环，一般不需要本脚本；
'       仅当你想让同步独立于桌宠运行（例如不常开桌宠窗口）时才用它。
'       两者不要同时跑：会争抢同一个浏览器 profile。停止见「停止自动同步.bat」。
' 日志见 auto_sync_log.txt
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(base)
script = fso.BuildPath(fso.BuildPath(root, "src"), "auto_sync.py")
sh.CurrentDirectory = root
sh.Run """" & ResolvePythonW() & """ """ & script & """", 0, False

' 定位可用的 pythonw：优先每用户 Python 安装目录（不含用户名），回退到 PATH。
Function ResolvePythonW()
  Dim pyroot, f, p
  On Error Resume Next
  pyroot = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python")
  If fso.FolderExists(pyroot) Then
    For Each f In fso.GetFolder(pyroot).SubFolders
      p = fso.BuildPath(f.Path, "pythonw.exe")
      If fso.FileExists(p) Then
        ResolvePythonW = p
        Exit Function
      End If
    Next
  End If
  ResolvePythonW = "pythonw.exe"
End Function
