$externalUserGroup = "externalusers"

$DOMAIN = "domain"
$DOMAINEXT = "int"
$ADMINGROUP = "Domain Admins"

$OS = (Get-CimInstance Win32_OperatingSystem).Caption;
If (-Not ($OS -like "*Windows 10*") -and -Not ($OS -like "*Windows Server*")) {
	Read-Host -Prompt "This script only works on Windows 10 and Windows Server.";
	exit 2;
}

[Security.Principal.WindowsPrincipal]$user = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdministrator = $user.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator);

if(-not ($isAdministrator)) {
	# Since this script requires admin privilegies (even if logged in as admin)
	# we'll need to reboot the script with "run as administrator"
	Start-Process powershell -Verb runAs -ArgumentList "-ep unrestricted -file $PSCommandPath"
	exit 0
}

if(-Not (Get-HotFix -Id KB2693643 -ErrorAction SilentlyContinue) -or -Not (Get-Help Get-ADDomain)) {
	Write-Host "Installing ActiveDirectory tools (Might take a minute or two).";
	$URL = "https://download.microsoft.com/download/1/D/8/1D8B5022-5477-4B9A-8104-6A71FF9D98AB/WindowsTH-RSAT_WS_1803-x64.msu";
	$Destination = "$ENV:UserProfile\AppData\Local\Temp\RSAT.msu"
	If ((Get-CimInstance Win32_ComputerSystem).SystemType -like "x64*") {
		# Download the hotfix for RSAT install
		$WebClient = New-Object System.Net.WebClient
		$WebClient.DownloadFile($URL, $Destination)
		$WebClient.Dispose()

		# Install the hotfix. No native PowerShell way that I could find.
		# wusa.exe returns immediately. Loop until install complete.
		wusa.exe $Destination /quiet /norestart /log:$home\Documents\RSAT.log
		do {
			Write-Host "." -NoNewline
			Start-Sleep -Seconds 3
		} until (Get-HotFix -Id KB2693643 -ErrorAction SilentlyContinue)

		Write-Host "";
		Write-Host "Successfully installed ActiveDirectory tools";

		# Double-check that the role is enabled after install.
		If (-Not ((Get-WindowsOptionalFeature -Online -FeatureName `
					RSATClient-Roles-AD-Powershell -ErrorAction SilentlyContinue).State `
					-eq 'Enabled')) {

			Enable-WindowsOptionalFeature -Online -FeatureName `
				 RSATClient-Roles-AD-Powershell
		}

		# Install the help
		Update-Help -Module ActiveDirectory -Force | out-null
	}
}

Import-Module ActiveDirectory
$UserGroups = (Get-ADPrincipalGroupMembership $env:UserName| select -ExpandProperty name)

# Yes, "Domain Admins" is not something that should be used.
if(-not ($UserGroups -contains $ADMINGROUP)) {
	Write-Host "Not a domain admin, please log in with your administrator account."
	#$credential = Get-Credential;
	#Start-Process powershell -credential $credential -ArgumentList " -ep unrestricted -file $PSCommandPath"
}

# Prompt for username and create a 10 character password:
$Username = Read-Host -Prompt 'Username'
$Password = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 10 | % {[char]$_})

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
	# Do the group magic by setting "$externalUserGroup" as the primary group
	# and after that remove "Domain Users" from the user.
	Add-ADGroupMember -Identity "$externalUserGroup" -Members $_
	$group = get-adgroup "$externalUserGroup" -properties @("primaryGroupToken")
	Set-ADUser $_ -replace @{primaryGroupID=$group.primaryGroupToken}
	Remove-ADGroupMember -Identity "Domain Users" -Members $_ -Confirm:$False
}

Write-Host "External user '$Username' with password '$Password' was created."
Write-Host ""

# Halt the window so admin gets a chance to copy the password.
Read-Host -Prompt "Press Enter to close window."
