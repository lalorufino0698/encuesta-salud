param([string]$Server = 'DC02.cafedcallao.gob.pe')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/ad_credentials.ps1"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$connection = $null
try {
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
    $rootRequest = [System.DirectoryServices.Protocols.SearchRequest]::new(
        '', '(objectClass=*)', [System.DirectoryServices.Protocols.SearchScope]::Base,
        [string[]]@('defaultNamingContext'))
    $rootResponse = $connection.SendRequest($rootRequest)
    $baseDn = [string]$rootResponse.Entries[0].Attributes['defaultNamingContext'][0]
    if ([string]::IsNullOrWhiteSpace($baseDn)) { throw 'No se recibio la base del dominio.' }
    $request = [System.DirectoryServices.Protocols.SearchRequest]::new(
        $baseDn, '(|(objectClass=group)(objectClass=organizationalUnit))',
        [System.DirectoryServices.Protocols.SearchScope]::Subtree,
        [string[]]@('name', 'distinguishedName', 'objectClass', 'sAMAccountName', 'description'))
    $page = [System.DirectoryServices.Protocols.PageResultRequestControl]::new(500)
    [void]$request.Controls.Add($page)
    $groups = [System.Collections.Generic.List[object]]::new()
    $ous = [System.Collections.Generic.List[object]]::new()
    do {
        $response = $connection.SendRequest($request)
        foreach ($entry in $response.Entries) {
            $item = [ordered]@{nombre = [string]$entry.Attributes['name'][0]; dn = $entry.DistinguishedName; descripcion = ''}
            if ($entry.Attributes.Contains('description')) { $item.descripcion = [string]$entry.Attributes['description'][0] }
            $classes = $entry.Attributes['objectClass'].GetValues([string])
            if ($classes -contains 'group') {
                $item['cuenta'] = if ($entry.Attributes.Contains('sAMAccountName')) { [string]$entry.Attributes['sAMAccountName'][0] } else { '' }
                $groups.Add([pscustomobject]$item)
            } else { $ous.Add([pscustomobject]$item) }
        }
        $pageResponse = @($response.Controls | Where-Object { $_ -is [System.DirectoryServices.Protocols.PageResultResponseControl] })
        if ($pageResponse.Count -ne 1) { throw 'El servidor no devolvio el control de paginacion; no se mostraran resultados incompletos.' }
        $page.Cookie = $pageResponse[0].Cookie
    } while ($page.Cookie.Length -gt 0)
    [ordered]@{
        servidor = $Server
        base_dn = $baseDn
        identidad = if ($env:AD_USERNAME) { if ($env:AD_DOMAIN) { $env:AD_DOMAIN + '\' + $env:AD_USERNAME } else { $env:AD_USERNAME } } else { [System.Security.Principal.WindowsIdentity]::GetCurrent().Name }
        grupos = @($groups | Sort-Object nombre, dn)
        unidades_organizativas = @($ous | Sort-Object nombre, dn)
    } | ConvertTo-Json -Depth 5 -Compress
} catch {
    [Console]::Error.WriteLine($_.Exception.GetBaseException().Message)
    exit 1
} finally {
    if ($null -ne $connection) { $connection.Dispose() }
}
