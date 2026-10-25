$ErrorActionPreference = 'Stop'

$projectRoot = 'C:\Users\aaron\Pictures\AI-Intrusion-Detection'
$galleryRoot = 'C:\Users\aaron\Documents\Intruder Detection System Project\local-photo-gallery'
$activeMlRoot = 'C:\Users\aaron\Downloads\AI-Intrusion-Detection-main\AI-Intrusion-Detection-main'
$backupRoot = Join-Path $projectRoot 'backups'
$stamp = Get-Date -Format 'yyyy-MM-dd_HH-mm-ss'
$backupDir = Join-Path $backupRoot "phase1-$stamp"

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) { throw 'Project root is missing.' }
if (-not (Test-Path -LiteralPath $galleryRoot -PathType Container)) { throw 'Gallery root is missing.' }
if (-not (Test-Path -LiteralPath $activeMlRoot -PathType Container)) { throw 'Active ML root is missing.' }
New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null

$items = [System.Collections.Generic.List[object]]::new()
function Add-BackupFile([string]$source, [string]$relativeTarget) {
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Required file missing: $source" }
    $items.Add([pscustomobject]@{ Source = $source; RelativeTarget = $relativeTarget })
}
function Add-BackupDirectory([string]$sourceDir, [string]$relativeTarget, [string[]]$extensions = @()) {
    if (-not (Test-Path -LiteralPath $sourceDir -PathType Container)) { throw "Required directory missing: $sourceDir" }
    foreach ($file in Get-ChildItem -LiteralPath $sourceDir -File -Recurse) {
        if ($extensions.Count -gt 0 -and $file.Extension.ToLowerInvariant() -notin $extensions) { continue }
        $relative = [IO.Path]::GetRelativePath($sourceDir, $file.FullName)
        $items.Add([pscustomobject]@{ Source = $file.FullName; RelativeTarget = (Join-Path $relativeTarget $relative) })
    }
}

Add-BackupDirectory (Join-Path $galleryRoot 'captures') 'gallery/captures' @('.jpg')
Add-BackupDirectory (Join-Path $activeMlRoot 'ml/gallery_predictions') 'ml/gallery_predictions' @('.jpg', '.json', '.html')
Add-BackupDirectory (Join-Path $galleryRoot 'integrated') 'firmware/integrated' @('.ino', '.md')
Add-BackupDirectory (Join-Path $galleryRoot 'esp32cam_upload') 'firmware/esp32cam_upload' @('.ino', '.md')
Add-BackupDirectory (Join-Path $galleryRoot 'main_buzzer') 'firmware/main_buzzer' @('.ino', '.md')
Add-BackupDirectory (Join-Path $galleryRoot 'main_no_camera_log') 'firmware/main_no_camera_log' @('.ino', '.md')
Add-BackupDirectory (Join-Path $galleryRoot 'main_wait_five') 'firmware/main_wait_five' @('.ino', '.md')
Add-BackupDirectory (Join-Path $galleryRoot 'camera_diagnostic') 'firmware/camera_diagnostic' @('.ino', '.md')
Add-BackupFile (Join-Path $galleryRoot 'server.py') 'gallery/server.py'
Add-BackupFile (Join-Path $galleryRoot 'test_server.py') 'gallery/test_server.py'
Add-BackupFile (Join-Path $galleryRoot 'START_GALLERY.bat') 'gallery/START_GALLERY.bat'
Add-BackupFile (Join-Path $galleryRoot 'README.md') 'gallery/README.md'
Add-BackupFile (Join-Path $activeMlRoot 'ml/watch_gallery.py') 'ml/watch_gallery.py'
Add-BackupFile (Join-Path $activeMlRoot 'ml/detector.py') 'ml/detector.py'
Add-BackupFile (Join-Path $activeMlRoot 'ml/yolo11m.pt') 'ml/yolo11m.pt'
Add-BackupFile (Join-Path $activeMlRoot 'ml/yolo11n.pt') 'ml/yolo11n.pt'
Add-BackupFile (Join-Path $activeMlRoot 'ml/requirements.txt') 'ml/requirements.txt'
Add-BackupFile (Join-Path $activeMlRoot 'START_CAMERA_ML.bat') 'ml/START_CAMERA_ML.bat'
Add-BackupFile (Join-Path $projectRoot 'START_GALLERY.bat') 'launchers/START_GALLERY.bat'
Add-BackupFile (Join-Path $projectRoot 'START_CAMERA_ML.bat') 'launchers/START_CAMERA_ML.bat'
Add-BackupFile (Join-Path $projectRoot 'CAMERA_GALLERY_STEPS.txt') 'docs/CAMERA_GALLERY_STEPS.txt'
Add-BackupFile (Join-Path $projectRoot 'FULL_PROJECT_ROADMAP.md') 'docs/FULL_PROJECT_ROADMAP.md'

$manifest = [System.Collections.Generic.List[object]]::new()
foreach ($item in $items) {
    $destination = Join-Path $backupDir $item.RelativeTarget
    $destinationParent = Split-Path -Parent $destination
    New-Item -ItemType Directory -Path $destinationParent -Force | Out-Null
    Copy-Item -LiteralPath $item.Source -Destination $destination -ErrorAction Stop
    $sourceHash = (Get-FileHash -LiteralPath $item.Source -Algorithm SHA256).Hash
    $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if ($sourceHash -ne $destinationHash) { throw "Hash mismatch: $($item.Source)" }
    $manifest.Add([pscustomobject]@{
        source = $item.Source
        backup = $item.RelativeTarget.Replace('\', '/')
        bytes = (Get-Item -LiteralPath $destination).Length
        sha256 = $sourceHash
    })
}

$manifestPath = Join-Path $backupDir 'manifest.json'
$manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $manifestPath -Encoding utf8
$summary = [pscustomobject]@{
    createdAt = (Get-Date).ToString('o')
    backupDirectory = $backupDir
    totalFiles = $manifest.Count
    totalBytes = ($manifest | Measure-Object bytes -Sum).Sum
    captureFiles = @($manifest | Where-Object { $_.backup -like 'gallery/captures/*' }).Count
    predictionJsonFiles = @($manifest | Where-Object { $_.backup -like 'ml/gallery_predictions/*.json' }).Count
    predictionJpegFiles = @($manifest | Where-Object { $_.backup -like 'ml/gallery_predictions/*.jpg' }).Count
    allHashesMatched = $true
}
$summary | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $backupDir 'summary.json') -Encoding utf8
$summary | Format-List
