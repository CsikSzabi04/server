# PowerShell
<!-- tech: powershell -->
<!-- aliases: pwsh, ps1 -->

A PowerShell a Microsoft objektumorientált shellje és szkriptnyelve, amely .NET-re épül: a pipeline-ban nem szöveg, hanem típusos .NET objektumok áramlanak, így a szűrés, rendezés és formázás tulajdonságnevekkel történik, szövegparse-olás nélkül. Két fő változata a Windowsba épített Windows PowerShell 5.1 (`powershell.exe`, .NET Framework) és a keresztplatformos PowerShell 7+ (`pwsh`, .NET), ami Linuxon és macOS-en is fut. Fő területei a Windows- és felhőadminisztráció (Active Directory, Exchange, Azure, Microsoft 365), az automatizálás, a konfigurációkezelés (DSC) és a CI/CD szkriptek. Kevésbé ideális nagy teljesítményű adatfeldolgozásra (a pipeline overheadje jelentős) és ott, ahol a POSIX shell a természetes közeg.

## Objektumok a pipeline-ban
<!-- q: Miben különbözik a PowerShell pipeline a bash pipeline-tól? -->
<!-- tags: pipeline, objects, where-object, select-object, sort-object, group-object, measure-object -->

A PowerShell pipeline-ban .NET objektumok haladnak tulajdonságokkal és metódusokkal, ezért a `Where-Object`, `Sort-Object`, `Group-Object`, `Select-Object` és `Measure-Object` közvetlenül a mezőkön dolgozik, szövegvágás nélkül. Az objektumok elemenként, folyamatosan (streaming) haladnak, így a memóriahasználat kicsi marad. A formázás (`Format-Table`, `Format-List`) mindig a lánc legvégére kerüljön, mert utána már csak megjelenítési objektumok maradnak. Teljesítménybuktató: nagy adatnál a `Where-Object` lassú, ilyenkor a `.Where()` metódus, a `foreach` utasítás vagy a cmdlet saját `-Filter` paramétere sokkal gyorsabb.

```powershell
# Csak olvas: a temp mappa 30 napnál régebbi, nagy fájljainak elemzése
$limit = (Get-Date).AddDays(-30)

$report = Get-ChildItem -Path $env:TEMP -File -Recurse -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt $limit -and $_.Length -gt 1MB } |   # $_ = aktuális objektum
    Group-Object -Property Extension |                                       # tulajdonság szerint csoportosít
    ForEach-Object {
        # Számolt mezőket tartalmazó saját objektum csoportonként
        [pscustomobject]@{
            Extension = if ($_.Name) { $_.Name } else { '(nincs)' }
            Count     = $_.Count
            TotalMB   = [math]::Round(($_.Group | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
        }
    } |
    Sort-Object -Property TotalMB -Descending |
    Select-Object -First 10

# Formázás CSAK a végén
$report | Format-Table -AutoSize

# Gyors alternatívák nagy adatra: .Where() metódus és foreach utasítás
$procs = Get-Process
$heavy = $procs.Where({ $_.WorkingSet64 -gt 200MB }, 'First', 5)   # az első 5 találat
$totalMem = 0
foreach ($p in $procs) { $totalMem += $p.WorkingSet64 }              # nincs pipeline overhead
"{0} nagy folyamat, összesen {1:N0} MB" -f $heavy.Count, ($totalMem / 1MB)
```

## Cmdletek felfedezése: Get-Command, Get-Help, Get-Member
<!-- q: Hogyan találjam meg a megfelelő cmdletet és nézzem meg egy objektum tulajdonságait PowerShellben? -->
<!-- tags: cmdlets, get-command, get-help, get-member, verb-noun, discovery, aliases -->

A cmdletek Ige-Főnév (`Get-Process`, `Set-Item`) nevűek, a jóváhagyott igék listáját a `Get-Verb` mutatja, ezért a `Get-Command -Noun *service*` jellegű keresés gyorsan célhoz vezet. A `Get-Help -Examples` példákat ad, a `Get-Member` pedig megmutatja, milyen típusú objektum jön ki egy parancsból, és milyen tulajdonságai/metódusai vannak — ez a PowerShell-tanulás legfontosabb eszköze. Szkriptekben kerüld az aliasokat (`gci`, `%`, `?`), mert rontják az olvashatóságot, és platformonként eltérhetnek (Linuxon az `ls` nem alias).

```powershell
# Parancs keresése ige/főnév alapján
Get-Command -Verb Get -Noun *Service* | Select-Object -Property Name, Source

# Mely parancsok fogadnak el egy adott paramétert?
Get-Command -ParameterName ComputerName -CommandType Cmdlet | Select-Object -First 5 -ExpandProperty Name

# Súgó csak a példákkal (frissítés: Update-Help, rendszergazdaként)
Get-Help -Name Get-ChildItem -Examples

# Milyen objektumot ad a parancs? Tulajdonságok és metódusok
Get-Service | Get-Member -MemberType Property, Method | Select-Object -First 10

# Egy objektum MINDEN tulajdonsága értékekkel
Get-Process -Id $PID | Format-List -Property *

# Paraméterek részletei: kötelező-e, pipeline-ból jöhet-e
(Get-Command -Name Stop-Process).Parameters['Id'].Attributes |
    Where-Object { $_ -is [System.Management.Automation.ParameterAttribute] } |
    Select-Object -Property Mandatory, ValueFromPipeline, ValueFromPipelineByPropertyName

# Alias feloldása — szkriptben a teljes nevet írd!
Get-Alias -Name gci, '%', '?' | Select-Object -Property Name, Definition

# Jóváhagyott igék (saját függvény elnevezéséhez)
Get-Verb | Where-Object Group -EQ 'Lifecycle' | Select-Object -ExpandProperty Verb
```

## Advanced function: CmdletBinding, paraméter-validáció, -WhatIf
<!-- q: Hogyan írjak profi PowerShell függvényt paraméter-validációval és -WhatIf támogatással? -->
<!-- tags: advanced functions, cmdletbinding, param, validation, shouldprocess, whatif, confirm -->

