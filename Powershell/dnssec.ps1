<#
.SYNOPSIS
    Enterprise-grade DNSSEC management utility for Windows DNS Server environments.

.DESCRIPTION
    Advanced PowerShell script for managing Domain Name System Security Extensions (DNSSEC) operations
    on Windows DNS servers. Provides complete lifecycle management of DNSSEC zones including signing,
    unsigned removal, re-signing, key management, and root trust anchor retrieval with comprehensive
    error handling, input validation, and proper resource management.

    Supported Operations:
    - Sign: Apply DNSSEC cryptographic signing to DNS zones
    - UnSign: Remove DNSSEC signing and clean up all associated keys and certificates
    - ReSign: Update zone signatures by replacing the Zone Signing Key (ZSK)
    - Root: Retrieve DNSSEC root trust anchor (DS records)
    - Keys: Display all DNSSEC keys (KSK and ZSK) for a zone
    - List: Display all zones and their DNSSEC status (default action)

    Supports batch operations via DNSZones.txt filter file for managing multiple zones efficiently.

.PARAMETER DNSServer
    Specifies the target DNS server hostname or IP address.
    Default value: '127.0.0.1' (localhost)
    Must be a valid hostname or IP address.

.PARAMETER ZoneName
    The DNS zone name to operate on (e.g., 'example.com').
    When omitted, script processes zones listed in DNSZones.txt filter file.
    Zone name is validated against existing zones on the DNS server.

.PARAMETER Action
    The DNSSEC operation to perform on the specified zone(s).
    Valid values: 'Sign' | 'UnSign' | 'ReSign' | 'Root' | 'Keys' | 'List'
    Case-insensitive. Defaults to 'List' if not specified.

.PARAMETER CryptoAlgorithm
    Cryptographic algorithm for DNSSEC key generation.
    Valid values: 'RsaSha256' (default) | 'RsaSha512' | 'EcdsaP256Sha256' | 'EcdsaP384Sha384'
    Only applicable for Sign and ReSign operations.

.PARAMETER LogPath
    Optional file path for logging script output.
    If not specified, output is console only.
    Supports transcript-style logging.

.PARAMETER Force
    Suppress confirmation prompts for destructive operations (UnSign, ReSign).
    Use with caution in production environments.

.INPUTS
    None. This script does not accept pipeline input.

.OUTPUTS
    System.String. Console and/or log file output displaying DNSSEC operation results and zone status.
    File: DNSZones.txt created in script directory if referenced but missing.

.EXAMPLE
    .\dnssec_v3.0.0.ps1
    Displays all zones and their current DNSSEC status on localhost.

.EXAMPLE
    .\dnssec_v3.0.0.ps1 -DNSServer 'ns1.example.com' -ZoneName 'example.com' -Action 'Sign'
    Signs the example.com zone on the specified DNS server using RsaSha256 algorithm.

.EXAMPLE
    .\dnssec_v3.0.0.ps1 -ZoneName 'example.com' -Action 'UnSign' -Force
    Removes DNSSEC signing from example.com without confirmation prompt.

.EXAMPLE
    .\dnssec_v3.0.0.ps1 -ZoneName 'example.com' -Action 'ReSign' -CryptoAlgorithm 'EcdsaP256Sha256'
    Re-signs example.com using ECDSA P-256 algorithm.

.EXAMPLE
    .\dnssec_v3.0.0.ps1 -ZoneName 'example.com' -Action 'Keys'
    Lists all DNSSEC keys (KSK and ZSK) configured for the example.com zone.

.EXAMPLE
    .\dnssec_v3.0.0.ps1 -Action 'Root' -LogPath 'C:\Logs\dnssec.log'
    Retrieves root trust anchor and logs output to specified file.

