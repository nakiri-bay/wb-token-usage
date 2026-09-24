' 静默启动桌宠（WorkBuddy 积分消耗统计）：双击运行，全程无黑色命令行窗口闪烁
' 桌宠自带同步：启动即同步一次 -> 之后每 15±2 分钟自动同步 -> 退出桌宠时同步一并停止。
' 路径随本文件自动解析（启动器在 scripts/，源码在 ../src/），整个文件夹移动后依然可用。
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")
base = fso.GetParentFolderName(WScript.ScriptFullName)
root = fso.GetParentFolderName(base)
script = fso.BuildPath(fso.BuildPath(root, "src"), "deskpet.py")
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