A `[CmdletBinding()]` attribútum a függvényt „advanced function”-né teszi: megkapja a közös paramétereket (`-Verbose`, `-ErrorAction`, `-WhatIf` stb.), és a validációs attribútumok (`ValidateSet`, `ValidateRange`, `ValidateScript`, `ValidatePattern`, `Mandatory`) már a futás előtt kiszűrik a hibás bemenetet. A `SupportsShouldProcess` és a `$PSCmdlet.ShouldProcess()` hívás adja a `-WhatIf` (szárazfuttatás) és `-Confirm` támogatást, ami minden módosító művelethez kötelező illem. A `ConfirmImpact = 'High'` automatikusan megerősítést kér. Buktató: a `Write-Host` nem a pipeline-ba ír — adatot `Write-Output`-tal (vagy egyszerűen visszaadva), diagnosztikát `Write-Verbose`-zal adj.

```powershell
function Remove-OldLogFile {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
    [OutputType([System.IO.FileInfo])]
    param(
        [Parameter(Mandatory, Position = 0)]
        [ValidateScript({ Test-Path -Path $_ -PathType Container })]   # létező mappa kell
        [string]$Path,

        [ValidateRange(1, 3650)]
        [int]$OlderThanDays = 30,

        [ValidateSet('*.log', '*.tmp', '*.bak')]
        [string]$Filter = '*.log',

        [switch]$PassThru
    )

    $limit = (Get-Date).AddDays(-$OlderThanDays)
    Write-Verbose "Keresés: $Path, szűrő: $Filter, határ: $limit"

    Get-ChildItem -Path $Path -Filter $Filter -File | Where-Object LastWriteTime -LT $limit | ForEach-Object {
        # -WhatIf esetén a ShouldProcess $false-t ad, és csak kiírja, mit TENNE
        if ($PSCmdlet.ShouldProcess($_.FullName, 'Törlés')) {
            Remove-Item -LiteralPath $_.FullName
            if ($PassThru) { $_ }
        }
    }
}

# Biztonságos kipróbálás: saját temp mappa + -WhatIf (semmit nem töröl)
$demo = Join-Path -Path ([IO.Path]::GetTempPath()) -ChildPath "pbdemo_$([guid]::NewGuid().ToString('N'))"
New-Item -Path $demo -ItemType Directory | Out-Null
$old = New-Item -Path (Join-Path $demo 'regi.log') -ItemType File
$old.LastWriteTime = (Get-Date).AddDays(-90)

Remove-OldLogFile -Path $demo -OlderThanDays 60 -WhatIf -Verbose
# Remove-OldLogFile -Path $demo -Filter '*.exe'   # hiba: nem szerepel a ValidateSet-ben
```

## Pipeline-bemenet: begin, process, end
<!-- q: Hogyan fogadjon a saját PowerShell függvényem pipeline-ból bemenetet? -->
<!-- tags: pipeline input, valuefrompipeline, valuefrompipelinebypropertyname, begin process end -->

A `ValueFromPipeline` paraméter a teljes bejövő objektumot köti, a `ValueFromPipelineByPropertyName` pedig az azonos nevű (vagy `Alias`-szal megadott) tulajdonságot — így a függvény bármely parancs kimenetéhez illeszthető. A `begin` blokk egyszer fut az elején (inicializálás), a `process` minden elemre, az `end` a végén (összesítés). Ha nincs `process` blokk, a kód az `end`-ben fut, és csak az utolsó elemet látja — ez gyakori hiba. A paraméter tömb típusú is lehet, hogy közvetlen híváskor (`-Name a,b`) is működjön.

```powershell
function Measure-TextFile {
    [CmdletBinding()]
    param(
        # Get-ChildItem kimenetéből a FullName tulajdonság kötődik (alias: Path)
        [Parameter(Mandatory, ValueFromPipeline, ValueFromPipelineByPropertyName)]
        [Alias('FullName')]
        [string[]]$Path,

        [string]$Pattern = 'TODO'
    )

    begin {
        # Egyszer fut: számlálók inicializálása
        $fileCount = 0
        $hitCount = 0
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
    }

    process {
        # Minden pipeline-elemre lefut; a $Path itt egyetlen elem (vagy közvetlen híváskor tömb)
        foreach ($p in $Path) {
            $fileCount++
            $lines = [System.IO.File]::ReadAllLines($p)      # gyorsabb, mint Get-Content nagy fájlnál
            $hits = @($lines | Select-String -Pattern $Pattern -SimpleMatch)
            $hitCount += $hits.Count
            [pscustomobject]@{
                File  = Split-Path -Path $p -Leaf
                Lines = $lines.Count
                Hits  = $hits.Count
            }
        }
    }

    end {
        Write-Verbose ("{0} fájl, {1} találat, {2} ms" -f $fileCount, $hitCount, $sw.ElapsedMilliseconds)
    }
}

# Saját temp fájlok a demóhoz
$dir = New-Item -ItemType Directory -Path (Join-Path ([IO.Path]::GetTempPath()) "pb_$PID") -Force
Set-Content -Path (Join-Path $dir 'a.txt') -Value 'egy', 'TODO: teszt', 'kettő'
Set-Content -Path (Join-Path $dir 'b.txt') -Value 'TODO', 'TODO'

Get-ChildItem -Path $dir -Filter *.txt | Measure-TextFile -Verbose | Format-Table
Remove-Item -Path $dir -Recurse    # csak a saját demó mappánk
```

## Hibakezelés: terminating és non-terminating hibák
<!-- q: Hogyan kezeljem a hibákat PowerShellben try/catch-csel és ErrorAction-nel? -->
<!-- tags: error handling, try catch finally, erroraction, erroractionpreference, terminating errors, throw -->

A PowerShellben kétféle hiba van: a terminating (pl. `throw`, .NET kivétel) megszakítja a futást és `try/catch`-csel elkapható, a non-terminating (pl. egy nem létező fájl a `Get-Item` listájában) csak kiír egy hibát, és a parancs folytatódik — ezt a `catch` alapból NEM kapja el. Az `-ErrorAction Stop` (vagy szkriptszinten `$ErrorActionPreference = 'Stop'`) terminatingé teszi, így kezelhető. A `catch` típusonként szűrhető, a hibaobjektum a `$_` (ErrorRecord), az eredeti kivétel `$_.Exception`. Külső programoknál (`git`, `robocopy`) a `$LASTEXITCODE`-ot kell ellenőrizni, mert azok nem dobnak kivételt (PS 7.4+: `$PSNativeCommandUseErrorActionPreference`).

