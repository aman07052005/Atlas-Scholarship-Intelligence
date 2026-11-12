$ErrorActionPreference = "Stop"
Write-Host "Atlas Scholarship Intelligence - release verification" -ForegroundColor Cyan
python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Automated tests failed." }
python scripts/validate_package.py
if ($LASTEXITCODE -ne 0) { throw "Package validation failed." }
python scripts/run_local_fixture.py
if ($LASTEXITCODE -ne 0) { throw "Local crawler fixture failed." }
Write-Host "Local release checks passed. Run python scripts/run_live_crawl.py and streamlit run app.py on a network-enabled machine for external acceptance." -ForegroundColor Green
