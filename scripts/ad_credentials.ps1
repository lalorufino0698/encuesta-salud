# Called by the Python backend with AD settings in the child environment.
function Set-DirectoryCredential($Connection) {
    if ($env:AD_USERNAME -or $env:AD_PASSWORD) {
        if (-not $env:AD_USERNAME -or -not $env:AD_PASSWORD) { throw 'Falta AD_USERNAME o AD_PASSWORD.' }
        if ($env:AD_DOMAIN) {
            $Connection.Credential = [System.Net.NetworkCredential]::new($env:AD_USERNAME, $env:AD_PASSWORD, $env:AD_DOMAIN)
        } else {
            $Connection.Credential = [System.Net.NetworkCredential]::new($env:AD_USERNAME, $env:AD_PASSWORD)
        }
    }
}
