<#
.SYNOPSIS
Compiles a TeX submission through an isolated Windows TinyTeX drive alias.

.DESCRIPTION
TeX Live can fail while canonicalizing sandboxed AppData ancestors. This
launcher maps the existing TinyTeX root to a free temporary drive, invokes the
bundled Perl and latexmk.pl convergence loop, validates the final PDF/log/BibTeX
state, and restores location, PATH, and the drive table in a finally block.
It never installs packages or copies the TinyTeX tree.

.PARAMETER TexFile
TeX source to compile. Relative paths are resolved from the invocation folder.

.PARAMETER TinyTexRoot
TinyTeX root. Defaults to $env:APPDATA\TinyTeX.

.PARAMETER OutputDirectory
Directory for PDF and working outputs. Defaults to the TeX source directory.

.PARAMETER DriveLetter
Optional free drive letter from D through Z. The highest free letter is used
when this parameter is omitted.

.PARAMETER PlanOnly
Prints the resolved command and cleanup plan as JSON without mapping or running
TeX.

.EXAMPLE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  scripts\compile_ijds_submission_windows.ps1 `
  -TexFile paper\submission\CRPTO_ijds_submission.tex `
  -OutputDirectory paper\submission
#>
[CmdletBinding()]
param(
    [string]$TexFile = "",
    [string]$TinyTexRoot = "",
    [string]$OutputDirectory = "",
    [ValidatePattern("^[D-Zd-z]$")]
    [string]$DriveLetter = "",
    [switch]$PlanOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AbsolutePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$BaseDirectory
    )

    if ([System.IO.Path]::IsPathRooted($Path)) {
        return [System.IO.Path]::GetFullPath($Path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $BaseDirectory $Path))
}

function Test-PathWithin {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Candidate,
        [Parameter(Mandatory = $true)]
        [string]$Root
    )

    $trimCharacters = [char[]]@("\", "/")
    $rootWithSeparator = $Root.TrimEnd($trimCharacters) + [System.IO.Path]::DirectorySeparatorChar
    return $Candidate.Equals($Root, [System.StringComparison]::OrdinalIgnoreCase) -or
        $Candidate.StartsWith(
            $rootWithSeparator,
            [System.StringComparison]::OrdinalIgnoreCase
        )
}

function Get-SubstExecutable {
    if (-not $env:SystemRoot) {
        throw "SystemRoot is unavailable; cannot locate subst.exe."
    }
    $candidate = Join-Path $env:SystemRoot "System32\subst.exe"
    if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
        throw "subst.exe is unavailable at $candidate."
    }
    return $candidate
}

function Test-DriveLetterInUse {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Letter,
        [Parameter(Mandatory = $true)]
        [string]$SubstExecutable
    )

    if (Get-PSDrive -Name $Letter -PSProvider FileSystem -ErrorAction SilentlyContinue) {
        return $true
    }
    $substLines = & $SubstExecutable 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "subst.exe could not enumerate existing drive aliases."
    }
    return [bool]($substLines | Where-Object { $_ -match "^$Letter`:\\:" })
}

function Get-FreeDriveLetter {
    param(
        [string]$Preferred,
        [Parameter(Mandatory = $true)]
        [string]$SubstExecutable
    )

    if ($Preferred) {
        $normalized = $Preferred.ToUpperInvariant()
        if (Test-DriveLetterInUse -Letter $normalized -SubstExecutable $SubstExecutable) {
            throw "Requested drive letter $normalized`: is already in use."
        }
        return $normalized
    }

    for ($code = [int][char]"Z"; $code -ge [int][char]"D"; $code--) {
        $candidate = ([char]$code).ToString()
        if (-not (Test-DriveLetterInUse -Letter $candidate -SubstExecutable $SubstExecutable)) {
            return $candidate
        }
    }
    throw "No free drive letter is available from D: through Z:."
}

