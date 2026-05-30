# Script para iniciar o bot em modo LIVE em background
# Uso: .\start_live_bot.ps1 -Days 30 -Horizon "24h" -Interval 60

param(
    [int]$Days = 30,
    [string]$Horizon = "24h",
    [int]$Interval = 60
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Iniciando Bot BTC em Modo LIVE" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Dias de coleta: $Days" -ForegroundColor Yellow
Write-Host "Horizonte de previsao: $Horizon" -ForegroundColor Yellow
Write-Host "Intervalo de atualizacao: $Interval minutos" -ForegroundColor Yellow
Write-Host ""

# Obter a data/hora atual
$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "Inicio: $StartTime" -ForegroundColor Cyan

# Criar arquivo de log com caminho absoluto
$LogsDir = Join-Path -Path $PSScriptRoot -ChildPath "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
}

$LogFile = Join-Path -Path $LogsDir -ChildPath "live_bot_$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').log"

Write-Host "Log sera salvo em: $LogFile" -ForegroundColor Cyan
Write-Host ""

# Iniciar o bot em background
Write-Host "Iniciando processo em background..." -ForegroundColor Green

$ProcessArgs = @(
    "main.py",
    "--mode", "live",
    "--collect-days", $Days.ToString(),
    "--prediction-horizon", $Horizon,
    "--update-interval", $Interval.ToString()
)

# Redirecionar output para arquivo de log
$Process = Start-Process -FilePath "python" -ArgumentList $ProcessArgs -NoNewWindow -PassThru -RedirectStandardOutput $LogFile

$ProcessId = $Process.Id
Write-Host "Processo iniciado com PID: $ProcessId" -ForegroundColor Green
Write-Host ""

# Aguardar um pouco para confirmar que iniciou
Start-Sleep -Seconds 3

# Verificar se o processo ainda esta rodando
if ($Process.HasExited) {
    Write-Host "ERRO: Processo terminou inesperadamente!" -ForegroundColor Red
    Write-Host "Verifique o arquivo de log: $LogFile" -ForegroundColor Red
    exit 1
} else {
    Write-Host "Bot rodando com sucesso!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Para parar o bot abra uma nova janela do PowerShell e use:" -ForegroundColor Yellow
    Write-Host "  Stop-Process -Id $ProcessId" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Para monitorar o bot em tempo real, use:" -ForegroundColor Yellow
    Write-Host "  Get-Content -Path '$LogFile' -Wait" -ForegroundColor Yellow
}