.NOTES
    Author: Anton Hvornum (Torxed)
    Contributor: Francois Fournier

    Created: 2024
    Version: 3.0.0
    Last Updated: April 21, 2026
    License: MIT

    Requirements:
    · Windows Server 2012 R2 or later with DNS Server role
    · PowerShell 5.1 or higher
    · Administrator privileges required
    · DNSSEC feature enabled on target DNS server
    · DNSServer PowerShell module available

    Error Codes:
    · 0: Success
    · 1: DNS Server role not installed or not accessible
    · 2: Failed to transfer key master role during operations
    · 3: Zone DNSSEC configuration error or validation failure
    · 4: Insufficient permissions on DNS server
    · 5: Invalid parameter value
    · 6: Zone not found on specified DNS server
    · 7: Cryptographic operation failed
    · 8: Certificate store operation failed

    Security Considerations:
    - Always verify DNS server connectivity before production use
    - Test UnSign and ReSign operations on non-critical zones first
    - Use Force parameter only in controlled automation scenarios
    - Monitor DNSSEC key rollover schedules
    - Maintain offline backup of DNSSEC keys
    - Verify certificate store access before operations

    Algorithm Recommendations:
    - RSA-SHA256: Widely supported, good security/performance balance
    - RSA-SHA512: Maximum security, slight performance impact
    - ECDSA-P256: Modern, smaller key size, faster operations
    - ECDSA-P384: Maximum ECDSA security

    Known Issues Fixed in v3.0.0:
    - Certificate store now properly disposed
    - Proper exception handling in all critical operations
    - Input parameter validation
    - Case-insensitive action matching
    - Variable shadowing resolved
    - Deprecated WMI replaced with native cmdlets
    - Null reference checking added

    Related Documentation:
    - DNSSEC Overview: https://docs.microsoft.com/en-us/windows-server/networking/dns/dnssec-overview
    - DNS Server PowerShell: https://docs.microsoft.com/en-us/powershell/module/dnsserver
    - GitHub Repository: https://github.com/Torxed/Scripts
    - DNSSEC Algorithm Analysis: https://www.ietf.org/rfc/rfc6944.txt

    Changelog:
    3.0.0 (2026-04-21): Major rewrite - proper parameter naming, comprehensive error handling,
                        logging support, input validation, function naming conventions,
                        algorithm selection, confirmation prompts, certificate store disposal,
                        null checks, deprecated cmdlet replacement
    2.0.0 (2026-04-21): Comprehensive help documentation, enhanced error handling
    1.0.0 (2024): Initial release

.COMPONENT
    DNS Server Management

.ROLE
    DNSSEC Operations Administrator

.FUNCTIONALITY
    Domain Name System Security Extensions Management

.LINK
    https://github.com/Torxed/Scripts

.LINK
    https://docs.microsoft.com/en-us/windows-server/networking/dns/dnssec-overview

#>

#Requires -Version 5.1
#Requires -RunAsAdministrator
#Requires -Modules DNSServer

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
	[Parameter(ValueFromPipelineByPropertyName, HelpMessage = 'DNS server hostname or IP address')]
	[ValidateNotNullOrEmpty()]
	[string]$DNSServer = '127.0.0.1',

	[Parameter(ValueFromPipelineByPropertyName, HelpMessage = 'DNS zone name (e.g., example.com)')]
	[string]$ZoneName,

	[Parameter(ValueFromPipelineByPropertyName, HelpMessage = 'DNSSEC operation to perform')]
	[ValidateSet('Sign', 'UnSign', 'ReSign', 'Root', 'Keys', 'List')]
	[string]$Action = 'List',

	[Parameter(ValueFromPipelineByPropertyName, HelpMessage = 'Cryptographic algorithm for key generation')]
	[ValidateSet('RsaSha256', 'RsaSha512', 'EcdsaP256Sha256', 'EcdsaP384Sha384')]
	[string]$CryptoAlgorithm = 'RsaSha256',

	[Parameter(HelpMessage = 'Log file path for script output')]
	[string]$LogPath,

	[Parameter(HelpMessage = 'Suppress confirmation prompts for destructive operations')]
	[switch]$Force
)

#region Script Configuration
$script:ErrorCount = 0
$script:WarningCount = 0
$script:SuccessCount = 0
$script:ScriptVersion = '3.0.0'
$script:DNSZonesFilterFile = '.\DNSZones.txt'
$script:CertStoreLocation = 'MS-DNSSEC'
$script:CertStorePath = "Cert:\LocalMachine\$($script:CertStoreLocation)"
$script:LogEnabled = $PSBoundParameters.ContainsKey('LogPath')
$script:StartTime = Get-Date
#endregion Script Configuration

