[Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdministrator = $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);

if(-not ($isAdministrator)) {
	# Since this script requires admin privilegies (even if logged in as admin)
	# we'll need to reboot the script with "run as administrator"
	Start-Process powershell -Verb runAs $MyInvocation.MyCommand.Definition
	exit 0
}

Import-Module ActiveDirectory

# Prompt for username and create a 10 character password:
$Username = Read-Host -Prompt 'Username'
$Password = -join ((65..90) + (97..122) | Get-Random -Count 10 | % {[char]$_})

# Set it up
$newUser = New-ADUser -Name "$Username External"  `
			-GivenName "$Username"  `
			-Surname "External"  `
			-SamAccountName "$Username"  `
			-UserPrincipalName "$Username@domain.int"  `
			-Path "OU=ExternalUsers,DC=domain,DC=int"  `
			-AccountPassword(ConvertTo-SecureString $Password  -AsPlainText -Force)  `
			-ChangePasswordAtLogon $false  `
			-Enabled $true -PassThru |  `
% {
	# Do the group magic by setting "newprimarygroup" as the primary group
	# and after that remove "Domain Users" from the user.
	Add-ADGroupMember -Identity "newprimarygroup" -Members $_
	$group = get-adgroup "newprimarygroup" -properties @("primaryGroupToken")
	Set-ADUser $_ -replace @{primaryGroupID=$group.primaryGroupToken}
	Remove-ADGroupMember -Identity "Domain Users" -Members $_ -Confirm:$False
}

Write-Host "External user '$Username' with password '$Password' was created."
Write-Host ""

# Halt the window so admin gets a chance to copy the password.
Read-Host -Prompt "Press Enter to close window."