```powershell
Set-StrictMode -Version Latest          # nem deklarált változó, hibás property → hiba
$ErrorActionPreference = 'Stop'         # minden hiba terminating ebben a szkriptben

function Get-ConfigValue {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path, [Parameter(Mandatory)][string]$Key)

    try {
        $json = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        # StrictMode mellett a $json.$Key hiányzó kulcsnál hibát dobna — inkább ellenőrizzük
        $prop = $json.PSObject.Properties[$Key]
        if ($null -eq $prop) {
            # Saját, értelmes hiba dobása
            throw [System.Collections.Generic.KeyNotFoundException]::new("Hiányzó kulcs: '$Key' ($Path)")
        }
        return $prop.Value
    }
    catch [System.Management.Automation.ItemNotFoundException] {
        Write-Warning "A konfigurációs fájl nem létezik: $Path — alapértéket használok."
        return $null
    }
    catch [System.ArgumentException] {
        # A ConvertFrom-Json hibás JSON esetén ArgumentException-t dob
        throw "Érvénytelen JSON a(z) $Path fájlban: $($_.Exception.Message)"
    }
    finally {
        Write-Verbose "Get-ConfigValue lefutott: $Path"
    }
}

# Non-terminating hiba összegyűjtése ErrorVariable-lel, a futás folytatódik
$items = Get-Item -Path $env:TEMP, 'C:\nincs\ilyen\mappa' -ErrorAction SilentlyContinue -ErrorVariable notFound
"Talált: $(@($items).Count), hibák: $($notFound.Count)"

# Külső program: az exit kódot kell nézni
$null = & cmd.exe /c 'exit 3'
if ($LASTEXITCODE -ne 0) { Write-Warning "A külső parancs hibakóddal tért vissza: $LASTEXITCODE" }

$cfg = Join-Path ([IO.Path]::GetTempPath()) "pb_cfg_$PID.json"
'{ "Port": 8080 }' | Set-Content -LiteralPath $cfg
try   { "Port: $(Get-ConfigValue -Path $cfg -Key Port)"; Get-ConfigValue -Path $cfg -Key Host }
catch { "Elkapva: $($_.Exception.GetType().Name) — $($_.Exception.Message)" }
finally { Remove-Item -LiteralPath $cfg }
```

## Hashtable, PSCustomObject és splatting
<!-- q: Hogyan használjam a hashtable-t, a PSCustomObject-et és a splattinget PowerShellben? -->
<!-- tags: hashtable, pscustomobject, splatting, ordered, string formatting, here-string -->

A `@{}` hashtable kulcs-érték tár (alapból rendezetlen, `[ordered]@{}` megtartja a sorrendet), a `[pscustomobject]@{}` pedig valódi objektumot hoz létre, ami szépen formázódik, exportálható CSV-be/JSON-ba és a pipeline-ban tulajdonságként szűrhető. A splatting (`@params`) a paramétereket hashtable-ből adja át, így a hosszú parancssorok olvashatók, és feltételesen bővíthetők. Stringekhez a `"..$var.."` interpoláció, a `$()` subexpression és a `-f` formázó operátor való; a `'...'` nem interpolál. Buktató: a `"$obj.Prop"` csak `$obj`-ot helyettesíti — tulajdonsághoz `"$($obj.Prop)"` kell.

```powershell
# Rendezett hashtable — a kulcsok sorrendje megmarad
$config = [ordered]@{
    Server   = 'db01.example.local'
    Port     = 5432
    Timeout  = 30
    Features = @('cache', 'audit')
}
$config['Port'] = 5433                 # módosítás
$config.Add('Retries', 3)              # új kulcs (már létezőnél hibát dob)

# Splatting: paraméterek hashtable-ből, feltételes bővítéssel
$params = @{
    Path        = $env:TEMP
    File        = $true
    ErrorAction = 'SilentlyContinue'
}
if ($config.Timeout -gt 10) { $params['Filter'] = '*.log' }
$logs = Get-ChildItem @params           # @ és NEM $ a splattinghez

# PSCustomObject tömb: típusos rekordok listája
$servers = foreach ($i in 1..3) {
    [pscustomobject]@{
        Name   = 'web{0:D2}' -f $i     # web01, web02...
        Cpu    = Get-Random -Minimum 5 -Maximum 95
        Online = ($i % 2 -eq 1)
    }
}
$servers | Where-Object Online | Sort-Object Cpu -Descending | Format-Table

# Számolt tulajdonság a Select-Object-ben
$servers | Select-Object Name, @{ Name = 'Status'; Expression = { if ($_.Cpu -gt 80) { 'TERHELT' } else { 'OK' } } }

# Stringek: interpoláció, subexpression, -f formázás, here-string
$first = $servers[0]
"Első: $($first.Name), CPU: $($first.Cpu)%"            # $() kell a tulajdonsághoz
'Szó szerint: $first.Name'                             # aposztróf: nincs interpoláció
'{0,-8}|{1,5:N1}' -f 'kerek', 3.14159                  # igazítás és tizedesek
$summary = @"
Szerver: $($config.Server):$($config.Port)
Logfájlok: $(@($logs).Count)
"@
$summary
```

## Fájlok és adatformátumok: CSV, JSON, XML
<!-- q: Hogyan dolgozzak fel CSV, JSON és XML fájlokat PowerShellben? -->
<!-- tags: csv, json, xml, import-csv, export-csv, convertto-json, convertfrom-json, encoding -->

Az `Import-Csv` minden sorból objektumot készít (a mezők stringek, ezért számoláshoz kasztolni kell), az `Export-Csv` objektumokat ír ki; a `ConvertTo-Json`/`ConvertFrom-Json` a REST API-k és konfigok alapja, az `[xml]` típusgyorsító pedig XML-t pontozott navigációval tesz elérhetővé, XPath-szal (`Select-Xml`) kiegészítve. Buktatók: a `ConvertTo-Json` alapból csak 2 szint mélységig szerializál (`-Depth`), Windows PowerShell 5.1-ben az `Export-Csv` ASCII/UTF-16 kódolást használhat és típusinformációs sort ír (`-NoTypeInformation`, `-Encoding UTF8`), a magyar Excel pedig pontosvesszős CSV-t vár (`-Delimiter ';'`).