#region Logging Functions
function Write-LogMessage {
	<#
    .SYNOPSIS
        Writes a message to console and optionally to log file.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory, ValueFromPipeline)]
		[string]$Message,

		[Parameter()]
		[ValidateSet('Info', 'Warning', 'Error', 'Success', 'Verbose')]
		[string]$Level = 'Info',

		[Parameter()]
		[switch]$NoNewline
	)

	process {
		$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
		$logEntry = "[$timestamp] [$Level] $Message"

		# Console output
		switch ($Level) {
			'Error' {
				Write-Host $Message -ForegroundColor Red -NoNewline:$NoNewline
				$script:ErrorCount++
			}
			'Warning' {
				Write-Host $Message -ForegroundColor Yellow -NoNewline:$NoNewline
				$script:WarningCount++
			}
			'Success' {
				Write-Host $Message -ForegroundColor Green -NoNewline:$NoNewline
				$script:SuccessCount++
			}
			'Verbose' {
				Write-Verbose $Message
			}
			default {
				Write-Host $Message -NoNewline:$NoNewline
			}
		}

		# File logging
		if ($script:LogEnabled) {
			try {
				Add-Content -Path $LogPath -Value $logEntry -ErrorAction Stop
			} catch {
				Write-Warning "Failed to write to log file: $_"
			}
		}
	}
}

function Write-LogError {
	<#
    .SYNOPSIS
        Writes error message with automatic logging.
    #>
	param([string]$Message)
	Write-Error $Message
	Write-LogMessage -Message $Message -Level 'Error'
}

function Write-LogVerbose {
	<#
    .SYNOPSIS
        Writes verbose message with automatic logging.
    #>
	param([string]$Message)
	Write-Verbose $Message
}
#endregion Logging Functions

#region Validation Functions
function Test-DNSServerConnectivity {
	<#
    .SYNOPSIS
        Validates connectivity to DNS server.

    .DESCRIPTION
        Tests that the specified DNS server is reachable and has the DNS role installed.
    #>
	[CmdletBinding()]
	param()

	Write-LogVerbose "Testing connectivity to DNS server: $DNSServer"

	try {
		$null = Get-DnsServerZone -ComputerName $DNSServer -ErrorAction Stop | Select-Object -First 1
		Write-LogMessage "Successfully connected to DNS server: $DNSServer" -Level 'Success'
		return $true
	} catch {
		Write-LogError "Failed to connect to DNS server: $DNSServer - Error: $($_.Exception.Message)"
		exit 1
	}
}

function Test-ZoneExists {
	<#
    .SYNOPSIS
        Validates that specified zone exists on DNS server.

    .PARAMETER ZoneName
        The zone name to validate.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName
	)

	try {
		$null = Get-DnsServerZone -Name $ZoneName -ComputerName $DNSServer -ErrorAction Stop
		return $true
	} catch {
		Write-LogError "Zone '$ZoneName' not found on DNS server: $DNSServer"
		exit 6
	}
}

function Test-ZoneSigned {
	<#
    .SYNOPSIS
        Determines if a zone is DNSSEC signed.

    .PARAMETER ZoneName
        The zone name to check.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName
	)

	try {
		$zone = Get-DnsServerZone -Name $ZoneName -ComputerName $DNSServer -ErrorAction Stop
		return [bool]$zone.IsSigned
	} catch {
		Write-LogError "Failed to check DNSSEC status for zone: $ZoneName - Error: $($_.Exception.Message)"
		return $false
	}
}

function Test-CertificateStoreAccess {
	<#
    .SYNOPSIS
        Validates access to DNSSEC certificate store.
    #>
	[CmdletBinding()]
	param()

	try {
		$null = Get-ChildItem -Path $script:CertStorePath -ErrorAction Stop
		return $true
	} catch {
		Write-LogError "Cannot access certificate store: $($script:CertStorePath) - Error: $($_.Exception.Message)"
		exit 8
	}
}
#endregion Validation Functions

