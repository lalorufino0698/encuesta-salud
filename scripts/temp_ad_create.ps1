$ErrorActionPreference = 'Stop'
. "$PSScriptRoot/ad_credentials.ps1"
Add-Type -AssemblyName System.DirectoryServices.Protocols
$identifier = [System.DirectoryServices.Protocols.LdapDirectoryIdentifier]::new('DC02.cafedcallao.gob.pe', 389)
$connection = [System.DirectoryServices.Protocols.LdapConnection]::new($identifier)
$connection.AuthType = [System.DirectoryServices.Protocols.AuthType]::Negotiate
$connection.SessionOptions.ProtocolVersion = 3
Set-DirectoryCredential $connection
$connection.Bind()

$userDn = 'CN=Test User99,OU=Otic,OU=CAFED,DC=cafedcallao,DC=gob,DC=pe'

# 1. Create disabled
$request = [System.DirectoryServices.Protocols.AddRequest]::new()
$request.DistinguishedName = $userDn
$attributes = [ordered]@{objectClass='user'; sAMAccountName='test99'; userPrincipalName='test99@cafedcallao.gob.pe'; userAccountControl='514'}
foreach ($name in $attributes.Keys) {
    $attr = [System.DirectoryServices.Protocols.DirectoryAttribute]::new()
    $attr.Name = $name
    [void]$attr.Add([string]$attributes[$name])
    [void]$request.Attributes.Add($attr)
}
[void]$connection.SendRequest($request)

# 2. Set password
$modPwd = [System.DirectoryServices.Protocols.DirectoryAttributeModification]::new()
$modPwd.Name = 'unicodePwd'
$modPwd.Operation = [System.DirectoryServices.Protocols.DirectoryAttributeOperation]::Replace
$bytes = [Text.Encoding]::Unicode.GetBytes('"Password123!"')
[void]$modPwd.Add([byte[]]$bytes)
$reqPwd = [System.DirectoryServices.Protocols.ModifyRequest]::new($userDn, $modPwd)
[void]$connection.SendRequest($reqPwd)

# 3. Set pwdLastSet = 0
$modPL = [System.DirectoryServices.Protocols.DirectoryAttributeModification]::new()
$modPL.Name = 'pwdLastSet'
$modPL.Operation = [System.DirectoryServices.Protocols.DirectoryAttributeOperation]::Replace
[void]$modPL.Add('0')
$reqPL = [System.DirectoryServices.Protocols.ModifyRequest]::new($userDn, $modPL)
[void]$connection.SendRequest($reqPL)

# 4. Enable account
$modUAC = [System.DirectoryServices.Protocols.DirectoryAttributeModification]::new()
$modUAC.Name = 'userAccountControl'
$modUAC.Operation = [System.DirectoryServices.Protocols.DirectoryAttributeOperation]::Replace
[void]$modUAC.Add('512')
$reqUAC = [System.DirectoryServices.Protocols.ModifyRequest]::new($userDn, $modUAC)
[void]$connection.SendRequest($reqUAC)

# 5. Read back
$reqRead = [System.DirectoryServices.Protocols.SearchRequest]::new('DC=cafedcallao,DC=gob,DC=pe', '(sAMAccountName=test99)', [System.DirectoryServices.Protocols.SearchScope]::Subtree, 'pwdLastSet', 'userAccountControl')
$response = $connection.SendRequest($reqRead)
foreach ($entry in $response.Entries) {
    Write-Host "pwdLastSet: $($entry.Attributes['pwdlastset'][0])"
}
