' 静默启动桌宠：双击运行，全程无黑色命令行窗口闪烁
' 路径随本文件所在目录自动解析，移动文件夹后依然可用
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
strDir = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = strDir
sh.Run """" & ResolvePythonW() & """ """ & strDir & "\deskpet.py""", 0, False

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
