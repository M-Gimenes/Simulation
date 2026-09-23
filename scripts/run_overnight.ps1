# run_overnight.ps1 - encadeia os sweeps e a bateria para rodar sozinho, a noite.
#
# ASCII puro, sem acentos, pela mesma razao do setup.ps1: o Windows PowerShell 5.1 le
# .ps1 como ANSI quando o arquivo nao tem BOM, e acento vira erro de parse.
#
# O QUE ELE FAZ, em ordem:
#   1. Declara ao Windows que ha trabalho em andamento (SetThreadExecutionState), o que
#      impede suspensao e hibernacao ENQUANTO ele roda e solta sozinho quando termina.
#      E o mecanismo certo: mexer no plano de energia global resolve a noite de hoje e
#      deixa a maquina sem hibernar para sempre, o que ninguem lembra de desfazer.
#   2. Roda os sweeps (run_sweeps.ps1) - ou, se ja estiverem rodando, espera terminarem.
#      Nao adianta so enfileirar: os dois competindo por CPU dobram o tempo dos dois e
#      aumentam o risco de estourar o limite de commit do Windows (WinError 1455, que ja
#      matou uma bateria no meio). Os sweeps vem ANTES porque os bracos exploratorios
#      tambem levam o carimbo do motor: uma mudanca de motor deixa os 16 obsoletos, e a
#      bateria nao os regera.
#   3. Roda a bateria, com UMA retomada automatica se um passo falhar.
#
# POR QUE UMA retomada e nao varias: WinError 1455 e pressao de memoria e costuma passar
# na segunda tentativa; um defeito de verdade repete, e ai insistir so queima a noite
# escondendo a causa. A retomada usa `-From N` do passo que falhou, entao nada ja feito e
# refeito. Os sweeps nao tem retomada automatica: se falharem, o log diz de onde retomar a
# mao e a bateria roda mesmo assim - ela e o que a tese cita.
#
# Uso:
#   .\scripts\run_overnight.ps1              # sweeps (ou espera os que ja rodam) e depois a bateria
#   .\scripts\run_overnight.ps1 -SkipSweeps  # vai direto para a bateria
#   .\scripts\run_overnight.ps1 -From 5      # retoma a bateria no passo 5 (sem sweeps)

param(
    [int]    $From = 1,
    [switch] $SkipSweeps
)

$ErrorActionPreference = "Continue"
# O script mora em scripts/; a raiz do projeto e o diretorio acima.
$raiz = Split-Path -Parent $PSScriptRoot
$log  = Join-Path $raiz "results\logs\overnight.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

function Escreve($msg) {
    $linha = "[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $msg
    Write-Host $linha
    Add-Content -Path $log -Value $linha -Encoding utf8
}

# -- 1. Segura a maquina acordada ---------------------------------------------------------
# ES_CONTINUOUS | ES_SYSTEM_REQUIRED: "ha trabalho, nao durma".
# Sem ES_DISPLAY_REQUIRED de proposito - o monitor pode desligar, nao atrapalha em nada.
#
# As constantes vao em DECIMAL e com cast explicito por um motivo que custou um teste: no
# PowerShell 5.1 o literal `0x80000000` e lido como Int32 e transborda para -2147483648,
# que nao converte para o `uint` da assinatura. A chamada falha, cai no catch, e o script
# seguiria a noite inteira ACHANDO que travou a suspensao sem ter travado.
$ES_CONTINUOUS       = [uint32]2147483648   # 0x80000000
$ES_SYSTEM_REQUIRED  = [uint32]1            # 0x00000001
$sig = @"
[DllImport("kernel32.dll", SetLastError = true)]
public static extern uint SetThreadExecutionState(uint esFlags);
"@
$power = $null
try {
    $power = Add-Type -MemberDefinition $sig -Name Power -Namespace Win32 -PassThru
    $anterior = $power::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED)
    if ($anterior -eq 0) { Escreve "AVISO: SetThreadExecutionState falhou; seguindo mesmo assim" }
    else                 { Escreve "maquina travada acordada enquanto este script rodar" }
} catch {
    Escreve "AVISO: nao consegui travar a suspensao ($($_.Exception.Message)); seguindo"
}

