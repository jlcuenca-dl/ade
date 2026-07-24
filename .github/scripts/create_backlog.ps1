# create_backlog.ps1
# Script para crear el backlog completo del proyecto ADE en GitHub
# Usa la API REST de GitHub directamente (no requiere gh CLI)
# Repo: jlcuenca-dl/ade

param(
    [Parameter(Mandatory=$true)]
    [string]$Token
)

$OWNER = "jlcuenca-dl"
$REPO = "ade"
$BASE_URL = "https://api.github.com/repos/$OWNER/$REPO"
$HEADERS = @{
    "Authorization" = "Bearer $Token"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
    "User-Agent" = "ADE-Backlog-Script"
}

function Invoke-GitHubAPI {
    param([string]$Method, [string]$Url, [hashtable]$Body = $null)
    try {
        $params = @{
            Method = $Method
            Uri = $Url
            Headers = $HEADERS
            ContentType = "application/json; charset=utf-8"
        }
        if ($Body) {
            $jsonBody = $Body | ConvertTo-Json -Depth 5
            $params["Body"] = [System.Text.Encoding]::UTF8.GetBytes($jsonBody)
        }
        return Invoke-RestMethod @params
    } catch {
        $status = $_.Exception.Response.StatusCode.value__
        if ($status -eq 422) {
            Write-Host "    (Ya existe - continuando)" -ForegroundColor DarkGray
            return $null
        }
        Write-Host "    ERROR ($status): $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  CREANDO BACKLOG ADE EN GITHUB" -ForegroundColor Cyan
Write-Host "  Repo: $OWNER/$REPO" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Verificar autenticacion
Write-Host ">>> Verificando autenticacion..." -ForegroundColor Yellow
$user = Invoke-GitHubAPI -Method "GET" -Url "https://api.github.com/user"
if (-not $user) {
    Write-Host "ERROR: Token invalido o sin permisos. Verifica tu PAT." -ForegroundColor Red
    exit 1
}
Write-Host "  Autenticado como: $($user.login)" -ForegroundColor Green
Write-Host ""

# ============================================
# PASO 1: CREAR MILESTONES (Releases)
# ============================================
Write-Host ">>> PASO 1: Creando Milestones (Releases)..." -ForegroundColor Yellow

$milestones = @(
    @{ title = "R0 - MVP / Funcionalidad base"; description = "Base de datos, infraestructura, extraccion, carga, validaciones y normatividad base" },
    @{ title = "R1 - Mejoras y gestion avanzada"; description = "Gestion de incidencias, reportes, versionado de BD, mantenimiento" },
    @{ title = "R2 - Optimizacion y complementarios"; description = "Ajustes masivos, documentacion QA, interfaces complementarias" },
    @{ title = "R3 - Roles y Permisos"; description = "Comunicacion, organigrama, administracion de usuarios, roles y permisos" }
)

foreach ($m in $milestones) {
    Write-Host "  Creando milestone: $($m.title)" -ForegroundColor Gray
    Invoke-GitHubAPI -Method "POST" -Url "$BASE_URL/milestones" -Body @{
        title = $m.title
        description = $m.description
        state = "open"
    } | Out-Null
}
Write-Host "  Milestones listos." -ForegroundColor Green
Write-Host ""

# ============================================
# PASO 2: CREAR LABELS
# ============================================
Write-Host ">>> PASO 2: Creando Labels..." -ForegroundColor Yellow

$labels = @(
    @{ name = "epic:E1-comunicacion"; color = "1D76DB"; description = "Comunicacion y requerimientos" },
    @{ name = "epic:E2-normatividad"; color = "D93F0B"; description = "Gestor de Normatividad sectorial e interna" },
    @{ name = "epic:E3-incidencias"; color = "E99695"; description = "Gestor de incidencias y reportes" },
    @{ name = "epic:E4-reportes"; color = "F9D0C4"; description = "Generador de reportes y cartas aclaratorias" },
    @{ name = "epic:E5-validaciones"; color = "0E8A16"; description = "Gestor de validaciones y transformacion" },
    @{ name = "epic:E6-base-datos"; color = "006B75"; description = "Base de datos y procedimientos BD origen" },
    @{ name = "epic:E7-carga-info"; color = "FBCA04"; description = "Modulo de carga de informacion y ajustes" },
    @{ name = "epic:E8-extraccion"; color = "B60205"; description = "Extraccion de informacion origen SIISA TCC Reservas" },
    @{ name = "epic:E9-infraestructura"; color = "5319E7"; description = "Configuracion y gobernanza de datos infraestructura" },
    @{ name = "epic:E10-mantenimiento"; color = "BFD4F2"; description = "Mantenimiento post-implementacion" },
    @{ name = "priority:0-lowest"; color = "CCCCCC"; description = "Prioridad mas baja" },
    @{ name = "priority:1-low"; color = "78C7FF"; description = "Prioridad baja" },
    @{ name = "priority:2-medium"; color = "FBCA04"; description = "Prioridad media" },
    @{ name = "priority:3-medium"; color = "FBC404"; description = "Prioridad media" },
    @{ name = "priority:4-high"; color = "FF9F1C"; description = "Prioridad alta" },
    @{ name = "priority:5-high"; color = "FF9E1C"; description = "Prioridad alta" },
    @{ name = "priority:6-high"; color = "FF9D1C"; description = "Prioridad alta" },
    @{ name = "priority:7-highest"; color = "B60205"; description = "Prioridad maxima" },
    @{ name = "priority:8-highest"; color = "B50205"; description = "Prioridad maxima" },
    @{ name = "sp:1"; color = "C2E0C6"; description = "1 Story Point" },
    @{ name = "sp:2"; color = "0E8A16"; description = "2 Story Points" },
    @{ name = "sp:3"; color = "006B75"; description = "3 Story Points" },
    @{ name = "sp:4"; color = "1D76DB"; description = "4 Story Points" },
    @{ name = "sp:5"; color = "5319E7"; description = "5 Story Points" },
    @{ name = "type:story"; color = "1D76DB"; description = "Historia de usuario" }
)

foreach ($l in $labels) {
    Write-Host "  Creando label: $($l.name)" -ForegroundColor Gray
    Invoke-GitHubAPI -Method "POST" -Url "$BASE_URL/labels" -Body @{
        name = $l.name
        color = $l.color
        description = $l.description
    } | Out-Null
}
Write-Host "  Labels listos." -ForegroundColor Green
Write-Host ""

# ============================================
# PASO 3: OBTENER IDs DE MILESTONES
# ============================================
Write-Host ">>> PASO 3: Obteniendo IDs de milestones..." -ForegroundColor Yellow

$rawMs = Invoke-GitHubAPI -Method "GET" -Url "$BASE_URL/milestones"
$milestoneMap = @{}
foreach ($ms in $rawMs) {
    if ($ms.title -like "R0*") { $milestoneMap["R0"] = $ms.number }
    elseif ($ms.title -like "R1*") { $milestoneMap["R1"] = $ms.number }
    elseif ($ms.title -like "R2*") { $milestoneMap["R2"] = $ms.number }
    elseif ($ms.title -like "R3*") { $milestoneMap["R3"] = $ms.number }
}

Write-Host "  R0=#$($milestoneMap['R0']), R1=#$($milestoneMap['R1']), R2=#$($milestoneMap['R2']), R3=#$($milestoneMap['R3'])" -ForegroundColor Green
Write-Host ""

# ============================================
# PASO 4: CREAR ISSUES (99 Historias de Usuario)
# ============================================
Write-Host ">>> PASO 4: Creando 99 Issues..." -ForegroundColor Yellow

$issues = @(
    # E9 - Configuracion y gobernanza - Prioridad 0
    @{ id=609; task="Documentacion tecnica y codigos fuente"; epic="epic:E9-infraestructura"; priority="priority:0-lowest"; release="R0"; sp="sp:1" },
    @{ id=610; task="Caracteristicas y costos de la infraestructura"; epic="epic:E9-infraestructura"; priority="priority:0-lowest"; release="R0"; sp="sp:1" },
    @{ id=640; task="Entornos de desarrollo de QA, produccion y desarrollo"; epic="epic:E9-infraestructura"; priority="priority:0-lowest"; release="R0"; sp="sp:1" },
    @{ id=642; task="Documentacion de los diagramas entidad-relacion y diccionario de datos"; epic="epic:E9-infraestructura"; priority="priority:0-lowest"; release="R2"; sp="" },
    @{ id=644; task="Reporte de pruebas de calidad"; epic="epic:E9-infraestructura"; priority="priority:0-lowest"; release="R2"; sp="" },
    # E6 - BASE DE DATOS - Prioridad 1
    @{ id=601; task="Base de datos integral ADE (capa 1)"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R0"; sp="sp:2" },
    @{ id=602; task="Base de datos integral ADE con politicas internas (capa 2)"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R0"; sp="sp:2" },
    @{ id=603; task="Insumos de SIISA (datos en CLOUD SQL postgreSQL)"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R0"; sp="sp:2" },
    @{ id=604; task="Base de datos integral detalle para SESAs (capa 3)"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R0"; sp="sp:3" },
    @{ id=605; task="Base de datos para reportes SESAs agrupada (capa 4)"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R0"; sp="sp:3" },
    @{ id=606; task="Gestor de versiones de las bases ajustadas"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R1"; sp="" },
    @{ id=607; task="Restablecer a X version"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R1"; sp="" },
    @{ id=608; task="Bitacora de cambios de las bases"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R1"; sp="" },
    @{ id=754; task="Base de datos integral ADE"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R0"; sp="sp:2" },
    @{ id=761; task="Gestor de bases"; epic="epic:E6-base-datos"; priority="priority:1-low"; release="R1"; sp="" },
    # E7 - Modulo de carga - Prioridad 2
    @{ id=634; task="Informacion proveniente de SIISA (origen)"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R0"; sp="sp:3" },
    @{ id=635; task="Brechas de informacion"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R0"; sp="sp:4" },
    @{ id=636; task="Carga de ajustes de informacion"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R0"; sp="sp:4" },
    @{ id=637; task="Cifras control"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R0"; sp="sp:4" },
    @{ id=638; task="Los ajustes sean uno a uno o masivo"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R2"; sp="" },
    @{ id=639; task="Gestor de versiones de carga de informacion de las distintas areas"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R2"; sp="" },
    @{ id=771; task="Procedimiento de modificacion de la base de datos origen"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R2"; sp="" },
    @{ id=772; task="Interfaz de carga de informacion"; epic="epic:E7-carga-info"; priority="priority:2-medium"; release="R2"; sp="" },
    # E2 - Normatividad - Prioridad 3
    @{ id=597; task="Notificacion de actualizacion y cambios con versiones de la CNSF"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R1"; sp="" },
    @{ id=620; task="Notificaciones periodicas de actualizacion de politicas internas"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R1"; sp="" },
    @{ id=621; task="Bitacora de politicas internas y externas"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R1"; sp="" },
    @{ id=622; task="Gestor de version de reglas internas"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R0"; sp="sp:5" },
    @{ id=623; task="Indicadores de cumplimiento de aplicacion de politicas internas"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R0"; sp="sp:5" },
    @{ id=681; task="Gestor de version de reglas del sector"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R0"; sp="sp:5" },
    @{ id=683; task="Administracion de politicas por capas"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R0"; sp="sp:5" },
    @{ id=685; task="Aplicacion de politicas y reglas internas-externas por capas"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R0"; sp="sp:5" },
    @{ id=687; task="Comparador de versiones de ano con ano"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R0"; sp="sp:5" },
    @{ id=688; task="Interfaz amigable"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R1"; sp="" },
    @{ id=689; task="Notificacion de cambios en politicas y reglas de negocio"; epic="epic:E2-normatividad"; priority="priority:3-medium"; release="R1"; sp="" },
    # E5 - Validaciones - Prioridad 4
    @{ id=627; task="Gestor de validacion (version de validaciones, actualizacion, etc.)"; epic="epic:E5-validaciones"; priority="priority:4-high"; release="R0"; sp="sp:4" },
    @{ id=628; task="Interfaz de administracion y modelo de validaciones"; epic="epic:E5-validaciones"; priority="priority:4-high"; release="R0"; sp="sp:4" },
    @{ id=629; task="Clasificacion de validaciones segun su tipo e importancia (por niveles)"; epic="epic:E5-validaciones"; priority="priority:4-high"; release="R0"; sp="sp:4" },
    @{ id=630; task="Clasificacion de prioridad de incidencias por capas"; epic="epic:E5-validaciones"; priority="priority:4-high"; release="R0"; sp="sp:4" },
    # E8 - Extraccion - Prioridad 4
    @{ id=792; task="Copia de base de datos de SIISA"; epic="epic:E8-extraccion"; priority="priority:4-high"; release="R0"; sp="sp:1" },
    @{ id=793; task="Procesos de ETL para lectura de la copia de SIISA"; epic="epic:E8-extraccion"; priority="priority:4-high"; release="R0"; sp="sp:3" },
    # E3 - Incidencias - Prioridad 5
    @{ id=698; task="Restriccion de atencion a incidencias"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=699; task="Interfaz de interaccion de usuarios para resolucion de incidencias"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=700; task="Envio de incidencias al responsable correspondiente"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=701; task="Tablero de control de la atencion de incidencias por capas y campo"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=702; task="Graficos dinamicos y Tableros dinamicos"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=704; task="Gestor de aprobaciones"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=705; task="Comunicacion bilateral para la solucion de las incidencias"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=706; task="Tablero ejecutivo de revision de incidencias (Indicadores de control)"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=708; task="Modulo de indicadores realizando drilldown a nivel bajo"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=709; task="Apartado de explicaciones"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=710; task="Vistas ejecutivas de la calidad de la informacion"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=711; task="Motivo de la modificacion"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=712; task="Niveles de aprobacion de la GIE (asignacion de responsabilidad)"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=713; task="Motivo de la aprobacion o rechazo"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=714; task="Niveles de aprobacion fuera de la GIE"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=715; task="Panel de revision de incidencias"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=716; task="Modulo de comunicacion (reasignacion de actividades dentro de la GIE)"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=717; task="Apartado de explicaciones (2)"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=719; task="Clasificacion de prioridad de las incidencias por capas"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=720; task="Restablecer a X version de ajustes"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    @{ id=722; task="Modelo de aplicacion de ajustes de incidencias por capas"; epic="epic:E3-incidencias"; priority="priority:5-high"; release="R1"; sp="" },
    # E4 - Reportes - Prioridad 6
    @{ id=631; task="Utilizar la informacion de cualquier capa"; epic="epic:E4-reportes"; priority="priority:6-high"; release="R1"; sp="" },
    @{ id=737; task="Bitacora de generacion de reportes (responsable, fecha)"; epic="epic:E4-reportes"; priority="priority:6-high"; release="R1"; sp="" },
    @{ id=740; task="Generacion de reportes en distintos tipos de archivos (txt, xls)"; epic="epic:E4-reportes"; priority="priority:6-high"; release="R1"; sp="" },
    @{ id=742; task="Interfaz de configuracion de campos de reportes y cifras control"; epic="epic:E4-reportes"; priority="priority:6-high"; release="R1"; sp="" },
    @{ id=744; task="Admision y configuracion de plantillas"; epic="epic:E4-reportes"; priority="priority:6-high"; release="R1"; sp="" },
    # E1 - Comunicacion - Prioridad 7
    @{ id=577; task="Listado de roles con permisos asignados"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=578; task="Bitacora en los roles y permisos"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=579; task="Criterios de modificacion al rol y permisos del usuario"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=580; task="Carga de datos generales de usuarios (individual y masiva)"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=581; task="Buscador de roles y permisos"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=582; task="Asignacion de roles a nivel de usuario"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=583; task="Descarga de Bitacora de los requerimientos"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=584; task="Envio de notificaciones en plataforma y por correo"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=585; task="Resumen visual del usuario al modificar o dar de alta"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=586; task="Roles y permisos, dependencias del organigrama de usuarios de BD"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=587; task="Uno o Todos los usuarios inactivos"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=588; task="Bitacora de modificaciones del organigrama"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=589; task="Administracion del organigrama"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=590; task="Bitacora de atencion a notificaciones"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=591; task="Regla de re-distribucion cuando no hay usuario activo"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=592; task="Visualizacion de los roles y permisos del usuario (panel)"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=593; task="Buscador dentro de la bitacora administrativa"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=594; task="Consulta, listado, busqueda y descarga de listado de usuarios"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=595; task="Administracion de notificaciones (Alta y modificacion)"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=596; task="Tablero de Metricas de requerimientos"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=598; task="Reglas de escalamiento de las notificaciones"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=599; task="Tablero de flujo de proceso del trabajo"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=600; task="Modulo de administracion del flujo de trabajo"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=613; task="Modulo de administracion (Organigrama)"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=615; task="Tablero de flujo de proceso del trabajo (vista 2)"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=616; task="Visualizacion de usuarios y permisos (Panel de usuarios)"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=617; task="Alta, baja o modificacion de usuarios"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=649; task="Administracion de roles y permisos"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=652; task="Roles y permisos, dependencias del organigrama de la aplicacion"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=653; task="Ventana emergente de datos generales del organigrama"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    @{ id=654; task="Diseno grafico del panel del organigrama"; epic="epic:E1-comunicacion"; priority="priority:7-highest"; release="R3"; sp="" },
    # E10 - Mantenimiento - Prioridad 8
    @{ id=611; task="Servicios de mantenimiento post-implementacion"; epic="epic:E10-mantenimiento"; priority="priority:8-highest"; release="R1"; sp="" },
    @{ id=612; task="Documentacion y cumplimiento de acuerdos de seguridad e infraestructura"; epic="epic:E10-mantenimiento"; priority="priority:8-highest"; release="R1"; sp="" },
    @{ id=614; task="Politicas del proceso de extraccion"; epic="epic:E10-mantenimiento"; priority="priority:8-highest"; release="R1"; sp="" }
)

$total = $issues.Count
$count = 0
$errors = 0

foreach ($issue in $issues) {
    $count++
    $title = "[HU-$($issue.id)] $($issue.task)"
    $labelsList = @($issue.epic, $issue.priority, "type:story")
    if ($issue.sp -ne "") { $labelsList += $issue.sp }

    $body = @"
## Historia de Usuario

**ID Original:** HU-$($issue.id)
**Modulo (Epica):** $($issue.epic -replace 'epic:', '')
**Release:** $($issue.release)

## Descripcion

$($issue.task)

## Criterios de Aceptacion

- [ ] Funcionalidad implementada segun requerimiento
- [ ] Pruebas unitarias escritas y pasando
- [ ] Documentacion actualizada
- [ ] Code review aprobado
- [ ] Pruebas de integracion verificadas

## Definition of Done

- [ ] Codigo mergeado a main
- [ ] Desplegado en entorno de QA
- [ ] Validado por Product Owner
"@

    Write-Host "  [$count/$total] Creando: $title" -ForegroundColor Gray

    $issueBody = @{
        title = $title
        body = $body
        labels = $labelsList
    }

    # Add milestone if mapped
    $msNum = $milestoneMap[$issue.release]
    if ($msNum) {
        $issueBody["milestone"] = $msNum
    }

    $result = Invoke-GitHubAPI -Method "POST" -Url "$BASE_URL/issues" -Body $issueBody

    if (-not $result) {
        $errors++
    }

    # Delay to respect rate limits (max 5000 req/hr with auth)
    Start-Sleep -Milliseconds 400
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  BACKLOG CREADO" -ForegroundColor Green
Write-Host "  Total procesados: $total" -ForegroundColor Green
Write-Host "  Errores: $errors" -ForegroundColor $(if($errors -gt 0){"Red"}else{"Green"})
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Verifica en: https://github.com/$OWNER/$REPO/issues" -ForegroundColor Cyan
Write-Host ""
