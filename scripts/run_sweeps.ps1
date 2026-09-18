# run_sweeps.ps1 - os sweeps exploratorios, em orcamento reduzido.
#
# ASCII puro, sem acentos, pela mesma razao do setup.ps1: o Windows PowerShell 5.1 le
# .ps1 como ANSI quando o arquivo nao tem BOM, e acento vira erro de parse.
#
# POR QUE ORCAMENTO REDUZIDO (pop 120 x 60 geracoes, ~16% do custo): experimento
# exploratorio quer ORDENACAO entre configuracoes, e ordenacao transfere de orcamento.
# Numero citavel nao transfere - esse sai da bateria (run_battery.ps1). Os artefatos daqui
# vao para results/exploratory/, fora dos caminhos que o compare_algorithms le.
#
# POR QUE OS TRES SWEEPS NO MESMO SCRIPT: eles COMPARTILHAM o braco default (passo 1).
# Rodado uma vez, serve de ancora aos tres - e, mais importante, garante que os 16 bracos
# saiam do MESMO digest de motor. Foi exatamente isso que faltou em 2026-09-17: os bracos
# de lambda rodaram antes de um refactor e os de peso depois, e metade do conjunto passou a
# se declarar obsoleta enquanto a outra metade se declarava atual. Comportamento identico,
# leitura incoerente.
#
# POR QUE SO O AG ESCALAR: a fronteira do NSGA-II e lambda-independente
# (nsga2.scalar_objective le os LAMBDA_* so para ESCOLHER o scalar_optimum, nunca para
# buscar), e elitismo/torneio sao lidos so por operators.next_generation e
# tournament_selection - o NSGA-II usa rank de Pareto e torneio binario. Rodar o NSGA-II
# por braco mediria o mesmo numero N vezes.
#
# Uso:
#   .\scripts\run_sweeps.ps1                 # roda tudo, na ordem
#   .\scripts\run_sweeps.ps1 -From 6         # retoma a partir do passo 6
#   .\scripts\run_sweeps.ps1 -WhatIf         # so lista os passos e o custo

param(
    [int]    $From = 1,
    [switch] $WhatIf
)

$ErrorActionPreference = "Stop"
# Os scripts moram em scripts/ e rodam a partir da raiz do projeto: `-m src...` e main.py
# sao resolvidos pelo diretorio corrente.
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$py = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Ambiente nao encontrado. Rode .\scripts\setup.ps1 primeiro." }
$env:PYTHONIOENCODING = "utf-8"

$base = @("-m", "src.experiments.multi_run", "--algorithm", "ga", "--n-seeds", "5",
          "--pop", "120", "--generations", "60")

