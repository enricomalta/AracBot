# Deprecated daemon launcher retained as a one-cycle local smoke test.
# Production scheduling is POST /api/cron from cron-job.org; it never starts a
# local background process or sleeps between analyses.
param()

Write-Host "Executing one serverless analysis cycle locally..." -ForegroundColor Cyan
py -3 main.py --mode live