```powershell
$work = Join-Path ([IO.Path]::GetTempPath()) "pb_data_$PID"
New-Item -ItemType Directory -Path $work -Force | Out-Null

# Bemeneti CSV előállítása (demóadat)
@'
Datum;Termek;Mennyiseg;Egysegar
2026-11-01;Laptop;2;450000
2026-11-01;Eger;10;4500
2026-11-02;Laptop;1;440000
'@ | Set-Content -Path "$work\sales.csv" -Encoding UTF8

# CSV → objektumok; a mezők stringek, ezért kasztolunk
$sales = Import-Csv -Path "$work\sales.csv" -Delimiter ';' | ForEach-Object {
    [pscustomobject]@{
        Datum  = [datetime]::ParseExact($_.Datum, 'yyyy-MM-dd', $null)
        Termek = $_.Termek
        Ertek  = [int]$_.Mennyiseg * [decimal]$_.Egysegar
    }
}

# Összesítés termékenként → CSV (magyar Excelhez pontosvessző)
$summary = $sales | Group-Object Termek | ForEach-Object {
    [pscustomobject]@{ Termek = $_.Name; Osszesen = ($_.Group | Measure-Object Ertek -Sum).Sum }
}
$summary | Export-Csv -Path "$work\summary.csv" -Delimiter ';' -NoTypeInformation -Encoding UTF8

# JSON: -Depth nélkül a mélyebb szintek stringgé laposodnának!
$doc = @{ generated = (Get-Date).ToString('o'); items = $summary; meta = @{ source = @{ file = 'sales.csv' } } }
$doc | ConvertTo-Json -Depth 5 | Set-Content -Path "$work\summary.json" -Encoding UTF8
$back = Get-Content -Path "$work\summary.json" -Raw | ConvertFrom-Json
"JSON-ból visszaolvasva: $($back.items.Count) tétel, forrás: $($back.meta.source.file)"

# XML: típusgyorsító + XPath
[xml]$xml = '<config><app name="demo"><setting key="mode" value="test"/><setting key="level" value="3"/></app></config>'
$xml.config.app.name                                                  # demo
(Select-Xml -Xml $xml -XPath "//setting[@key='level']").Node.value    # 3

Remove-Item -Path $work -Recurse      # saját temp mappánk takarítása
```

## Modulok készítése
<!-- q: Hogyan készítsek újrahasznosítható PowerShell modult manifesttel? -->
<!-- tags: modules, psm1, psd1, module manifest, export-modulemember, import-module, psgallery -->

A modul egy `.psm1` szkriptfájl (függvényekkel) és opcionálisan egy `.psd1` manifest (verzió, szerző, függőségek, exportált parancsok), amit a `$env:PSModulePath` valamelyik mappájába téve az `Import-Module` — vagy automatikus betöltés — elérhetővé tesz. Csak a nyilvános függvényeket exportáld (`Export-ModuleMember` és a manifest `FunctionsToExport` mezője), a segédfüggvények maradjanak privátak; a `FunctionsToExport = '*'` lassítja az automatikus betöltést. A megosztás a PowerShell Gallery-n vagy belső NuGet tárolón keresztül megy (`Publish-Module`/`Publish-PSResource`). Fejlesztés közben az `Import-Module -Force` tölti újra a módosított modult.

```powershell
# Modul létrehozása egy temp mappában: PbTools\PbTools.psm1 + PbTools.psd1
$root = Join-Path ([IO.Path]::GetTempPath()) "pb_modules_$PID"
$modDir = New-Item -ItemType Directory -Path (Join-Path $root 'PbTools') -Force

@'
# --- Privát segédfüggvény: NEM exportáljuk ---
function ConvertTo-SafeName([string]$Text) {
    ($Text -replace '[^\w\-]', '_').ToLowerInvariant()
}

# --- Nyilvános függvények ---
function Get-PbSlug {
    [CmdletBinding()]
    param([Parameter(Mandatory, ValueFromPipeline)][string]$Text)
    process { ConvertTo-SafeName -Text $Text }
}

function Get-PbChecksum {
    [CmdletBinding()]
    param([Parameter(Mandatory)][string]$Path, [ValidateSet('SHA256', 'SHA512')][string]$Algorithm = 'SHA256')
    (Get-FileHash -Path $Path -Algorithm $Algorithm).Hash.ToLowerInvariant()
}

Export-ModuleMember -Function Get-PbSlug, Get-PbChecksum
'@ | Set-Content -Path (Join-Path $modDir 'PbTools.psm1') -Encoding UTF8

# Manifest generálása: explicit exportlista a gyors automatikus betöltéshez
$manifest = @{
    Path              = Join-Path $modDir 'PbTools.psd1'
    RootModule        = 'PbTools.psm1'
    ModuleVersion     = '1.0.0'
    Author            = 'Példa Szerző'
    Description       = 'Demó segédfüggvények'
    PowerShellVersion = '5.1'
    FunctionsToExport = @('Get-PbSlug', 'Get-PbChecksum')
    CmdletsToExport   = @()
    AliasesToExport   = @()
}
New-ModuleManifest @manifest

Test-ModuleManifest -Path $manifest.Path | Select-Object Name, Version, ExportedFunctions
Import-Module -Name $manifest.Path -Force                    # fejlesztés közben -Force
'Árvíz Tűrő 2026!' | Get-PbSlug
Get-Command -Module PbTools                                  # a privát függvény nem látszik

Remove-Module PbTools
Remove-Item -Path $root -Recurse                             # saját temp mappa
```

## Registry kezelése
<!-- q: Hogyan olvassam és írjam a Windows registryt PowerShellből? -->
<!-- tags: registry, hkcu, hklm, get-itemproperty, new-itemproperty, psdrive, windows -->