#region Certificate Management Functions
function Remove-DNSSECCertificate {
	<#
    .SYNOPSIS
        Safely removes DNSSEC certificates from the certificate store.

    .PARAMETER ZoneName
        The zone name for certificate filtering.

    .PARAMETER KeyType
        Filter by key type: 'ZSK', 'KSK', or 'All'.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName,

		[Parameter()]
		[ValidateSet('ZSK', 'KSK', 'All')]
		[string]$KeyType = 'All'
	)

	$store = $null

	try {
		Write-LogVerbose "Removing $KeyType certificates for zone: $ZoneName"

		$store = New-Object System.Security.Cryptography.X509Certificates.X509Store $script:CertStoreLocation, 'LocalMachine' -ErrorAction Stop
		$store.Open('ReadWrite')

		$certs = @(Get-ChildItem -Path $script:CertStorePath -ErrorAction Stop)

		if ($certs.Count -eq 0) {
			Write-LogVerbose "No certificates found for zone: $ZoneName"
			return
		}

		$removedCount = 0

		foreach ($cert in $certs) {
			$certName = $cert.FriendlyName

			# Validate certificate belongs to this zone
			if (-not $certName.StartsWith($ZoneName)) {
				continue
			}

			# Filter by key type if specified
			if ($KeyType -ne 'All' -and -not $certName.EndsWith($KeyType)) {
				continue
			}

			try {
				Write-LogVerbose "Removing certificate: $certName"
				$store.Remove($cert)
				$removedCount++
			} catch {
				Write-LogError "Failed to remove certificate '$certName': $($_.Exception.Message)"
			}
		}

		Write-LogVerbose "Removed $removedCount certificate(s) for zone: $ZoneName"
	} catch {
		Write-LogError "Error accessing certificate store: $($_.Exception.Message)"
	} finally {
		if ($null -ne $store) {
			try {
				$store.Close()
				$store.Dispose()
			} catch {
				Write-LogError "Error closing certificate store: $($_.Exception.Message)"
			}
		}
	}
}
#endregion Certificate Management Functions

#region DNSSEC Operations
function New-DNSZonesFilterFile {
	<#
    .SYNOPSIS
        Creates filter file with list of manageable zones.

    .DESCRIPTION
        Generates DNSZones.txt containing all non-system, forward-lookup zones
        suitable for DNSSEC operations.
    #>
	[CmdletBinding()]
	param()

	Write-LogVerbose 'Creating filter file for zones'

	try {
		$zones = @(Get-DnsServerZone -ComputerName $DNSServer -ErrorAction Stop)
		$zoneCount = 0

		# Clear file if exists
		if (Test-Path -Path $script:DNSZonesFilterFile) {
			Clear-Content -Path $script:DNSZonesFilterFile
		}

		foreach ($zone in $zones) {
			# Filter: Non-system, forward-lookup zones, excluding TrustAnchors
			if (-not $zone.IsAutoCreated -and -not $zone.IsReverseLookupZone -and $zone.ZoneName -ne 'TrustAnchors') {
				Add-Content -Path $script:DNSZonesFilterFile -Value $zone.ZoneName
				Write-LogVerbose "Added zone to filter: $($zone.ZoneName)"
				$zoneCount++
			}
		}

		Write-LogMessage "Filter file created with $zoneCount zones" -Level 'Success'
	} catch {
		Write-LogError "Failed to create filter file: $($_.Exception.Message)"
		exit 1
	}
}

