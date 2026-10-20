param(
    [switch]$Probe,
    [string]$ImagePath,
    [string]$OutputPath,
    [string]$Language = 'auto'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType=WindowsRuntime]
$null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]

function Await-Result($Operation, [Type]$ResultType) {
    $method = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and
        $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
    } | Select-Object -First 1
    $task = $method.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    $task.GetAwaiter().GetResult()
}

$available = @([Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages | ForEach-Object { $_.LanguageTag })
if ($Probe) {
    @{engine='Windows.Media.Ocr';languages=$available;max_image_dimension=[Windows.Media.Ocr.OcrEngine]::MaxImageDimension} | ConvertTo-Json -Compress
    exit 0
}
if (-not $ImagePath -or -not $OutputPath) { throw 'ImagePath and OutputPath are required.' }
if (Test-Path -LiteralPath $OutputPath) { throw 'OCR output exists; preserve the previous result.' }
if ($Language -eq 'auto') {
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
} else {
    $lang = New-Object Windows.Globalization.Language($Language)
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
}
if (-not $engine) { throw 'Requested OCR language is not available locally.' }
$imageAbsolute = (Resolve-Path -LiteralPath $ImagePath).Path
$file = Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync($imageAbsolute)) ([Windows.Storage.StorageFile])
$stream = Await-Result ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
try {
    $decoder = Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    try {
        if ($bitmap.PixelWidth -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension -or $bitmap.PixelHeight -gt [Windows.Media.Ocr.OcrEngine]::MaxImageDimension) { throw 'Image exceeds local OCR engine dimension limit.' }
        $result = Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        $lines = @($result.Lines | ForEach-Object {
            $line = $_
            @{text=$line.Text;words=@($line.Words | ForEach-Object {
                @{text=$_.Text;box=@($_.BoundingRect.X,$_.BoundingRect.Y,$_.BoundingRect.Width,$_.BoundingRect.Height);confidence=$null}
            })}
        })
        $record = @{engine='Windows.Media.Ocr';language=$engine.RecognizerLanguage.LanguageTag;text=($result.Lines.Text -join "`n");lines=$lines;confidence=$null;width=$bitmap.PixelWidth;height=$bitmap.PixelHeight;review_status='OCR_UNVERIFIED'}
        $json = $record | ConvertTo-Json -Depth 12
        [System.IO.File]::WriteAllText($OutputPath, $json, (New-Object System.Text.UTF8Encoding($false)))
    } finally { if ($bitmap) { $bitmap.Dispose() } }
} finally { if ($stream) { $stream.Dispose() } }