A registry PSDrive-ként érhető el (`HKLM:`, `HKCU:`), így ugyanazokkal a parancsokkal navigálsz, mint a fájlrendszerben: a kulcsok elemek (`Get-ChildItem`, `New-Item`), az értékek tulajdonságok (`Get-ItemProperty`, `New-ItemProperty`, `Set-ItemProperty`). A `HKLM` írásához rendszergazdai jog kell, a `HKCU` a felhasználóé. Buktatók: 64 bites rendszeren a 32 bites alkalmazások a `WOW6432Node` ágat látják, a `-PropertyType` (DWord, String, MultiString, ExpandString) megadása fontos, és módosítás előtt érdemes exportálni a kulcsot (`reg export`) — írásnál mindig adj `-WhatIf` lehetőséget.

```powershell
# OLVASÁS: telepített programok listája (64 és 32 bites ág)
$uninstallPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*'
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
Get-ItemProperty -Path $uninstallPaths -ErrorAction SilentlyContinue |
    Where-Object DisplayName |
    Select-Object DisplayName, DisplayVersion, Publisher |
    Sort-Object DisplayName |
    Select-Object -First 10

# Egyetlen érték közvetlen olvasása (hiányzó értéknél hibát dob)
$build = Get-ItemPropertyValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -Name CurrentBuild
"Windows build: $build"

# ÍRÁS: csak a saját, dedikált demó kulcsunkba a HKCU alatt
function Set-DemoSetting {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][object]$Value,
        [ValidateSet('String', 'DWord', 'QWord', 'MultiString', 'ExpandString')]
        [string]$Type = 'String'
    )
    $key = 'HKCU:\Software\ProgramingBrainDemo'
    if (-not (Test-Path $key) -and $PSCmdlet.ShouldProcess($key, 'Kulcs létrehozása')) {
        New-Item -Path $key | Out-Null
    }
    if ($PSCmdlet.ShouldProcess("$key\$Name", "Érték beállítása: $Value ($Type)")) {
        New-ItemProperty -Path $key -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
    }
}

Set-DemoSetting -Name 'RetryCount' -Value 3 -Type DWord -WhatIf   # csak kiírja, mit tenne
# Valódi futtatás után takarítás:
# Remove-Item -Path 'HKCU:\Software\ProgramingBrainDemo' -Recurse -WhatIf
```

## WMI és CIM lekérdezések
<!-- q: Hogyan kérdezzem le a hardver- és rendszeradatokat CIM/WMI-vel PowerShellben? -->
<!-- tags: cim, wmi, get-ciminstance, cimsession, win32_operatingsystem, system inventory -->

A WMI a Windows rendszerinformációs és -kezelő interfésze (operációs rendszer, lemezek, szolgáltatások, BIOS, folyamatok); a modern elérése a `Get-CimInstance` (WS-Man/DCOM), a régi `Get-WmiObject` PowerShell 7-ben már nem létezik. A `-Filter` paraméterrel (WQL szintaxis) a szűrés a forrásoldalon történik, ami sokkal gyorsabb a `Where-Object`-nél, távoli gépeknél pedig a `New-CimSession` egyetlen kapcsolatot használ több lekérdezéshez. Módosító metódusokat (`Invoke-CimMethod`, pl. folyamatindítás, újraindítás) csak `-WhatIf`-fel próbálj ki.

```powershell
# Gépleltár egyetlen objektumban (csak olvasás)
function Get-MachineInventory {
    [CmdletBinding()]
    param([string[]]$ComputerName = $env:COMPUTERNAME)

    foreach ($computer in $ComputerName) {
        # Egy CIM session több lekérdezéshez — távoli gépnél jelentős gyorsítás
        $session = New-CimSession -ComputerName $computer -ErrorAction Stop
        try {
            $os   = Get-CimInstance -CimSession $session -ClassName Win32_OperatingSystem
            $cs   = Get-CimInstance -CimSession $session -ClassName Win32_ComputerSystem
            $cpu  = Get-CimInstance -CimSession $session -ClassName Win32_Processor | Select-Object -First 1
            # WQL szűrés a forrásnál: csak helyi lemezek (DriveType=3)
            $disks = Get-CimInstance -CimSession $session -ClassName Win32_LogicalDisk -Filter 'DriveType = 3'

            [pscustomobject]@{
                Computer   = $computer
                OS         = $os.Caption
                Build      = $os.BuildNumber
                UptimeDays = [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalDays, 1)
                CPU        = $cpu.Name.Trim()
                RamGB      = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
                Disks      = ($disks | ForEach-Object {
                    '{0} {1:N0}/{2:N0} GB szabad' -f $_.DeviceID, ($_.FreeSpace / 1GB), ($_.Size / 1GB)
                }) -join '; '
            }
        }
        finally {
            Remove-CimSession -CimSession $session
        }
    }
}

Get-MachineInventory | Format-List

# Leállt, automatikus indítású szolgáltatások — szűrés a WMI oldalon
Get-CimInstance -ClassName Win32_Service -Filter "StartMode = 'Auto' AND State <> 'Running'" |
    Select-Object Name, DisplayName, State

# Elérhető osztályok felderítése
Get-CimClass -ClassName Win32_*Network* | Select-Object -First 5 CimClassName
```

## Remoting: Invoke-Command és PSSession
<!-- q: Hogyan futtassak parancsokat távoli gépeken PowerShell remotinggal? -->
<!-- tags: remoting, invoke-command, pssession, winrm, ssh, using scope, fan-out -->

A PowerShell remoting WinRM-en (Windows) vagy PowerShell 7-ben SSH-n keresztül futtat parancsokat távoli gépeken; az `Invoke-Command -ComputerName a,b,c` párhuzamosan (fan-out) dolgozik, az eredmény objektumai `PSComputerName` tulajdonságot kapnak. Több egymás utáni híváshoz a `New-PSSession` tartós kapcsolatot ad, az `Enter-PSSession` interaktív. A helyi változókat a távoli szkriptblokkban `$using:` előtaggal éred el. Buktatók: a visszajövő objektumok deszerializáltak (metódusaik nincsenek), a „második ugrás” (távoli gépről harmadikra) alapból nem engedélyezett, és jelszót soha ne írj a szkriptbe — `Get-Credential` vagy SecretManagement kell.