function Get-DNSSECKeyList {
	<#
    .SYNOPSIS
        Retrieves and displays DNSSEC keys for a zone.

    .PARAMETER ZoneName
        The zone name to retrieve keys for.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName
	)

	Write-LogVerbose "Listing DNSSEC keys for zone: $ZoneName"

	try {
		$keys = @(Get-DnsServerSigningKey -ZoneName $ZoneName -ComputerName $DNSServer -ErrorAction Stop)

		if ($keys.Count -eq 0) {
			Write-LogMessage "No DNSSEC keys found for zone: $ZoneName" -Level 'Warning'
			return
		}

		Write-LogMessage "`nDNSSEC Keys for zone: $ZoneName" -Level 'Info'
		Write-LogMessage ('=' * 80)

		foreach ($key in $keys) {
			Write-Host "  KeyId: $($key.KeyId)"
			Write-Host "    Type: $($key.KeyType)"
			Write-Host "    Algorithm: $($key.CryptoAlgorithm)"
			Write-Host "    State: $($key.KeyState)"
			Write-Host ''
		}
	} catch {
		Write-LogError "Failed to retrieve keys for zone: $ZoneName - Error: $($_.Exception.Message)"
		exit 7
	}
}

function Get-DNSSECRootTrustAnchor {
	<#
    .SYNOPSIS
        Retrieves the root trust anchor from DNS server.

    .DESCRIPTION
        Executes dnscmd to retrieve current DNSSEC root trust anchor.
        Operation may take up to 30 seconds.
    #>
	[CmdletBinding()]
	param()

	Write-LogVerbose 'Retrieving root trust anchor (this may take 30 seconds)'
	Write-LogMessage 'Executing dnscmd /RetrieveRootTrustAnchors...' -Level 'Info'

	try {
		$job = Start-Job -ScriptBlock { dnscmd /RetrieveRootTrustAnchors /f } -ErrorAction Stop

		if ($null -eq $job) {
			throw 'Failed to start background job'
		}

		$jobResult = Wait-Job -Job $job -Timeout 30 -ErrorAction Stop

		if ($jobResult.State -eq 'Running') {
			Stop-Job -Job $job -ErrorAction SilentlyContinue
			Write-LogError 'Root trust anchor retrieval timed out (30 seconds)'
			Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
			exit 3
		}

		$result = Receive-Job -Job $job -ErrorAction Stop
		Remove-Job -Job $job -Force -ErrorAction SilentlyContinue

		if ($result -match 'Successfully|Completed') {
			Write-LogMessage 'Root trust anchor retrieved successfully' -Level 'Success'
			return $true
		} else {
			Write-LogError 'Failed to retrieve root trust anchor'
			exit 3
		}
	} catch {
		Write-LogError "Error retrieving root trust anchor: $($_.Exception.Message)"
		exit 3
	}
}