# Os `Min` sao ESTIMATIVAS com o pool persistente: ~10,4 min por braco medidos em
# 2026-09-18 com o pool recriado por geracao, escalados pela razao que o AG mostrou na
# seed 42 (6,7 -> 3,0 min) e por +13% da semente por luta (CRN).
#
# O default vem primeiro: os tres sweeps o usam como ancora, e uma interrupcao no meio
# ainda deixa a ancora no disco.
$passos = @(
    @{ N = 1; Min = 6; Nome = "ANCORA - default (elitismo 0,10 | torneio 3 | lambda 1,0)"
       Args = $base }

    # --- elitismo: o braco 0 e o informativo, como o 1/0/0 foi nos pesos do dominance ---
    @{ N = 2; Min = 6; Nome = "elitismo 0,00 - sem elitismo (mostra o que ele segura)"
       Args = $base + @("--elite-rate", "0") }
    @{ N = 3; Min = 6; Nome = "elitismo 0,05"
       Args = $base + @("--elite-rate", "0.05") }
    @{ N = 4; Min = 6; Nome = "elitismo 0,20"
       Args = $base + @("--elite-rate", "0.20") }
    @{ N = 5; Min = 6; Nome = "elitismo 0,30"
       Args = $base + @("--elite-rate", "0.30") }

    # --- torneio: pressao seletiva; 2 e quase aleatorio, 7 e quase greedy ---
    @{ N = 6; Min = 6; Nome = "torneio 2 - pressao seletiva minima"
       Args = $base + @("--tournament-size", "2") }
    @{ N = 7; Min = 6; Nome = "torneio 5"
       Args = $base + @("--tournament-size", "5") }
    @{ N = 8; Min = 6; Nome = "torneio 7 - pressao seletiva alta"
       Args = $base + @("--tournament-size", "7") }

    # --- lambda: re-rodados sob o motor final (ver o cabecalho) ---
    @{ N = 9;  Min = 6; Nome = "lambda_drift 0,25 - equilibrio pesa 4x"
       Args = $base + @("--lambda-drift", "0.25") }
    @{ N = 10; Min = 6; Nome = "lambda_drift 0,5"
       Args = $base + @("--lambda-drift", "0.5") }
    @{ N = 11; Min = 6; Nome = "lambda_drift 2,0"
       Args = $base + @("--lambda-drift", "2") }
    @{ N = 12; Min = 6; Nome = "lambda_drift 4,0 - identidade pesa 4x"
       Args = $base + @("--lambda-drift", "4") }

    # --- pesos do dominance: idem. Comparar pelos TERMOS, nunca pelo composto ---
    @{ N = 13; Min = 6; Nome = "pesos 1 / 2 / 0,5 - cap dobrado"
       Args = $base + @("--dom-cap", "2") }
    @{ N = 14; Min = 6; Nome = "pesos 1 / 1 / 1 - secundarios no peso do primario"
       Args = $base + @("--dom-cap", "1", "--dom-decis", "1") }
    @{ N = 15; Min = 6; Nome = "pesos 1 / 0,5 / 0 - sem o piso de decisividade"
       Args = $base + @("--dom-decis", "0") }
    @{ N = 16; Min = 6; Nome = "pesos 1 / 0 / 0 - a falsificacao: so o termo primario"
       Args = $base + @("--dom-cap", "0", "--dom-decis", "0") }
)

$restantes = @($passos | Where-Object { $_.N -ge $From })
if ($restantes.Count -eq 0) { throw "-From $From nao deixa nenhum passo (max: $($passos.Count))." }
# ForEach-Object antes do Measure-Object: no PS 5.1 o -Property nao enxerga chave de
# hashtable, so propriedade de objeto.
$total = ($restantes | ForEach-Object { $_.Min } | Measure-Object -Sum).Sum

Write-Host ""
Write-Host "  SWEEPS EXPLORATORIOS - pop 120 x 60 geracoes, 5 sementes, so o AG escalar" -ForegroundColor Cyan
$horas = [int][math]::Floor($total / 60)
$mins  = [int]($total % 60)
Write-Host "  $($restantes.Count) passos, custo estimado ${horas}h$('{0:d2}' -f $mins)m"
Write-Host ""
foreach ($p in $restantes) {
    Write-Host ("    {0,2}. {1,-60} ~{2,3} min" -f $p.N, $p.Nome, $p.Min)
}
Write-Host ""

if ($WhatIf) { Write-Host "  (-WhatIf: nada foi executado)"; exit 0 }

$inicio = Get-Date
foreach ($p in $restantes) {
    $t0 = Get-Date
    Write-Host ""
    Write-Host "  === passo $($p.N)/$($passos.Count) - $($p.Nome)" -ForegroundColor Yellow
    Write-Host ""
    & $py @($p.Args)
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "  x passo $($p.N) FALHOU (exit $LASTEXITCODE)." -ForegroundColor Red
        Write-Host "    Os passos anteriores estao salvos. Retome com:" -ForegroundColor Red
        Write-Host "      .\scripts\run_sweeps.ps1 -From $($p.N)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    $dt = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    Write-Host "  ok passo $($p.N) em $dt min" -ForegroundColor Green
}

$dtTotal = [math]::Round(((Get-Date) - $inicio).TotalMinutes, 1)
Write-Host ""
Write-Host "  SWEEPS COMPLETOS em $dtTotal min" -ForegroundColor Green
Write-Host ""
Write-Host "  Os 16 bracos devem sair do MESMO digest de motor. Confira com:"
Write-Host "      py -m src.tests.test_provenance"
Write-Host "  Todos devem aparecer como 'braco de experimento' (o default, como 'atual')."
Write-Host "  Qualquer 'obsoleto' significa que o motor mudou no meio - refaca aquele braco."
Write-Host ""