```powershell
function Get-RemoteDiskReport {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string[]]$ComputerName,
        [ValidateRange(1, 99)][int]$WarnPercent = 15,
        [pscredential]$Credential      # interaktívan: Get-Credential — SOHA ne tárold szkriptben
    )

    $params = @{
        ComputerName  = $ComputerName
        ThrottleLimit = 16              # legfeljebb 16 gép párhuzamosan
        ErrorAction   = 'SilentlyContinue'
        ErrorVariable = 'remoteErrors'
    }
    if ($Credential) { $params.Credential = $Credential }

    # A szkriptblokk a TÁVOLI gépen fut; csak olvas
    $results = Invoke-Command @params -ScriptBlock {
        Get-CimInstance -ClassName Win32_LogicalDisk -Filter 'DriveType = 3' | ForEach-Object {
            $free = [math]::Round($_.FreeSpace / $_.Size * 100, 1)
            [pscustomobject]@{
                Drive       = $_.DeviceID
                FreePercent = $free
                Warning     = $free -lt $using:WarnPercent   # helyi változó a $using: előtaggal
            }
        }
    }

    foreach ($err in $remoteErrors) { Write-Warning "Nem elérhető: $($err.TargetObject)" }
    $results | Select-Object PSComputerName, Drive, FreePercent, Warning
}

# Tartós session több híváshoz (a végén mindig zárd le)
function Invoke-WithSession {
    param([string]$ComputerName)
    $s = New-PSSession -ComputerName $ComputerName
    try {
        Invoke-Command -Session $s -ScriptBlock { $global:cache = Get-Process }   # állapot megmarad
        Invoke-Command -Session $s -ScriptBlock { $global:cache.Count }
    }
    finally { Remove-PSSession -Session $s }
}

# Példa (WinRM-et igényel; csak olvasó lekérdezés):
# Get-RemoteDiskReport -ComputerName 'srv01', 'srv02' -WarnPercent 20 | Format-Table
# PowerShell 7 SSH-val: Invoke-Command -HostName 'linux01' -UserName 'admin' -ScriptBlock { uname -a }
```

## Jobok, runspace-ek és ForEach-Object -Parallel
<!-- q: Hogyan futtassak párhuzamosan feladatokat PowerShellben? -->
<!-- tags: jobs, start-job, threadjob, runspaces, foreach-object parallel, concurrency, throttlelimit -->

A `Start-Job` külön folyamatban futtat (erős izoláció, de lassú indulás és deszerializált eredmények), a `Start-ThreadJob` ugyanabban a folyamatban, külön runspace-ben (sokkal könnyebb), a PowerShell 7 `ForEach-Object -Parallel` pedig a legegyszerűbb párhuzamos ciklus `-ThrottleLimit`-tel. Mindegyiknél külön a hatókör: a külső változókat `$using:`-gal kell átadni, és a megosztott gyűjteménynek szálbiztosnak kell lennie (`ConcurrentDictionary`/`ConcurrentBag`). I/O-kötött munkánál (HTTP, ping) nagy a nyereség, CPU-kötött apró feladatnál a runspace indítási költsége elviheti az előnyt. A jobokat mindig gyűjtsd be (`Receive-Job`) és takarítsd el (`Remove-Job`).

```powershell
# 1) Háttérjob külön folyamatban (Windows PowerShell 5.1-ben is működik)
$job = Start-Job -Name 'HashJob' -ScriptBlock {
    param($Folder)
    Get-ChildItem -Path $Folder -File -ErrorAction SilentlyContinue |
        Select-Object -First 20 |
        Get-FileHash -Algorithm SHA256 |
        Select-Object Path, Hash
} -ArgumentList $env:TEMP

# Közben a fő szkript dolgozhat...
Wait-Job -Job $job -Timeout 60 | Out-Null
$hashes = Receive-Job -Job $job
Remove-Job -Job $job                      # takarítás
"Hash-elt fájlok: $(@($hashes).Count)"

# 2) PowerShell 7: ForEach-Object -Parallel szálbiztos gyűjtéssel
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $results = [System.Collections.Concurrent.ConcurrentDictionary[string, double]]::new()
    $hosts = 'example.com', 'example.org', 'example.net'

    $hosts | ForEach-Object -ThrottleLimit 3 -Parallel {
        $dict = $using:results                 # külső változó csak $using:-gal
        $sw = [Diagnostics.Stopwatch]::StartNew()
        try {
            $null = [System.Net.Dns]::GetHostAddresses($_)
            $dict[$_] = $sw.Elapsed.TotalMilliseconds
        }
        catch { $dict[$_] = -1 }
    }
    $results.GetEnumerator() | Sort-Object Value | Format-Table Key, Value
}

# 3) Runspace pool: finomhangolt, nagy számú rövid feladatra (5.1-ben is)
$pool = [runspacefactory]::CreateRunspacePool(1, 4)
$pool.Open()
$tasks = foreach ($n in 1..8) {
    $ps = [powershell]::Create().AddScript({ param($x) Start-Sleep -Milliseconds 200; $x * $x }).AddArgument($n)
    $ps.RunspacePool = $pool
    [pscustomobject]@{ Shell = $ps; Handle = $ps.BeginInvoke() }
}
$squares = foreach ($t in $tasks) { $t.Shell.EndInvoke($t.Handle); $t.Shell.Dispose() }
$pool.Close(); $pool.Dispose()
"Négyzetek: $($squares -join ', ')"
```

## REST API hívások: Invoke-RestMethod
<!-- q: Hogyan hívjak REST API-t PowerShellből hitelesítéssel, lapozással és újrapróbálással? -->
<!-- tags: rest api, invoke-restmethod, invoke-webrequest, json, authentication, pagination, retry -->

Az `Invoke-RestMethod` a JSON/XML választ automatikusan objektummá alakítja, így a mezők közvetlenül elérhetők; az `Invoke-WebRequest` a nyers választ adja (státuszkód, fejlécek). Bodyt hashtable-ből `ConvertTo-Json -Depth`-del küldj, `-ContentType 'application/json'` mellett. A tokent környezeti változóból vagy secret store-ból olvasd, soha ne írd a szkriptbe. PowerShell 7-ben van beépített újrapróbálás (`-MaximumRetryCount`, `-RetryIntervalSec`) és `-StatusCodeVariable`; 5.1-ben a TLS 1.2-t néha külön be kell kapcsolni, és a hibás státuszkód kivételt dob, amit `try/catch`-csel kezelj.

