$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.DirectoryServices.Protocols
$identifier = [System.DirectoryServices.Protocols.LdapDirectoryIdentifier]::new('DC02.cafedcallao.gob.pe', 389)
$connection = [System.DirectoryServices.Protocols.LdapConnection]::new($identifier)
$connection.AuthType = [System.DirectoryServices.Protocols.AuthType]::Negotiate
$connection.SessionOptions.ProtocolVersion = 3
$connection.Bind()

$userDn = 'CN=Orozco Merino Saphira,OU=Otic,OU=CAFED,DC=cafedcallao,DC=gob,DC=pe'

$mod = [System.DirectoryServices.Protocols.DirectoryAttributeModification]::new()
$mod.Name = 'pwdLastSet'
$mod.Operation = [System.DirectoryServices.Protocols.DirectoryAttributeOperation]::Replace
[void]$mod.Add('0')
$request = [System.DirectoryServices.Protocols.ModifyRequest]::new($userDn, $mod)
$response = $connection.SendRequest($request)

Write-Host "Success"
