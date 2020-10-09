$outputFile = "outputFile.csv"
$domain = "test.int"

<#
    The code below should not be modified.
    Tweak the variables above instead.
    (Unless you know what you're doing ;)

    HOWTO:
        Open a powershell window
        write: set-executionpolicy unrestricted      (requires admin privileges)
        write: .\get_ad_stats.ps1

    Ps. Rows 46-79 can be deleted if
        you don't want the powershell module
        for Active Directory to be installed
        automatically. But if you opt out,
        you need to install it manually.
                                         Ds.
#>

function get-ageindays { Param($when) (
    new-timespan -start $when -end (get-date)).Days
}

function get-userstats { Param($server, $output) (
    Get-ADUser -server $server -filter * -Property * | 
        Select-Object -Property Name,@{Name="AccountAge";Expression={
            get-ageindays  $_.whenCreated
        }},@{Name="PasswordAge";Expression={
            get-ageindays $_.PasswordLastSet
        }} | export-csv -Delimiter “;” $output -NoTypeInformation

)}

function get-domainadmincount {Param($server) (
    Get-ADGroupMember -Server $server -Identity "Domain Admins" | measure-object).Count
}

$OS = (Get-CimInstance Win32_OperatingSystem).Caption;
If (-Not ($OS -like "*Windows 10*") -and -Not ($OS -like "*Windows Server*")) {
	Read-Host -Prompt "This script only works on Windows 10 and Windows Server.";
	exit 2;
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

$outputFile = Resolve-Path $outputFile

get-userstats $domain $outputFile
$numDomainAdmins = get-domainadmincount $domain

Write-Host ""
Write-Host "The user information is stored in: $outputFile"
Write-Host "Number of domain admins: $numDomainAdmins"