# run_battery.ps1 - a bateria completa com n = 20 sementes.
#
# ASCII puro, sem acentos, pela mesma razao do setup.ps1: o Windows PowerShell 5.1 le
# .ps1 como ANSI quando o arquivo nao tem BOM, e acento vira erro de parse.
#
# OS SWEEPS NAO ESTAO AQUI: eles vivem em run_sweeps.ps1, em ORCAMENTO REDUZIDO (pop 120 x
# 60 geracoes, ~16% do custo). Experimento exploratorio quer ORDENACAO entre configuracoes,
# e ordenacao transfere de orcamento; numero citavel nao. Os artefatos deles vao para
# results/multi_run/exploratory/, fora dos caminhos que o compare_algorithms le.
#
# ORDEM ENTRE OS DOIS SCRIPTS: rode run_sweeps.ps1 ANTES. Implementar um braco de sweep
# mexe no motor (operators.py, fitness.py), e mexer no motor depois da bateria faria 8h de
# artefato nascerem carimbados como obsoletos. A bateria e sempre a ULTIMA coisa a rodar.
#
# Se um sweep futuro precisar ser comparado ponto a ponto com a FRONTEIRA, lembrar que
# ela e lambda-independente (nsga2.scalar_objective e a unica coisa que le os LAMBDA_*, e
# e reporting, nao busca): basta re-derivar o scalar_optimum de cada lambda a partir do
# front_objectives que esta bateria grava por semente. Nao precisa re-rodar o NSGA-II.
#
# Cada braco e uma INVOCACAO propria que salva seu artefato. E de proposito: o multi_run
# nao tem resume e a bateria de 2026-09-16 morreu no meio (WinError 1455). Se um passo
# falhar, os anteriores estao no disco e basta retomar dele.
#
# Uso:
#   .\run_battery.ps1                 # roda tudo, na ordem
#   .\run_battery.ps1 -From 3         # retoma a partir do passo 3
#   .\run_battery.ps1 -WhatIf         # so lista os passos e o custo

param(
    [int]    $From = 1,
    [switch] $WhatIf
)

$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Ambiente nao encontrado. Rode .\setup.ps1 primeiro." }
$env:PYTHONIOENCODING = "utf-8"

# Os `Min` sao os tempos MEDIDOS na execucao de 2026-09-18 (8 workers), arredondados
# para cima; os passos 6-11 levam segundos.
#
# Ordem deliberada: o que serve os DOIS experimentos vem primeiro, para que uma
# interrupcao no meio ainda deixe a bateria principal completa e citavel.
$passos = @(
    @{ N = 1; Min = 202; Nome = "NSGA-II, 20 sementes"
       Args = @("-m", "src.tools.multi_run", "--algorithm", "nsga2") }

    @{ N = 2; Min = 135; Nome = "AG escalar, 20 sementes"
       Args = @("-m", "src.tools.multi_run", "--algorithm", "ga") }

    @{ N = 3; Min = 1; Nome = "compare_algorithms (n=20) - checa proveniencia dos dois"
       Args = @("-m", "src.tools.compare_algorithms") }

    # Os individuais da seed 42 e as metricas post-hoc vem por ultimo: dependem do motor,
    # nao do sweep, e sao baratos perto dos bracos.
    @{ N = 4;  Min = 7;  Nome = "AG seed 42 (results.json)"
       Args = @("main.py", "--seed", "42") }

    @{ N = 5;  Min = 10; Nome = "NSGA-II seed 42 (nsga2_results.json + plots)"
       Args = @("main.py", "--algorithm", "nsga2", "--seed", "42") }

    @{ N = 6; Min = 1;  Nome = "external_validation - canonico"
       Args = @("-m", "src.tools.external_validation") }

    @{ N = 7; Min = 1;  Nome = "external_validation - AG escalar"
       Args = @("-m", "src.tools.external_validation", "--evolved") }

    @{ N = 8; Min = 1;  Nome = "external_validation - NSGA-II best_dominance"
       Args = @("-m", "src.tools.external_validation", "--nsga2", "best_dominance") }

    @{ N = 9; Min = 1;  Nome = "external_validation - NSGA-II knee_point"
       Args = @("-m", "src.tools.external_validation", "--nsga2", "knee_point") }

    @{ N = 10; Min = 1;  Nome = "sensitivity_analysis no evoluido (o canonico e saturado)"
       Args = @("-m", "src.tools.sensitivity_analysis", "--evolved") }

    @{ N = 11; Min = 1; Nome = "baselines (modelos nulos)"
       Args = @("-m", "src.tools.baselines", "--evolved") }
)

$restantes = @($passos | Where-Object { $_.N -ge $From })
if ($restantes.Count -eq 0) { throw "-From $From nao deixa nenhum passo (max: $($passos.Count))." }
# ForEach-Object antes do Measure-Object: no PS 5.1 o -Property nao enxerga chave de
# hashtable, so propriedade de objeto.
$total = ($restantes | ForEach-Object { $_.Min } | Measure-Object -Sum).Sum

Write-Host ""
Write-Host "  BATERIA COMPLETA - n = 20 sementes" -ForegroundColor Cyan
$horas = [int][math]::Floor($total / 60)
$mins  = [int]($total % 60)
Write-Host "  $($restantes.Count) passos, custo estimado ${horas}h$('{0:d2}' -f $mins)m"
Write-Host ""
foreach ($p in $restantes) {
    Write-Host ("    {0,2}. {1,-62} ~{2,4} min" -f $p.N, $p.Nome, $p.Min)
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
        Write-Host "      .\run_battery.ps1 -From $($p.N)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    $dt = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1)
    Write-Host "  ok passo $($p.N) em $dt min" -ForegroundColor Green
}

$dtTotal = [math]::Round(((Get-Date) - $inicio).TotalMinutes, 1)
Write-Host ""
Write-Host "  BATERIA COMPLETA em $dtTotal min" -ForegroundColor Green
Write-Host ""
Write-Host "  Confira a proveniencia de tudo com:"
Write-Host "      py -m src.tests.test_provenance"
Write-Host "  Os bracos do sweep devem aparecer como 'braco de experimento'; o resto,"
Write-Host "  como 'atual'. Qualquer 'obsoleto' significa que algo mudou no meio da"
Write-Host "  bateria, e aquele artefato precisa ser refeito."
Write-Host ""