function Assert-LatexConvergence {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Directory,
        [Parameter(Mandatory = $true)]
        [string]$JobName,
        [Parameter(Mandatory = $true)]
        [string]$LatexmkTranscript
    )

    $pdfPath = Join-Path $Directory "$JobName.pdf"
    $logPath = Join-Path $Directory "$JobName.log"
    $auxPath = Join-Path $Directory "$JobName.aux"
    foreach ($required in @($pdfPath, $logPath, $LatexmkTranscript)) {
        if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
            throw "Required LaTeX output is missing: $required"
        }
        if ((Get-Item -LiteralPath $required).Length -le 0) {
            throw "Required LaTeX output is empty: $required"
        }
    }

    $logText = [System.IO.File]::ReadAllText($logPath)
    $transcriptText = [System.IO.File]::ReadAllText($LatexmkTranscript)
    $failurePatterns = [ordered]@{
        "undefined references" = 'There were undefined references'
        "undefined citations" = 'Citation `[^`]+`.*undefined'
        "undefined labels" = 'Reference `[^`]+`.*undefined'
        "rerun requested" = 'Rerun to get cross-references right|Label\(s\) may have changed'
        "missing characters" = 'Missing character:'
        "fatal LaTeX error" = '(^|\r?\n)! |Fatal error occurred'
    }
    $failures = New-Object System.Collections.Generic.List[string]
    foreach ($entry in $failurePatterns.GetEnumerator()) {
        if ([System.Text.RegularExpressions.Regex]::IsMatch($logText, $entry.Value)) {
            $failures.Add($entry.Key)
        }
    }
    if ($failures.Count -gt 0) {
        throw "LaTeX did not converge cleanly: $($failures -join ', ')."
    }

    $pageMatches = [System.Text.RegularExpressions.Regex]::Matches(
        $logText,
        "Output written on .+?\(([0-9]+) pages?,"
    )
    if ($pageMatches.Count -eq 0) {
        throw "LaTeX log does not contain a parseable positive page count."
    }
    $pageCount = [int]$pageMatches[$pageMatches.Count - 1].Groups[1].Value
    if ($pageCount -le 0) {
        throw "LaTeX log reported a nonpositive page count: $pageCount."
    }
    if ($transcriptText -notmatch "Latexmk: All targets .* are up-to-date") {
        throw "latexmk did not report that all targets reached a fixed point."
    }

    if (Test-Path -LiteralPath $auxPath -PathType Leaf) {
        $auxText = [System.IO.File]::ReadAllText($auxPath)
        if ($auxText -match "\\bibdata") {
            $blgPath = Join-Path $Directory "$JobName.blg"
            $bblPath = Join-Path $Directory "$JobName.bbl"
            if (-not (Test-Path -LiteralPath $blgPath -PathType Leaf)) {
                throw "Bibliography was requested but the BibTeX log is missing: $blgPath"
            }
            if (-not (Test-Path -LiteralPath $bblPath -PathType Leaf) -or
                (Get-Item -LiteralPath $bblPath).Length -le 0) {
                throw "Bibliography was requested but the rendered bibliography is missing or empty: $bblPath"
            }
            $blgText = [System.IO.File]::ReadAllText($blgPath)
            if ($blgText -match "(?m)^Warning--") {
                throw "BibTeX emitted one or more warnings; inspect $blgPath."
            }
        }
    }

    return $pageCount
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$invocationRoot = (Get-Location).Path
if (-not $TexFile) {
    $TexFile = Join-Path $repoRoot "paper\submission\CRPTO_ijds_submission.tex"
}
if (-not $TinyTexRoot) {
    if (-not $env:APPDATA) {
        throw "APPDATA is unavailable; pass -TinyTexRoot explicitly."
    }
    $TinyTexRoot = Join-Path $env:APPDATA "TinyTeX"
}

$texPath = Get-AbsolutePath -Path $TexFile -BaseDirectory $invocationRoot
$tinyTexPath = Get-AbsolutePath -Path $TinyTexRoot -BaseDirectory $invocationRoot
if (-not (Test-Path -LiteralPath $texPath -PathType Leaf)) {
    throw "TeX source does not exist: $texPath"
}
if (-not (Test-Path -LiteralPath $tinyTexPath -PathType Container)) {
    throw "TinyTeX root does not exist: $tinyTexPath"
}

$sourceDirectory = Split-Path -Parent $texPath
if (-not $OutputDirectory) {
    $outputPath = $sourceDirectory
} else {
    $outputPath = Get-AbsolutePath -Path $OutputDirectory -BaseDirectory $invocationRoot
}
if (Test-PathWithin -Candidate $outputPath -Root $tinyTexPath) {
    throw "Output directory must not be TinyTeX itself or a descendant of TinyTeX."
}

$requiredTinyTexFiles = @(
    "bin\windows\pdflatex.exe",
    "bin\windows\bibtex.exe",
    "tlpkg\tlperl\bin\perl.exe",
    "texmf-dist\scripts\latexmk\latexmk.pl",
    "texmf-dist\web2c\texmf.cnf"
)
foreach ($relative in $requiredTinyTexFiles) {
    $required = Join-Path $tinyTexPath $relative
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "TinyTeX payload is incomplete; missing $required"
    }
}

$substExecutable = Get-SubstExecutable
$selectedDrive = Get-FreeDriveLetter -Preferred $DriveLetter -SubstExecutable $substExecutable
$driveRoot = "$selectedDrive`:"
$aliasedPerl = "$driveRoot\tlpkg\tlperl\bin\perl.exe"
$aliasedLatexmk = "$driveRoot\texmf-dist\scripts\latexmk\latexmk.pl"
$aliasedBin = "$driveRoot\bin\windows"
$aliasedPerlBin = "$driveRoot\tlpkg\tlperl\bin"
$jobName = [System.IO.Path]::GetFileNameWithoutExtension($texPath)
$transcriptPath = Join-Path $outputPath "$jobName.latexmk.txt"
$latexmkArguments = @(
    "-pdf",
    "-gg",
    "-interaction=nonstopmode",
    "-halt-on-error",
    "-file-line-error",
    "-bibtexfudge-",
    "-outdir=$outputPath",
    [System.IO.Path]::GetFileName($texPath)
)

