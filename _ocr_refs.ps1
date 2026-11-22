$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime

function Await($op) {
    while ($op.Status -eq [Windows.Foundation.AsyncStatus]::Started) { Start-Sleep -Milliseconds 10 }
    if ($op.Status -ne [Windows.Foundation.AsyncStatus]::Completed) { throw "async failed: $($op.Status)" }
    return $op.GetResults()
}

[Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.StorageFile, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null
[Windows.Graphics.Imaging.BitmapDecoder, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

$lang = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]::new('en-US')
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) { throw 'no OCR engine' }

$root = 'C:\Users\Chaitrangan\Downloads\EXPENSE_MANAGER\reference'
foreach ($i in 1..4) {
    $path = Join-Path $root "picture-$i.jpg"
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path))
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read))
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream))
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync())
    $result = Await ($engine.RecognizeAsync($bitmap))
    Write-Output "===== PICTURE $i  ($($decoder.PixelWidth)x$($decoder.PixelHeight)) ====="
    foreach ($line in $result.Lines) {
        $words = ($line.Words | ForEach-Object { $_.Text }) -join ' '
        $box = $line.Words[0].BoundingRect
        Write-Output ("[{0,4},{1,4}] {2}" -f [int]$box.X, [int]$box.Y, $words)
    }
    $stream.Dispose()
}
