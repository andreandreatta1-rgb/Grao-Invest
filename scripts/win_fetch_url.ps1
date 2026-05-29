param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$OutFile,
  [int]$TimeoutSec = 20,
  [string]$UserAgent = "",
  [string]$AcceptLanguage = "pt-BR,pt;q=0.9,en;q=0.8"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$result = [ordered]@{
  ok = $false
  status = 0
  final_url = $Url
  content_type = ""
  out_file = $OutFile
  error = ""
}

try {
  $req = [System.Net.HttpWebRequest]::Create($Url)
  $req.Method = "GET"
  $req.Timeout = [Math]::Max(1000, $TimeoutSec * 1000)
  $req.ReadWriteTimeout = [Math]::Max(1000, $TimeoutSec * 1000)
  $req.AllowAutoRedirect = $true
  $req.MaximumAutomaticRedirections = 5
  if ($UserAgent) { $req.UserAgent = $UserAgent }
  if ($AcceptLanguage) { $req.Headers["Accept-Language"] = $AcceptLanguage }

  $resp = $req.GetResponse()
  try {
    $result.ok = $true
    try { $result.status = [int]($resp.StatusCode) } catch {}
    try { $result.final_url = [string]($resp.ResponseUri.AbsoluteUri) } catch {}
    try { $result.content_type = [string]($resp.ContentType) } catch {}

    $stream = $resp.GetResponseStream()
    if ($stream) {
      $fs = [System.IO.File]::Open($OutFile, [System.IO.FileMode]::Create)
      $stream.CopyTo($fs)
      $fs.Close()
      $stream.Close()
    }
  } finally {
    try { $resp.Close() } catch {}
  }
} catch {
  $ex = $_.Exception
  try { $result.error = [string]$ex.Message } catch {}

  if ($ex -and $ex.Response) {
    $webResp = $ex.Response
    try { $result.status = [int]($webResp.StatusCode) } catch {}
    try { $result.final_url = [string]($webResp.ResponseUri.AbsoluteUri) } catch {}
    try { $result.content_type = [string]($webResp.ContentType) } catch {}
    try {
      $stream = $webResp.GetResponseStream()
      if ($stream) {
        $fs = [System.IO.File]::Open($OutFile, [System.IO.FileMode]::Create)
        $stream.CopyTo($fs)
        $fs.Close()
        $stream.Close()
      }
    } catch {}
  }
}

$result | ConvertTo-Json -Compress
