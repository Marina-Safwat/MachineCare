$ErrorActionPreference = 'Stop'
Set-Location "$PSScriptRoot/app"
if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) { throw 'Install Flutter and add its bin directory to PATH first. See README.md.' }
$manifest = Get-Content pubspec.yaml -Raw
flutter create --project-name machinecare --platforms web .
if ($LASTEXITCODE -ne 0) { throw 'Flutter project generation failed.' }
Set-Content -Path pubspec.yaml -Value $manifest -Encoding utf8
flutter pub get
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
flutter analyze
if ($LASTEXITCODE -ne 0) { Write-Warning 'Review Flutter analysis output before presenting.' }
Write-Host 'Project prepared. Start the backend, then run the command in README.md.'