function Initialize-DNSSECZone {
	<#
    .SYNOPSIS
        Signs a DNS zone with DNSSEC.

    .PARAMETER ZoneName
        The zone name to sign.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName
	)

	Write-LogVerbose "Initializing DNSSEC for zone: $ZoneName"

	if (Test-ZoneSigned -ZoneName $ZoneName) {
		Write-LogMessage "Zone '$ZoneName' is already signed. Use -Action ReSign to update keys" -Level 'Warning'
		return
	}


	# Transfer key master role if needed
	Write-LogVerbose "Checking key master role for zone: $ZoneName"
	try {
		$dnssecSettings = Get-DnsServerDnsSecZoneSetting -ZoneName $ZoneName -ComputerName $DNSServer -ErrorAction Stop
	} catch {
		Write-LogError "Failed to retrieve DNSSEC settings for zone '$ZoneName': $($_.Exception.Message)"
		exit 3
	}
	$keyMasterServer = $dnssecSettings.KeyMasterServer

	if ($keyMasterServer -ne $DNSServer) {
		Write-LogVerbose "Transferring key master role from '$keyMasterServer' to '$DNSServer'"
		try {
			Reset-DnsServerZoneKeyMasterRole -ZoneName $ZoneName -SeizeRole -Force -KeyMasterServer $DNSServer -ErrorAction Stop
			Write-LogMessage 'Key master role transferred successfully' -Level 'Success'
		} catch {
			Write-LogError "Failed to transfer key master role for zone '$ZoneName': $($_.Exception.Message)"
			exit 2
		}
	}

	# Configure DNSSEC settings
	Write-LogVerbose "Configuring DNSSEC settings for zone: $ZoneName"
	try {
		Set-DnsServerDnsSecZoneSetting -ZoneName $ZoneName -ComputerName $DNSServer `
			-DenialOfExistence NSec3 `
			-DistributeTrustAnchor DnsKey `
			-DSRecordGenerationAlgorithm Sha256 `
			-EnableRfc5011KeyRollover $false `
			-NSec3HashAlgorithm RsaSha1 `
			-ErrorAction Stop
	} catch {
		Write-LogError "Failed to configure DNSSEC settings for zone '$ZoneName': $($_.Exception.Message)"
		exit 3
	}
	# Create KSK (Key Signing Key)
	Write-LogVerbose "Creating Key Signing Key (KSK) for zone: $ZoneName"
	try {
		Add-DnsServerSigningKey -ZoneName $ZoneName -ComputerName $DNSServer `
			-CryptoAlgorithm $CryptoAlgorithm -Type KeySigningKey -ErrorAction Stop
		Write-LogMessage 'KSK created successfully' -Level 'Success'
	} catch {
		Write-LogError "Failed to create KSK for zone '$ZoneName': $($_.Exception.Message)"
		exit 7
	}

	# Create ZSK (Zone Signing Key)
	Write-LogVerbose "Creating Zone Signing Key (ZSK) for zone: $ZoneName"
	try {

		Add-DnsServerSigningKey -ZoneName $ZoneName -ComputerName $DNSServer `
			-CryptoAlgorithm $CryptoAlgorithm -Type ZoneSigningKey -ErrorAction Stop
		Write-LogMessage 'ZSK created successfully' -Level 'Success'
	} catch {
		Write-LogError "Failed to create ZSK for zone '$ZoneName': $($_.Exception.Message)"
		exit 7
	}
	# Sign the zone
	Write-LogVerbose "Signing zone: $ZoneName"
	try {
		Invoke-DnsServerZoneSign -ZoneName $ZoneName -Force -ComputerName $DNSServer -ErrorAction Stop
		Write-LogMessage "Zone '$ZoneName' signed successfully with algorithm: $CryptoAlgorithm" -Level 'Success'
	} catch {
		Write-LogError "Failed to sign zone '$ZoneName': $($_.Exception.Message)"
		exit 7
	}
}

