# Usage:
#   powershell -ExecutionPolicy Bypass -File .\infra\gst_test_win.ps1

# 1) Video path hiện tại của bạn
$VideoPath = "D:\DockerData\video-pipeline\data\videos\Midtown corner store surveillance video 11-25-18.mp4"
if (-not (Test-Path $VideoPath)) {
  Write-Error "Video file not found: $VideoPath"
  exit 1
}

# 2) Tìm gst-launch-1.0.exe
$gstExe = $null
$probe = (Get-Command gst-launch-1.0 -ErrorAction SilentlyContinue)
if ($probe -and (Test-Path $probe.Source)) { $gstExe = $probe.Source }
if (-not $gstExe) {
  $candidates = @(
    "C:\Program Files\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe",
    "C:\gstreamer\1.0\msvc_x86_64\bin\gst-launch-1.0.exe"
  )
  foreach ($c in $candidates) { if (Test-Path $c) { $gstExe = $c; break } }
}
if (-not $gstExe) { Write-Error "Cannot find gst-launch-1.0.exe"; exit 1 }

# 3) Chuyển Windows path -> file URI (file:///D:/path/to/file.mp4)
$uri = "file:///" + ($VideoPath -replace '\\','/')

Write-Host "Using GStreamer:" $gstExe
Write-Host "Using URI:" $uri

# 4) Lệnh đầy đủ (audio + video) dùng uridecodebin
$cmdFull = "`"$gstExe`" -v uridecodebin uri=`"$uri`" name=dec dec. ! queue ! videoconvert ! autovideosink dec. ! queue ! audioconvert ! audioresample ! autoaudiosink"

# 5) Lệnh fallback không audio
$cmdNoAudio = "`"$gstExe`" -v uridecodebin uri=`"$uri`" ! videoconvert ! autovideosink"

Write-Host "Running (with audio):"
Write-Host $cmdFull
cmd /c $cmdFull
if ($LASTEXITCODE -ne 0) {
  Write-Warning "Full pipeline failed. Trying without audio..."
  Write-Host $cmdNoAudio
  cmd /c $cmdNoAudio
}
