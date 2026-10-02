param(
    [string]$Server = 'DC02.cafedcallao.gob.pe'
)

$ErrorActionPreference = 'Stop'
$connection = $null
try {
    Add-Type -AssemblyName System.DirectoryServices.Protocols
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    Write-Host "Sesion utilizada: $identity"
    $identifier = [System.DirectoryServices.Protocols.LdapDirectoryIdentifier]::new($Server, 389)
    $connection = [System.DirectoryServices.Protocols.LdapConnection]::new($identifier)
    $connection.AuthType = [System.DirectoryServices.Protocols.AuthType]::Negotiate
    $connection.Timeout = [TimeSpan]::FromSeconds(15)
    $connection.SessionOptions.ProtocolVersion = 3
    $connection.SessionOptions.Signing = $true
    $connection.SessionOptions.Sealing = $true
    $connection.SessionOptions.ReferralChasing = [System.DirectoryServices.Protocols.ReferralChasingOptions]::None
    $connection.Bind()
    Write-Host 'OK: autenticacion integrada aceptada, con firma y cifrado habilitados.'


    $request = [System.DirectoryServices.Protocols.SearchRequest]::new(
        '', '(objectClass=*)', [System.DirectoryServices.Protocols.SearchScope]::Base,
        [string[]]@('defaultNamingContext', 'dnsHostName'))
    $response = $connection.SendRequest($request)
    if ($response.Entries.Count -ne 1) { throw 'RootDSE no devolvio la entrada esperada.' }
    $baseDn = [string]$response.Entries[0].Attributes['defaultNamingContext'][0]
    $dcName = [string]$response.Entries[0].Attributes['dnsHostName'][0]
    if ([string]::IsNullOrWhiteSpace($baseDn)) { throw 'No se recibio la base del dominio.' }
    Write-Host "Controlador: $dcName"
    Write-Host "Base DN: $baseDn"

    $request = [System.DirectoryServices.Protocols.SearchRequest]::new(
        $baseDn, '(objectClass=*)', [System.DirectoryServices.Protocols.SearchScope]::Base,
        [string[]]@('distinguishedName'))
    $response = $connection.SendRequest($request)
    if ($response.Entries.Count -ne 1) { throw 'No se pudo leer el objeto base del dominio.' }
    Write-Host 'OK: lectura del dominio completada. No se modificaron objetos ni se guardaron credenciales.'
}
catch {
    Write-Host "ERROR: $($_.Exception.GetBaseException().Message)"
    Write-Host 'Ejecuta este script desde PowerShell con tu sesion habitual de dominio.'
    exit 1
}
finally {
    if ($null -ne $connection) { $connection.Dispose() }
}