```powershell
function Invoke-ApiRequest {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][uri]$Uri,
        [ValidateSet('GET', 'POST', 'PUT', 'DELETE')][string]$Method = 'GET',
        [hashtable]$Body,
        [int]$MaxRetries = 3
    )

    # Token környezeti változóból — soha ne égesd a kódba
    $headers = @{ Accept = 'application/json' }
    if ($env:DEMO_API_TOKEN) { $headers.Authorization = "Bearer $env:DEMO_API_TOKEN" }

    $params = @{ Uri = $Uri; Method = $Method; Headers = $headers; TimeoutSec = 30 }
    if ($Body) {
        $params.Body = $Body | ConvertTo-Json -Depth 10
        $params.ContentType = 'application/json; charset=utf-8'
    }

    for ($attempt = 1; $attempt -le $MaxRetries; $attempt++) {
        try {
            return Invoke-RestMethod @params
        }
        catch {
            $status = $_.Exception.Response.StatusCode.value__
            # 4xx (kivéve 429) nem javul újrapróbálással
            if ($status -and $status -lt 500 -and $status -ne 429) { throw }
            if ($attempt -eq $MaxRetries) { throw }
            $delay = [math]::Pow(2, $attempt)            # exponenciális várakozás: 2, 4, 8 s
            Write-Warning "Hiba ($status), újrapróbálás $delay s múlva ($attempt/$MaxRetries)"
            Start-Sleep -Seconds $delay
        }
    }
}

# Lapozás: amíg van következő oldal (nyilvános teszt API, csak olvasás)
function Get-AllPages {
    param([string]$BaseUri, [int]$PageSize = 10, [int]$MaxPages = 3)
    $page = 1
    do {
        $items = @(Invoke-ApiRequest -Uri "$($BaseUri)?_page=$page&_limit=$PageSize")
        $items                                           # kiadjuk a pipeline-ba
        $page++
    } while ($items.Count -eq $PageSize -and $page -le $MaxPages)
}

# Get-AllPages -BaseUri 'https://jsonplaceholder.typicode.com/posts' | Select-Object id, title -First 5
# Invoke-ApiRequest -Uri 'https://jsonplaceholder.typicode.com/posts' -Method POST -Body @{ title = 'teszt'; userId = 1 }
```

## Ütemezett feladatok (Scheduled Tasks)
<!-- q: Hogyan hozzak létre ütemezett feladatot PowerShellből? -->
<!-- tags: scheduled tasks, register-scheduledtask, task scheduler, trigger, automation, windows -->

A `ScheduledTasks` modul (`New-ScheduledTaskAction`, `New-ScheduledTaskTrigger`, `New-ScheduledTaskPrincipal`, `Register-ScheduledTask`) objektumokból rakja össze a Feladatütemező bejegyzését, így verziókezelhető és ismételhető. A futtatandó szkriptet `-NoProfile -ExecutionPolicy Bypass -File` paraméterekkel indítsd, abszolút útvonallal, és naplózz fájlba, mert ablak nem lesz. Buktatók: a `SYSTEM` fiók nem lát hálózati meghajtókat, a „csak bejelentkezve fut” beállítás meglepetést okozhat, és a régi feladatot regisztrálás előtt ellenőrizd (`Get-ScheduledTask`), különben `-Force` felülírja. Telepítő szkriptben adj szárazfuttatást (`-WhatIf`).

```powershell
function Install-CleanupTask {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][ValidateScript({ Test-Path $_ -PathType Leaf })][string]$ScriptPath,
        [string]$TaskName = 'PB-NightlyCleanup',
        [datetime]$At = '02:30'
    )

    # Mit futtasson: pwsh/powershell abszolút útvonallal, profil nélkül
    $exe = (Get-Command pwsh, powershell -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    $action = New-ScheduledTaskAction -Execute $exe `
        -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$ScriptPath`""

    # Mikor: naponta, kis véletlen késleltetéssel (ne induljon minden gép egyszerre)
    $trigger = New-ScheduledTaskTrigger -Daily -At $At -RandomDelay (New-TimeSpan -Minutes 15)

    # Kinek a nevében: az aktuális felhasználó, bejelentkezés nélkül is (S4U, jelszó tárolása nélkül)
    $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited

    # Beállítások: időkorlát, akkumulátoron is fusson, kihagyott futás pótlása
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
        -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Write-Warning "A(z) '$TaskName' feladat már létezik — felül fogjuk írni."
    }

    if ($PSCmdlet.ShouldProcess($TaskName, "Ütemezett feladat regisztrálása ($exe, naponta $($At.ToString('HH:mm')))")) {
        Register-ScheduledTask -TaskName $TaskName -TaskPath '\ProgramingBrain\' -Action $action `
            -Trigger $trigger -Principal $principal -Settings $settings `
            -Description 'Éjszakai takarítás (demó)' -Force
    }
}

# Szárazfuttatás: semmit nem regisztrál, csak kiírja, mit tenne
$demoScript = Join-Path ([IO.Path]::GetTempPath()) 'pb_cleanup_demo.ps1'
Set-Content -Path $demoScript -Value "Add-Content -Path `"$env:TEMP\pb_cleanup.log`" -Value (Get-Date)"
Install-CleanupTask -ScriptPath $demoScript -WhatIf

