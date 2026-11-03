# Bootstrap: requires Python 3.8+ -> https://www.python.org/downloads/
# Under `irm | iex` $PSScriptRoot is empty -> always download install.py.
$local = ''
if ($PSScriptRoot) { $local = Join-Path $PSScriptRoot 'install.py' }
if (-not $local -or -not (Test-Path $local)) {
    $local = Join-Path $env:TEMP 'da-install.py'
    Invoke-WebRequest -Headers @{ Accept = 'application/vnd.github.raw'; 'User-Agent' = 'devin-agentic' } `
        'https://api.github.com/repos/JoShMiQueL/devin-agentic/contents/install.py' -OutFile $local
}
& python $local @args