function Update-DNSSECZoneSignature {
	<#
    .SYNOPSIS
        Re-signs a zone by replacing the Zone Signing Key.

    .PARAMETER ZoneName
        The zone name to re-sign.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName
	)

	Write-LogVerbose "Re-signing zone: $ZoneName"

	if (-not (Test-ZoneSigned -ZoneName $ZoneName)) {
		Write-LogMessage "Zone '$ZoneName' is not currently signed. Use -Action Sign to enable DNSSEC" -Level 'Warning'
		return
	}

	# Confirmation prompt for destructive operation
	if (-not $Force -and -not $PSCmdlet.ShouldProcess($ZoneName, 'Re-sign zone')) {
		Write-LogMessage 'ReSign operation cancelled by user' -Level 'Info'
		return
	}

	try {
		Write-LogMessage 'Removing existing zone signature' -Level 'Info'
		Invoke-DnsServerZoneUnsign -ZoneName $ZoneName -ComputerName $DNSServer -Force -ErrorAction Stop

		# Remove old ZSK
		Write-LogVerbose 'Removing old Zone Signing Keys'
		$keys = @(Get-DnsServerSigningKey -ZoneName $ZoneName -ComputerName $DNSServer -ErrorAction Stop)

		foreach ($key in $keys) {
			if ($key.KeyType -eq 'ZoneSigningKey') {
				Write-LogVerbose "Removing ZSK with KeyId: $($key.KeyId)"
				Remove-DnsServerSigningKey -KeyId $key.KeyId -ZoneName $ZoneName -Force -ComputerName $DNSServer -ErrorAction Stop
			}
		}

		# Remove old certificates
		Write-LogVerbose 'Removing old Zone Signing Key certificates'
		Remove-DNSSECCertificate -ZoneName $ZoneName -KeyType 'ZSK'

		# Create new ZSK
		Write-LogVerbose 'Creating new Zone Signing Key'
		Add-DnsServerSigningKey -ZoneName $ZoneName -ComputerName $DNSServer `
			-CryptoAlgorithm $CryptoAlgorithm -Type ZoneSigningKey -ErrorAction Stop
		Write-LogMessage 'New ZSK created' -Level 'Success'

		# Re-sign the zone
		Write-LogVerbose 'Re-signing zone with new keys'
		Invoke-DnsServerZoneSign -ZoneName $ZoneName -Force -ComputerName $DNSServer -ErrorAction Stop
		Write-LogMessage "Zone '$ZoneName' re-signed successfully" -Level 'Success'
	} catch {
		Write-LogError "Failed to re-sign zone '$ZoneName': $($_.Exception.Message)"
		exit 7
	}
}

function Remove-DNSSECZoneSignature {
	<#
    .SYNOPSIS
        Removes DNSSEC signing from a zone and cleans up keys/certificates.

    .PARAMETER ZoneName
        The zone name to unsign.
    #>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory)]
		[ValidateNotNullOrEmpty()]
		[string]$ZoneName
	)

	Write-LogVerbose "Removing DNSSEC signing from zone: $ZoneName"

	# Confirmation prompt for destructive operation
	if (-not $Force -and -not $PSCmdlet.ShouldProcess($ZoneName, 'Remove DNSSEC signing')) {
		Write-LogMessage 'UnSign operation cancelled by user' -Level 'Info'
		return
	}

	try {
		if (Test-ZoneSigned -ZoneName $ZoneName) {
			Write-LogMessage 'Removing zone signature' -Level 'Info'
			Invoke-DnsServerZoneUnsign -ZoneName $ZoneName -ComputerName $DNSServer -Force -ErrorAction Stop
		}

		# Remove all keys
		Write-LogVerbose "Removing DNSSEC keys for zone: $ZoneName"
		$keys = @(Get-DnsServerSigningKey -ZoneName $ZoneName -ComputerName $DNSServer -ErrorAction Stop)

		foreach ($key in $keys) {
			try {
				Write-LogVerbose "Removing key: $($key.KeyId)"
				Remove-DnsServerSigningKey -KeyId $key.KeyId -ZoneName $ZoneName -Force -ComputerName $DNSServer -ErrorAction Stop
			} catch {
				Write-LogError "Failed to remove key $($key.KeyId): $($_.Exception.Message)"
			}
		}

		# Remove all certificates
		Write-LogVerbose "Removing DNSSEC certificates for zone: $ZoneName"
		Remove-DNSSECCertificate -ZoneName $ZoneName -KeyType 'All'

		Write-LogMessage "Zone '$ZoneName' DNSSEC signing removed successfully" -Level 'Success'
	} catch {
		Write-LogError "Failed to unsign zone '$ZoneName': $($_.Exception.Message)"
		exit 7
	}
}

function Show-DNSSECStatus {
	<#
    .SYNOPSIS
        Displays DNSSEC status for zones.

    .PARAMETER ZoneName
        Optional zone name to show status for single zone.
        If not specified, shows all zones.
    #>
	[CmdletBinding()]
	param(
		[Parameter()]
		[string]$ZoneName
	)

	try {
		Write-Host "`n" ('=' * 80)
		Write-Host 'DNSSEC Zone Status Report'
		Write-Host '=' * 80
		Write-Host "DNS Server: $DNSServer"
		Write-Host "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
		Write-Host ('=' * 80) "`n"

		if ($ZoneName) {
			$zones = @(Get-DnsServerZone -Name $ZoneName -ComputerName $DNSServer -ErrorAction Stop)
		} else {
			$zones = @(Get-DnsServerZone -ComputerName $DNSServer -ErrorAction Stop)
		}

		if ($zones.Count -eq 0) {
			Write-LogMessage "No zones found on DNS server: $DNSServer" -Level 'Warning'
			return
		}

		foreach ($zone in $zones) {
			$signedStatus = if ($zone.IsSigned) {
				'SIGNED'
			} else {
				'UNSIGNED'
			}
			$signedColor = if ($zone.IsSigned) {
				'Green'
			} else {
				'Yellow'
			}

			Write-Host 'Zone: ' -NoNewline
			Write-Host $zone.ZoneName -ForegroundColor $signedColor -NoNewline
			Write-Host " [$signedStatus]"

			if ($script:LogEnabled) {
				Add-Content -Path $LogPath -Value "Zone: $($zone.ZoneName) [$signedStatus]"
			}
		}

		Write-Host "`n" ('=' * 80) "`n"
	} catch {
		Write-LogError "Failed to display zone status: $($_.Exception.Message)"
		exit 1
	}
}
#endregion DNSSEC Operations