if ($PlanOnly) {
    [ordered]@{
        drive = "$selectedDrive`:"
        tinytex_root = $tinyTexPath
        working_directory = $sourceDirectory
        output_directory = $outputPath
        transcript = $transcriptPath
        command = @($aliasedPerl, $aliasedLatexmk) + $latexmkArguments
        environment = [ordered]@{
            path_prefix = "$aliasedPerlBin;$aliasedBin"
            bibinputs_prefix = $sourceDirectory
            bstinputs_prefix = $sourceDirectory
        }
        cleanup = @(
            "restore location",
            "restore process PATH and TeX search paths",
            "subst $selectedDrive`: /D"
        )
    } | ConvertTo-Json -Depth 4
    exit 0
}

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw "This launcher supports Windows only."
}
if (-not (Test-Path -LiteralPath $outputPath -PathType Container)) {
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
}

$originalPath = $env:PATH
$originalBibInputs = $env:BIBINPUTS
$originalBstInputs = $env:BSTINPUTS
$mapped = $false
$locationPushed = $false
$primaryError = $null
$cleanupFailures = New-Object System.Collections.Generic.List[string]

try {
    & $substExecutable "$selectedDrive`:" $tinyTexPath | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "subst.exe failed to map $selectedDrive`: to $tinyTexPath."
    }
    $mapped = $true
    if (-not (Test-Path -LiteralPath $aliasedPerl -PathType Leaf) -or
        -not (Test-Path -LiteralPath $aliasedLatexmk -PathType Leaf)) {
        throw "TinyTeX alias $selectedDrive`: does not expose the declared Perl/latexmk payload."
    }

    $env:PATH = "$aliasedPerlBin;$aliasedBin;$originalPath"
    # latexmk runs BibTeX from -outdir. Prefixing the source folder preserves
    # source-relative bibliography/style paths when output is elsewhere.
    $env:BIBINPUTS = "$sourceDirectory;$originalBibInputs"
    $env:BSTINPUTS = "$sourceDirectory;$originalBstInputs"
    Push-Location $sourceDirectory
    $locationPushed = $true

    if (Test-Path -LiteralPath $transcriptPath -PathType Leaf) {
        [System.IO.File]::Delete($transcriptPath)
    }
    $nativeOutput = $null
    $nativeExitCode = $null
    $savedErrorActionPreference = $ErrorActionPreference
    try {
        # latexmk is the convergence loop. Use its bundled Perl script directly;
        # TinyTeX's Windows latexmk.exe/runscript wrapper is not reliable here.
        $ErrorActionPreference = "Continue"
        $nativeOutput = & $aliasedPerl $aliasedLatexmk @latexmkArguments 2>&1
        $nativeExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $savedErrorActionPreference
    }

    $nativeLines = @($nativeOutput | ForEach-Object { $_.ToString() })
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText(
        $transcriptPath,
        (($nativeLines -join [System.Environment]::NewLine) + [System.Environment]::NewLine),
        $utf8NoBom
    )
    if ($nativeExitCode -ne 0) {
        throw "latexmk failed with exit code $nativeExitCode; inspect $transcriptPath."
    }

    $convergenceParameters = @{
        Directory = $outputPath
        JobName = $jobName
        LatexmkTranscript = $transcriptPath
    }
    $pages = Assert-LatexConvergence @convergenceParameters
    Write-Output "Converged official PDF: $(Join-Path $outputPath "$jobName.pdf") ($pages pages)."
} catch {
    $primaryError = $_
} finally {
    if ($locationPushed) {
        try {
            Pop-Location
        } catch {
            $cleanupFailures.Add("could not restore the original location: $($_.Exception.Message)")
        }
    }
    try {
        $env:PATH = $originalPath
        if ($null -eq $originalBibInputs) {
            Remove-Item Env:BIBINPUTS -ErrorAction SilentlyContinue
        } else {
            $env:BIBINPUTS = $originalBibInputs
        }
        if ($null -eq $originalBstInputs) {
            Remove-Item Env:BSTINPUTS -ErrorAction SilentlyContinue
        } else {
            $env:BSTINPUTS = $originalBstInputs
        }
    } catch {
        $cleanupFailures.Add(
            "could not restore process PATH/BIBINPUTS/BSTINPUTS: $($_.Exception.Message)"
        )
    }
    if ($mapped) {
        try {
            & $substExecutable "$selectedDrive`:" "/D" | Out-Null
            if ($LASTEXITCODE -ne 0) {
                throw "subst.exe returned exit code $LASTEXITCODE"
            }
            $driveCheckParameters = @{
                Letter = $selectedDrive
                SubstExecutable = $substExecutable
            }
            if (Test-DriveLetterInUse @driveCheckParameters) {
                throw "drive alias remains mounted"
            }
        } catch {
            $cleanupFailures.Add("could not remove $selectedDrive`: alias: $($_.Exception.Message)")
        }
    }
}

if ($cleanupFailures.Count -gt 0) {
    $primaryContext = ""
    if ($null -ne $primaryError) {
        $primaryContext = " Primary failure: $($primaryError.Exception.Message)"
    }
    throw "Windows LaTeX cleanup failed: $($cleanupFailures -join '; ').$primaryContext"
}
if ($null -ne $primaryError) {
    throw $primaryError
}
