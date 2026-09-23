# run_hybrid_sweep.ps1 - escolhe a configuracao do hibrido NSGA-II -> AG escalar.
#
# ASCII puro, sem acentos, pela mesma razao do setup.ps1: o Windows PowerShell 5.1 le
# .ps1 como ANSI quando o arquivo nao tem BOM, e acento vira erro de parse.
#
# O QUE ESTE SWEEP DECIDE: como repartir o orcamento entre as duas fases (split) e o que
# a fase de Pareto entrega a fase escalar (a fronteira inteira ou um ponto so). NAO decide
# se o hibrido e melhor que o AG escalar - isso e a bateria que mede, com n = 20 e o teste
# pareado. Orcamento reduzido ordena configuracoes; nao declara vencedor entre algoritmos.
#
# SEMENTES 1000-1004, DISJUNTAS DAS DA BATERIA (42-61), pela mesma razao do run_sweeps:
# a amostra que ESCOLHE a configuracao nao pode ser a que a AVALIA.
#
# O PASSO 1 E A ANCORA: o AG escalar no mesmo orcamento e nas mesmas sementes. Sem ele
# nao existe contra o que comparar os bracos - e ele tem de sair do MESMO digest de motor,
# por isso roda aqui dentro em vez de ser reaproveitado de um sweep anterior.
#
# Uso:
#   .\scripts\run_hybrid_sweep.ps1              # roda tudo, na ordem
#   .\scripts\run_hybrid_sweep.ps1 -From 4      # retoma a partir do passo 4
#   .\scripts\run_hybrid_sweep.ps1 -WhatIf      # so lista os passos e o custo

param(
    [int]    $From = 1,
    [switch] $WhatIf
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$py = Join-Path $raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Ambiente nao encontrado. Rode .\scripts\setup.ps1 primeiro." }
$env:PYTHONIOENCODING = "utf-8"

$base = @("-m", "src.experiments.multi_run", "--n-seeds", "5",
          "--seed-start", "1000", "--pop", "120", "--generations", "60")

# O hibrido custa mais que o escalar no mesmo orcamento: a fase de Pareto avalia pais +
# filhos (2x pop por geracao). Um split s custa ~ (1 + s) vezes o escalar.
$passos = @(
    @{ N = 1; Min = 6; Nome = "ANCORA - AG escalar (contra quem os bracos sao lidos)"
       Args = $base + @("--algorithm", "ga") }

    @{ N = 2; Min = 8; Nome = "hibrido split 0,25 - fronteira inteira"
       Args = $base + @("--algorithm", "hybrid", "--hybrid-split", "0.25", "--hybrid-carry", "front") }

    @{ N = 3; Min = 9; Nome = "hibrido split 0,50 - fronteira inteira (o default)"
       Args = $base + @("--algorithm", "hybrid", "--hybrid-split", "0.5", "--hybrid-carry", "front") }

    @{ N = 4; Min = 11; Nome = "hibrido split 0,75 - fronteira inteira"
       Args = $base + @("--algorithm", "hybrid", "--hybrid-split", "0.75", "--hybrid-carry", "front") }

    # Carregar UM ponto em vez da fronteira: isola quanto do efeito vem da DIVERSIDADE
    # preservada e quanto vem so de comecar de um roster bom. E a pergunta que o braco
    # `from_nsga` da investigacao levantou e nao pode responder (ele usava 2x orcamento).
    @{ N = 5; Min = 8; Nome = "hibrido split 0,25 - so o scalar_optimum"
       Args = $base + @("--algorithm", "hybrid", "--hybrid-split", "0.25", "--hybrid-carry", "scalar_optimum") }

    @{ N = 6; Min = 9; Nome = "hibrido split 0,50 - so o scalar_optimum"
       Args = $base + @("--algorithm", "hybrid", "--hybrid-split", "0.5", "--hybrid-carry", "scalar_optimum") }

    @{ N = 7; Min = 11; Nome = "hibrido split 0,75 - so o scalar_optimum"
       Args = $base + @("--algorithm", "hybrid", "--hybrid-split", "0.75", "--hybrid-carry", "scalar_optimum") }
)

$restantes = @($passos | Where-Object { $_.N -ge $From })
if ($restantes.Count -eq 0) { throw "-From $From nao deixa nenhum passo (max: $($passos.Count))." }

# ForEach-Object antes do Measure-Object: no PS 5.1 o -Property nao enxerga chave de
# hashtable (so propriedade .NET real), e -Property Min devolveria erro.
$total = ($restantes | ForEach-Object { $_.Min } | Measure-Object -Sum).Sum
$horas = [int][math]::Floor($total / 60)
$mins  = [int]($total % 60)
Write-Host ""
Write-Host "  SWEEP DO HIBRIDO - sementes 1000-1004, pop 120 x 60 geracoes" -ForegroundColor Cyan
Write-Host "  $($restantes.Count) passos, custo estimado ${horas}h$('{0:d2}' -f $mins)m"
Write-Host ""
foreach ($p in $restantes) {
    Write-Host ("    {0,2}. {1,-55} ~{2,3} min" -f $p.N, $p.Nome, $p.Min)
}
Write-Host ""
if ($WhatIf) { Write-Host "  (-WhatIf: nada foi executado)" -ForegroundColor Yellow; exit 0 }

$t0 = Get-Date
foreach ($p in $restantes) {
    Write-Host ""
    Write-Host "  === passo $($p.N)/$($passos.Count) - $($p.Nome)" -ForegroundColor Yellow
    $ti = Get-Date
    & $py $p.Args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  x passo $($p.N) FALHOU (exit $LASTEXITCODE)." -ForegroundColor Red
        Write-Host "    Os passos anteriores estao salvos. Retome com:" -ForegroundColor Red
        Write-Host "    .\scripts\run_hybrid_sweep.ps1 -From $($p.N)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    $dt = [math]::Round(((Get-Date) - $ti).TotalMinutes, 1)
    Write-Host "  ok passo $($p.N) em $dt min" -ForegroundColor Green
}

$dtTotal = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
Write-Host ""
Write-Host "  SWEEP COMPLETO em $dtTotal min" -ForegroundColor Cyan
Write-Host "  Artefatos em results/exploratory/. Leia com:" -ForegroundColor Cyan
Write-Host "    py -m src.experiments.hybrid_choice" -ForegroundColor Cyan
Write-Host ""
