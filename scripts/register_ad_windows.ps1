# JSON arrives through stdin; credentials are never command-line arguments.
param([string]$Server = 'DC02.cafedcallao.gob.pe')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/ad_credentials.ps1"
[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
$connection = $null
$attempted = $false
$created = $false
$stage = 'validacion'
$userDn = $null
function Progress([string]$message) {
    if ($data.action -eq 'create') {
        @{tipo='progreso'; mensaje=$message} | ConvertTo-Json -Compress
        [Console]::Out.Flush()
    }
}
function Escape-Filter([string]$value) {
    return $value.Replace('\', '\5c').Replace('*', '\2a').Replace('(', '\28').Replace(')', '\29').Replace([string][char]0, '\00')
}
function Escape-Rdn([string]$value) {
    $result = $value.Replace('\', '\\').Replace(',', '\,').Replace('+', '\+').Replace('"', '\"').Replace('<', '\<').Replace('>', '\>').Replace(';', '\;').Replace('=', '\=')
    if ($result.StartsWith('#')) { $result = '\' + $result }
    return $result
}
function Search([string]$base, [string]$filter, [string[]]$attributes, [bool]$subtree = $false) {
    $scope = [System.DirectoryServices.Protocols.SearchScope]::Base
    if ($subtree) { $scope = [System.DirectoryServices.Protocols.SearchScope]::Subtree }
    $request = [System.DirectoryServices.Protocols.SearchRequest]::new($base, $filter, $scope, $attributes)
    return $connection.SendRequest($request)
}
function Modify([string]$dn, [string]$attribute, $value, [bool]$add = $false) {
    $mod = [System.DirectoryServices.Protocols.DirectoryAttributeModification]::new()
    $mod.Name = $attribute
    $mod.Operation = [System.DirectoryServices.Protocols.DirectoryAttributeOperation]::Replace
    if ($add) { $mod.Operation = [System.DirectoryServices.Protocols.DirectoryAttributeOperation]::Add }
    if ($value -is [byte[]]) { [void]$mod.Add([byte[]]$value) } else { [void]$mod.Add([string]$value) }
    $request = [System.DirectoryServices.Protocols.ModifyRequest]::new($dn, $mod)
    [void]$connection.SendRequest($request)
}
try {
    $data = [Console]::In.ReadToEnd() | ConvertFrom-Json
    if ($data.action -notin @('validate', 'create')) { throw 'Accion no admitida.' }
    if ($data.username -cnotmatch '^[a-z][a-z0-9._-]{0,19}$') { throw 'Usuario no valido (maximo 20 caracteres).' }
    Add-Type -AssemblyName System.DirectoryServices.Protocols
    $identifier = [System.DirectoryServices.Protocols.LdapDirectoryIdentifier]::new($Server, 389)
    $connection = [System.DirectoryServices.Protocols.LdapConnection]::new($identifier)
    $connection.AuthType = [System.DirectoryServices.Protocols.AuthType]::Negotiate
    $connection.Timeout = [TimeSpan]::FromSeconds(15)
    $connection.SessionOptions.ProtocolVersion = 3
    $connection.SessionOptions.Signing = $true
    $connection.SessionOptions.Sealing = $true
    $connection.SessionOptions.ReferralChasing = [System.DirectoryServices.Protocols.ReferralChasingOptions]::None
    Set-DirectoryCredential $connection
    $connection.Bind()
    Progress 'Conexion autenticada. Comprobando usuario, unidad organizativa y grupo...'
    $root = Search '' '(objectClass=*)' @('defaultNamingContext')
    $base = [string]$root.Entries[0].Attributes['defaultNamingContext'][0]
    $cafed = 'OU=CAFED,' + $base
    if (-not ($data.ou_dn -ieq $cafed -or $data.ou_dn.EndsWith(',' + $cafed, [StringComparison]::OrdinalIgnoreCase))) { throw 'La OU debe pertenecer a CAFED.' }
    $ou = Search $data.ou_dn '(objectClass=organizationalUnit)' @('distinguishedName')
    if ($ou.Entries.Count -ne 1) { throw 'La OU seleccionada no existe.' }
    $group = Search $data.group_dn '(objectClass=group)' @('distinguishedName')
    if ($group.Entries.Count -ne 1) { throw 'El grupo seleccionado no existe.' }
    $upn = $data.username + '@' + $data.upn_suffix
    $account = Escape-Filter $data.username
    $upnFilter = Escape-Filter $upn
    $existing = Search $base "(|(sAMAccountName=$account)(userPrincipalName=$upnFilter))" @('distinguishedName') $true
    if ($existing.Entries.Count -gt 0) { throw 'El usuario o UPN ya existe. Elige otro nombre y vuelve a comprobar.' }
    $display = ($data.surnames + ' ' + $data.given_names).Trim()
    $userDn = 'CN=' + (Escape-Rdn $display) + ',' + $data.ou_dn
    $cnFilter = Escape-Filter $display
    $sameName = Search $data.ou_dn "(cn=$cnFilter)" @('distinguishedName') $true
    if (@($sameName.Entries | Where-Object { $_.DistinguishedName -ieq $userDn }).Count -gt 0) { throw 'Ya existe un objeto con ese nombre completo en la OU.' }
    if ($data.action -eq 'validate') {
        $domain = Search $base '(objectClass=*)' @('minPwdLength', 'pwdProperties')
        $minimum = [int][string]$domain.Entries[0].Attributes['minPwdLength'][0]
        $properties = [int][string]$domain.Entries[0].Attributes['pwdProperties'][0]
        @{ok=$true; dn=$userDn; upn=$upn; min_password_length=$minimum; complexity=(($properties -band 1) -ne 0)} | ConvertTo-Json -Compress
    } else {
        if ([string]::IsNullOrEmpty($data.password)) { throw 'La contrasena es obligatoria.' }
        $stage = 'crear_cuenta_deshabilitada'
        Progress 'Armando los atributos del usuario...'
        $request = [System.DirectoryServices.Protocols.AddRequest]::new()
        $request.DistinguishedName = $userDn
        $attributes = [ordered]@{objectClass='user'; sAMAccountName=$data.username; userPrincipalName=$upn; givenName=$data.given_names; sn=$data.surnames; displayName=$display; userAccountControl='514'}
        if ($data.area) { $attributes['department'] = $data.area }
        foreach ($name in $attributes.Keys) {
            $attr = [System.DirectoryServices.Protocols.DirectoryAttribute]::new()
            $attr.Name = $name
            [void]$attr.Add([string]$attributes[$name])
            [void]$request.Attributes.Add($attr)
        }
        $attempted = $true
        Progress 'Creando el usuario deshabilitado en la unidad organizativa seleccionada...'
        [void]$connection.SendRequest($request)
        $created = $true
        Progress 'Usuario creado y ubicado en la unidad organizativa.'
        # Group first: resultant fine-grained password policies can depend on membership.
        $stage = 'asignar_grupo'
        Progress 'Asignando Miembro de al grupo seleccionado...'
        Modify $data.group_dn 'member' $userDn $true
        Progress 'Membresia del grupo asignada.'
        $stage = 'establecer_contrasena'
        Progress 'Estableciendo la contrasena generada y validando las politicas de Active Directory...'
        $bytes = [Text.Encoding]::Unicode.GetBytes('"' + $data.password + '"')
        try { Modify $userDn 'unicodePwd' $bytes } finally { [Array]::Clear($bytes, 0, $bytes.Length); $data.password = $null }
        $stage = 'habilitar_cuenta'
        Progress 'Habilitando la cuenta...'
        Modify $userDn 'userAccountControl' '512'
        $stage = 'exigir_cambio_contrasena'
        Progress 'Contrasena aceptada. Configurando cambio obligatorio al iniciar sesion...'
        Modify $userDn 'pwdLastSet' '0'
        $stage = 'verificar'
        Progress 'Verificando cuenta, grupo y cambio de contrasena...'
        $verified = Search $userDn '(objectClass=user)' @('userAccountControl', 'memberOf', 'pwdLastSet')
        $entry = $verified.Entries[0]
        $memberships = $entry.Attributes['memberOf'].GetValues([string])
        if (([int][string]$entry.Attributes['userAccountControl'][0] -band 2) -ne 0 -or $memberships -inotcontains $data.group_dn -or [string]$entry.Attributes['pwdLastSet'][0] -ne '0') { throw 'No se pudo confirmar el estado final.' }
        @{ok=$true; estado='creado'; dn=$userDn; upn=$upn; cambio_contrasena=$true} | ConvertTo-Json -Compress
    }
} catch {
    $failure = $_.Exception
    $ldapResponse = $null
    $cursor = $failure
    while ($null -ne $cursor) {
        if ($cursor -is [System.DirectoryServices.Protocols.DirectoryOperationException]) {
            $ldapResponse = $cursor.Response
            break
        }
        $cursor = $cursor.InnerException
    }
    $message = 'No se pudo completar la operacion. Revisa permisos y conexion con AD.'
    $code = $null
    if ($null -ne $ldapResponse) {
        $code = [string]$ldapResponse.ResultCode
        $message = 'AD rechazo la operacion: ' + $code + '.'
        if ($stage -ne 'establecer_contrasena' -and $ldapResponse.ErrorMessage) {
            $message += ' Detalle: ' + $ldapResponse.ErrorMessage
        }
    } elseif ($stage -ne 'establecer_contrasena') {
        $message = $failure.GetBaseException().Message
    }
    if ($stage -eq 'establecer_contrasena') { $message = 'AD rechazo la contrasena o su configuracion. Revisa las politicas efectivas, permisos y cifrado.' }
    if ($code -eq 'InsufficientAccessRights') {
        $message = 'AD denego permisos en la etapa ' + $stage + '. Se requieren permisos sobre los atributos de la cuenta y/o membresia, ademas de crear objetos en la OU.'
    }
    # Redact the generated password even if a provider unexpectedly includes it.
    if ($data.password) { $message = $message.Replace([string]$data.password, '[REDACTADO]') }
    if ($env:AD_PASSWORD) { $message = $message.Replace($env:AD_PASSWORD, '[REDACTADO]') }
    # Never include exception text from a password operation or echo its input.
    $state = 'rechazado'
    if ($attempted) { $state = 'resultado_incierto' }
    if ($attempted -and -not $created -and $null -ne $ldapResponse) { $state = 'rechazado_sin_crear' }
    if ($created -and $stage -notin @('habilitar_cuenta', 'verificar')) { $state = 'parcial_deshabilitado' }
    @{ok=$false; estado=$state; etapa=$stage; codigo_ldap=$code; dn=$userDn; mensaje=$message} | ConvertTo-Json -Compress
    exit 1
} finally {
    if ($null -ne $connection) { $connection.Dispose() }
}
