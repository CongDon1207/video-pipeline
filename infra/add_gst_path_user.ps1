param(
  [string]$GstBin = "C:\Program Files\gstreamer\1.0\msvc_x86_64\bin"
)

# 1) Validate binary path
$exe = Join-Path $GstBin "gst-launch-1.0.exe"
if (-not (Test-Path $exe)) {
  Write-Error "gst-launch-1.0.exe not found in: $GstBin"
  exit 1
}

# 2) Read current User PATH
$old = [Environment]::GetEnvironmentVariable("Path","User")

# 3) Compose new PATH (avoid duplicate)
if ([string]::IsNullOrEmpty($old)) {
  $new = $GstBin
} elseif ($old -notlike "*$GstBin*") {
  $new = $old.TrimEnd(';') + ';' + $GstBin
} else {
  Write-Host "User PATH already contains: $GstBin"
  $new = $old
}

# 4) Write back User PATH
[Environment]::SetEnvironmentVariable("Path", $new, "User")
Write-Host "User PATH updated. Please close and reopen PowerShell."
Write-Host "Then run: gst-launch-1.0 --version"
