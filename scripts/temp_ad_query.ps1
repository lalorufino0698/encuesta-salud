$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.DirectoryServices.Protocols
$identifier = [System.DirectoryServices.Protocols.LdapDirectoryIdentifier]::new('DC02.cafedcallao.gob.pe', 389)
$connection = [System.DirectoryServices.Protocols.LdapConnection]::new($identifier)
$connection.AuthType = [System.DirectoryServices.Protocols.AuthType]::Negotiate
$connection.SessionOptions.ProtocolVersion = 3
$connection.Bind()

$request = [System.DirectoryServices.Protocols.SearchRequest]::new('DC=cafedcallao,DC=gob,DC=pe', '(sAMAccountName=sorozco)', [System.DirectoryServices.Protocols.SearchScope]::Subtree, 'pwdLastSet', 'userAccountControl', 'accountExpires')
$response = $connection.SendRequest($request)

foreach ($entry in $response.Entries) {
    Write-Host "DN: $($entry.DistinguishedName)"
    Write-Host "pwdLastSet: $($entry.Attributes['pwdlastset'][0])"
    Write-Host "userAccountControl: $($entry.Attributes['useraccountcontrol'][0])"
    Write-Host "accountExpires: $($entry.Attributes['accountexpires'][0])"
}