# Állapot lekérdezése / eltávolítás (szintén -WhatIf-fel kipróbálható):
# Get-ScheduledTask -TaskPath '\ProgramingBrain\' | Get-ScheduledTaskInfo
# Unregister-ScheduledTask -TaskName 'PB-NightlyCleanup' -Confirm:$false -WhatIf
```

## Desired State Configuration (DSC) alapok
<!-- q: Mi a PowerShell DSC és hogyan írjak deklaratív konfigurációt? -->
<!-- tags: dsc, desired state configuration, configuration, mof, idempotent, infrastructure as code -->

A DSC deklaratív konfigurációkezelés: nem lépéseket írsz le, hanem a kívánt állapotot (ez a mappa létezzen, ez a szolgáltatás fusson, ez a registry-érték legyen beállítva), és a Local Configuration Manager (LCM) gondoskodik róla, hogy a gép abba az állapotba kerüljön — idempotensen, újrafuttatva is biztonságosan. A `Configuration` blokk lefordítva gépenként egy `.mof` fájlt ad, amit a `Start-DscConfiguration` alkalmaz, a `Test-DscConfiguration` pedig az eltérést (drift) ellenőrzi. A klasszikus DSC Windows PowerShell 5.1-hez kötött; az újabb irány a DSC v3 és az Azure Machine Configuration. Alkalmazás előtt mindig nézd át a MOF-ot, és teszt gépen próbáld ki.

```powershell
# Windows PowerShell 5.1 — a konfiguráció fordítása csak MOF fájlt készít, a gépet NEM módosítja
Configuration WebServerBaseline {
    param(
        [string[]]$NodeName = 'localhost',
        [string]$SiteRoot = 'C:\inetpub\pbdemo'
    )

    Import-DscResource -ModuleName PSDesiredStateConfiguration

    Node $NodeName {
        # Windows-szerepkör telepítve legyen
        WindowsFeature IIS {
            Ensure = 'Present'
            Name   = 'Web-Server'
        }

        # Mappa létezzen (a függőség miatt csak az IIS után)
        File SiteFolder {
            Ensure          = 'Present'
            Type            = 'Directory'
            DestinationPath = $SiteRoot
            DependsOn       = '[WindowsFeature]IIS'
        }

        # Alapértelmezett oldal tartalma
        File IndexPage {
            Ensure          = 'Present'
            DestinationPath = Join-Path $SiteRoot 'index.html'
            Contents        = '<h1>DSC-vel konfigurálva</h1>'
            DependsOn       = '[File]SiteFolder'
        }

        # Szolgáltatás fusson és automatikusan induljon
        Service W3SVC {
            Name        = 'W3SVC'
            State       = 'Running'
            StartupType = 'Automatic'
            DependsOn   = '[WindowsFeature]IIS'
        }

        # Registry-érték (pl. biztonsági beállítás)
        Registry DisableServerHeader {
            Ensure    = 'Present'
            Key       = 'HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\HTTP\Parameters'
            ValueName = 'DisableServerHeader'
            ValueData = '1'
            ValueType = 'Dword'
        }
    }
}

# Fordítás MOF-ra egy temp mappába (biztonságos, nem változtat a rendszeren)
$out = Join-Path ([IO.Path]::GetTempPath()) 'pb_dsc'
WebServerBaseline -NodeName 'localhost' -OutputPath $out
Get-ChildItem -Path $out -Filter *.mof

# Alkalmazás / ellenőrzés (rendszergazdaként, TESZT gépen!):
# Start-DscConfiguration -Path $out -Wait -Verbose -WhatIf
# Test-DscConfiguration -Detailed
```

## Tesztelés Pesterrel
<!-- q: Hogyan írjak unit teszteket PowerShell függvényekhez Pesterrel? -->
<!-- tags: pester, unit testing, mock, describe, it, should, testdrive, ci -->

A Pester a PowerShell szabványos tesztkeretrendszere: `Describe`/`Context`/`It` blokkokkal szervezed a teszteket, a `Should` állításokkal ellenőrzöl (`-Be`, `-BeExactly`, `-Throw`, `-HaveCount`), a `Mock` pedig lecseréli a külső függőségeket (fájlrendszer, REST hívás, `Get-Date`), és ellenőrizhető, hányszor hívták (`Should -Invoke`). A `$TestDrive` egy tesztenként takarított ideiglenes mappa, így a fájlműveletek biztonságosan tesztelhetők. A Pester 5-ben a tesztelt kódot `BeforeAll`-ban kell betölteni (discovery és run fázis szétválik), CI-ben pedig `Invoke-Pester -CI` NUnit/JUnit kimenetet ad.

```powershell
# Fájl: Get-Greeting.Tests.ps1 — futtatás: Invoke-Pester -Path .\Get-Greeting.Tests.ps1 -Output Detailed
BeforeAll {
    # Pester 5: a tesztelt kód betöltése a BeforeAll-ban
    function Get-Greeting {
        param([Parameter(Mandatory)][string]$Name)
        $hour = (Get-Date).Hour
        $prefix = if ($hour -lt 10) { 'Jó reggelt' } elseif ($hour -lt 18) { 'Jó napot' } else { 'Jó estét' }
        "$prefix, $Name!"
    }

    function Save-Report {
        param([Parameter(Mandatory)][string]$Folder, [Parameter(Mandatory)][object[]]$Rows)
        if (-not (Test-Path $Folder)) { throw "Nem létező mappa: $Folder" }
        $path = Join-Path $Folder 'report.csv'
        $Rows | Export-Csv -Path $path -NoTypeInformation
        $path
    }
}

Describe 'Get-Greeting' {
    It 'reggel "Jó reggelt"-tel köszön' {
        # A Get-Date mockolása: a teszt nem függ a valós időtől
        Mock Get-Date { [datetime]'2026-01-01 08:00' }
        Get-Greeting -Name 'Teszt' | Should -BeExactly 'Jó reggelt, Teszt!'
        Should -Invoke Get-Date -Times 1 -Exactly
    }

    It 'a megadott órára a várt köszönést adja' -ForEach @(
        @{ Hour = 12; Expected = 'Jó napot' }
        @{ Hour = 21; Expected = 'Jó estét' }
    ) {
        Mock Get-Date { [datetime]::Today.AddHours($Hour) }
        Get-Greeting -Name 'X' | Should -BeLike "$Expected*"
    }
}

Describe 'Save-Report' {
    It 'CSV-t ír a TestDrive-ba' {
        # $TestDrive: tesztenként takarított ideiglenes mappa
        $path = Save-Report -Folder $TestDrive -Rows @([pscustomobject]@{ A = 1 }, [pscustomobject]@{ A = 2 })
        $path | Should -Exist
        Import-Csv $path | Should -HaveCount 2
    }

    It 'nem létező mappánál hibát dob' {
        { Save-Report -Folder (Join-Path $TestDrive 'nincs') -Rows @(1) } | Should -Throw '*Nem létező mappa*'
    }
}
```