Escreve "=============================================================="
Escreve "INICIO - encadeamento sweeps -> bateria"

# -- 2. Sweeps ----------------------------------------------------------------------------
function Sweeps-Rodando {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
             Where-Object { $_.CommandLine -like "*src.experiments.multi_run*" }
    return ($procs | Measure-Object).Count -gt 0
}

# Retomar a bateria no meio implica que os sweeps ja rodaram.
if ($From -gt 1) { $SkipSweeps = $true }

if (-not $SkipSweeps) {
    if (Sweeps-Rodando) {
        Escreve "sweeps em andamento - esperando terminarem antes de comecar a bateria"
        $ocioso = 0
        while ($true) {
            Start-Sleep -Seconds 60
            if (Sweeps-Rodando) {
                $ocioso = 0
            } else {
                # Duas checagens seguidas sem processo: o multi_run e relancado a cada
                # braco, entao uma unica leitura vazia pode ser so a troca entre dois.
                $ocioso++
                if ($ocioso -ge 2) { break }
            }
        }
        Escreve "sweeps terminaram"
    } else {
        Escreve "rodando os sweeps (run_sweeps.ps1)"
        $LASTEXITCODE = 0
        # `*>&1` e nao `2>&1`: os scripts falam por Write-Host, que desde o PS 5.0 vai para
        # o stream de INFORMACAO (6) e nao para o de erro.
        & (Join-Path $PSScriptRoot "run_sweeps.ps1") *>&1 | ForEach-Object { Escreve "  | $_" }
        $codigoSweeps = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
        if ($codigoSweeps -ne 0) {
            Escreve "sweeps FALHARAM (exit $codigoSweeps) - seguindo para a bateria mesmo assim."
            Escreve "Retome os sweeps a mao com .\scripts\run_sweeps.ps1 -From N (o N esta nas linhas acima)."
        }

    }

    # Os bracos rodam nas sementes 1000-1004, entao o nome de todos leva `seed1000`.
    $bracos = @(Get-ChildItem (Join-Path $raiz "results\exploratory") -Filter "*seed1000*.json" -ErrorAction SilentlyContinue)
    Escreve "bracos exploratorios no disco: $($bracos.Count) (esperado 22)"
}

# -- 3. Bateria, com uma retomada ---------------------------------------------------------
$bateria = Join-Path $PSScriptRoot "run_battery.ps1"
Escreve "iniciando a bateria a partir do passo $From"
# O ponto de retomada sai das linhas "=== passo N/16" que a bateria escreve no log. Conta-se
# o log a partir daqui, senao as linhas "=== passo N/16" dos sweeps entrariam na busca.
$linhasAntes = @(Get-Content $log).Count
$LASTEXITCODE = 0
& $bateria -From $From *>&1 | ForEach-Object { Escreve "  | $_" }
$codigo = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }

if ($codigo -ne 0) {
    $ultimo = Get-Content $log | Select-Object -Skip $linhasAntes |
              Select-String -Pattern "=== passo (\d+)/" | Select-Object -Last 1
    $passo = if ($ultimo) { [int]$ultimo.Matches[0].Groups[1].Value } else { $From }
    Escreve "bateria FALHOU (exit $codigo) no passo $passo - UMA retomada automatica"
    $LASTEXITCODE = 0
    & $bateria -From $passo *>&1 | ForEach-Object { Escreve "  | $_" }
    $codigo = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    if ($codigo -ne 0) {
        Escreve "a retomada tambem falhou (exit $codigo). Parando - repetir de novo so"
        Escreve "esconderia a causa. Retome a mao com: .\scripts\run_battery.ps1 -From $passo"
    }
}

if ($codigo -eq 0) { Escreve "BATERIA COMPLETA - tudo certo" }

Escreve "FIM"
Escreve "=============================================================="

# Solta a trava: o proprio fim do processo ja soltaria, mas explicito e mais claro.
if ($power) { try { $power::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null } catch { } }