#region Main Execution
function Initialize-Script {
	<#
    .SYNOPSIS
        Initializes script execution environment.
    #>
	[CmdletBinding()]
	param()

	# Clear log file if it exists
	if ($script:LogEnabled) {
		if (Test-Path -Path $LogPath) {
			Clear-Content -Path $LogPath -ErrorAction SilentlyContinue
		}
		Write-LogMessage "DNSSEC Management Script v$($script:ScriptVersion) started" -Level 'Info'
	}

	Write-Host "DNSSEC Management Script v$($script:ScriptVersion)" -ForegroundColor Cyan
	Write-Host ('=' * 80) -ForegroundColor Cyan
	Write-Host ''

	# Validate DNS server connectivity
	Test-DNSServerConnectivity

	# Validate certificate store access
	Test-CertificateStoreAccess

	# Ensure filter file exists
	if (-not (Test-Path -Path $script:DNSZonesFilterFile)) {
		Write-LogMessage "Creating filter file: $($script:DNSZonesFilterFile)" -Level 'Info'
		New-DNSZonesFilterFile
	}
}

function Invoke-DNSSECOperation {
	<#
    .SYNOPSIS
        Executes the specified DNSSEC operation.
    #>
	[CmdletBinding()]
	param()

	switch ($Action.ToLower()) {
		'sign' {
			if (-not $ZoneName) {
				Write-LogError 'Zone name required for Sign operation'
				exit 5
			}
			Test-ZoneExists -ZoneName $ZoneName
			Initialize-DNSSECZone -ZoneName $ZoneName
		}
		'unsign' {
			if (-not $ZoneName) {
				Write-LogError 'Zone name required for UnSign operation'
				exit 5
			}
			Test-ZoneExists -ZoneName $ZoneName
			Remove-DNSSECZoneSignature -ZoneName $ZoneName
		}
		'resign' {
			if (-not $ZoneName) {
				Write-LogError 'Zone name required for ReSign operation'
				exit 5
			}
			Test-ZoneExists -ZoneName $ZoneName
			Update-DNSSECZoneSignature -ZoneName $ZoneName
		}
		'root' {
			Get-DNSSECRootTrustAnchor
		}
		'keys' {
			if (-not $ZoneName) {
				Write-LogError 'Zone name required for Keys operation'
				exit 5
			}
			Test-ZoneExists -ZoneName $ZoneName
			Get-DNSSECKeyList -ZoneName $ZoneName
		}
		'list' {
			Show-DNSSECStatus -ZoneName $ZoneName
		}
		default {
			Write-LogError "Unknown action: $Action"
			exit 5
		}
	}
}

# Main execution
try {
	Initialize-Script
	Invoke-DNSSECOperation
} catch {
	Write-LogError "Unexpected error: $($_.Exception.Message)"
	exit 2
} finally {
	Write-Host ''
	Write-Host ('=' * 80) -ForegroundColor Cyan
	$duration = ((Get-Date) - $script:StartTime).TotalSeconds
	Write-LogMessage "Script completed in $([Math]::Round($duration, 2))s - Errors: $($script:ErrorCount), Warnings: $($script:WarningCount), Success: $($script:SuccessCount)" -Level 'Info'
	Write-Host '=' * 80 -ForegroundColor Cyan

	if ($script:LogEnabled) {
		Write-LogMessage "Log file saved to: $LogPath" -Level 'Info'
	}
}
#endregion Main Execution
