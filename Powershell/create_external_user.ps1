[Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdministrator = $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);

$primaryGroup = "externalUsers"
$DOMAIN = "example"
$DOMAINEXT = "int"

$OS = (Get-CimInstance Win32_OperatingSystem).Caption;
If (($OS -ne "*Windows 10*") -and ($OS -ne "*Windows Server*")) {
	Read-Host -Prompt "Will not run on anything except Windows 10 or Windows Server.";
	exit 2;
}

if(-not ($isAdministrator)) {
	# Since this script requires admin privilegies (even if logged in as admin)
	# we'll need to reboot the script with "run as administrator"
	Start-Process powershell -Verb runAs $MyInvocation.MyCommand.Definition
	exit 0
}

if(Get-HotFix -Id KB2693643 -eq "") {
	If ((Get-CimInstance Win32_ComputerSystem).SystemType -like "x64*") {
		# Download the hotfix for RSAT install
		$WebClient = New-Object System.Net.WebClient
		$WebClient.DownloadFile($URL,$Destination)
		$WebClient.Dispose()

		# Install the hotfix. No native PowerShell way that I could find.
		# wusa.exe returns immediately. Loop until install complete.
		wusa.exe $Destination /quiet /norestart /log:$home\Documents\RSAT.log
		do {
			Write-Host "." -NoNewline
			Start-Sleep -Seconds 3
		} until (Get-HotFix -Id KB2693643 -ErrorAction SilentlyContinue)

		# Double-check that the role is enabled after install.
		If ((Get-WindowsOptionalFeature -Online -FeatureName `
			RSATClient-Roles-AD-Powershell -ErrorAction SilentlyContinue).State -eq 'Enabled') {
		} Else {
			Enable-WindowsOptionalFeature -Online -FeatureName RSATClient-Roles-AD-Powershell
		}

		# Install the help
		Update-Help -Module ActiveDirectory -Verbose -Force
	}
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
			-UserPrincipalName "$Username@$DOMAIN.$DOMAINEXT"  `
			-Path "OU=ExternalUsers,DC=$DOMAIN,DC=$DOMAINEXT"  `
			-AccountPassword(ConvertTo-SecureString $Password  -AsPlainText -Force)  `
			-ChangePasswordAtLogon $false  `
			-Enabled $true -PassThru |  `
% {
	# Do the group magic by setting "$primaryGroup" as the primary group
	# and after that remove "Domain Users" from the user.
	Add-ADGroupMember -Identity "$primaryGroup" -Members $_
	$group = get-adgroup "$primaryGroup" -properties @("primaryGroupToken")
	Set-ADUser $_ -replace @{primaryGroupID=$group.primaryGroupToken}
	Remove-ADGroupMember -Identity "Domain Users" -Members $_ -Confirm:$False
}

Write-Host "External user '$Username' with password '$Password' was created."
Write-Host ""

# Halt the window so admin gets a chance to copy the password.
Read-Host -Prompt "Press Enter to close window."
