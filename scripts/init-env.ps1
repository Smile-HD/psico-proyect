# Create .env from .env.example when missing (dev-only defaults).
$ErrorActionPreference = 'Stop'

if (Test-Path .env) {
  Write-Host '.env already exists; leaving it untouched.'
} else {
  Copy-Item .env.example .env
  Write-Host 'Created .env from .env.example (dev-only defaults — override before real use).'
}
