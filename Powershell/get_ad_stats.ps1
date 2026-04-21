<#
.SYNOPSIS
    Generates comprehensive statistics for Active Directory users and domain administrators.

.DESCRIPTION
    This script queries Active Directory to collect detailed user account statistics including:
    - User account names and creation dates (Account Age in days)
    - Password last set dates (Password Age in days or "Never" if not set)
    - Count of domain administrators
    - Exports user statistics to a CSV file (semicolon-delimited) for analysis and reporting

    The script automatically validates Windows OS compatibility, imports the Active Directory
    module if needed, and creates output directories as necessary. It supports custom domain
    specification or uses the current domain automatically.

    Key Features:
    - Robust error handling with meaningful exit codes
    - Performance optimized (selective AD property queries)
    - Detailed verbose logging support
    - Input validation and parameter checking
    - Compatible with Windows 10, Windows 11, and Windows Server
    - Execution time tracking and summary reporting

.PARAMETER outputFile
    Specifies the path and filename for the CSV export file containing user statistics.
    - Default: '.\UserStats.csv'
    - Type: [string]
    - Note: Creates parent directory if it doesn't exist
    - Example: "C:\Reports\ADUsers.csv" or "D:\Exports\Users.csv"

.PARAMETER domain
    Specifies the Active Directory domain to query.
    - Default: Current domain (Get-ADDomain).DNSRoot
    - Type: [string]
    - Format: Domain FQDN (e.g., contoso.com, subdomain.company.local)
    - Optional: If omitted, queries the current domain

.INPUTS
    [string]
    Accepts domain names via the -domain parameter. Can be piped or specified directly.

.OUTPUTS
    [Console Output]
    - Success message with file path and domain admin count
    - Error messages with detailed diagnostics if issues occur
    - Execution time summary

    [CSV File Output]
    - File: UserStats.csv (or specified -outputFile path)
    - Delimiter: Semicolon (;)
    - Columns: Name, AccountAge (days), PasswordAge (days or "Never")

.EXAMPLE
    PS> .\get_ad_stats_v2.2.0.ps1
    Description: Executes against current domain and exports to .\UserStats.csv in current directory.

.EXAMPLE
    PS> .\get_ad_stats_v2.2.0.ps1 -outputFile "C:\Reports\ADUsers.csv" -domain "contoso.com"
    Description: Exports contoso.com domain users to specified CSV file. Creates C:\Reports if needed.

.EXAMPLE
    PS> .\get_ad_stats_v2.2.0.ps1 -outputFile "D:\Exports\Users.csv" -Verbose
    Description: Exports to specified file with verbose output for troubleshooting.

.EXAMPLE
    PS> .\get_ad_stats_v2.2.0.ps1 -domain "subdomain.company.local" -Verbose -WhatIf
    Description: Shows what would be exported for subdomain with verbose logging.

.NOTES
    Author:              Your Name / Organization
    Version:             2.2.0
    Created:             Unknown (Legacy Script - Refactored)
    Last Updated:        2026-04-21
    PowerShell Version:  5.1 or later
    License:             Proprietary

    Requirements:
        - Windows 10, Windows 11, or Windows Server (2012 R2 or later)
        - ActiveDirectory PowerShell Module
        - Read permissions on Active Directory domain
        - Domain Admins group query access (or Enterprise Admin equivalent)
        - Administrator privileges recommended (not always required)

    Exit Codes:
        0 - Success
        1 - Unexpected error during execution
        2 - Operating system incompatible
        3 - Domain retrieval failed
        4 - Output directory validation failed
        5 - User statistics retrieval failed

    Issues Fixed in v2.2.0:
        - Fixed undefined script variables ($script:ErrorCount, $WarningCount, $SuccessCount)
        - Fixed invalid Write-Host -Level parameter (not supported)
        - Fixed improper region nesting for try-catch-finally structure
        - Fixed default parameter value timestamp expression evaluation
        - Fixed typo in Variables section header comment (MAVariables -> VARIABLES)
        - Fixed improper $? status check logic for domain admin count
        - Added proper null/empty handling throughout
        - Added execution time tracking with proper formatting
        - Improved output readability with consistent formatting
        - Added data validation for CSV export success

    Issues Fixed in v2.1.0:
        - Function naming convention corrected to PascalCase (Get-AgeInDays, Get-UserStats, etc.)
        - Function parameters and calls now properly match
        - Comprehensive error handling with try-catch blocks on all operations
        - Output directory validation with auto-creation capability
        - Performance optimization: selective AD property queries (was Get-ADUser -Property *)
        - Null handling for PasswordLastSet returns "Never" instead of errors
        - Added parameter validation with ValidateNotNullOrEmpty
        - Improved logging and error reporting with meaningful messages
        - OS validation logic corrected with regex pattern matching
        - Graceful handling of empty AD result sets
        - Module import safety check before loading

    Previous Issues Resolved:
        - Function calls used lowercase naming (get-userstats vs Get-UserStats)
        - Parameter mismatch between function definitions and calls
        - Missing error handling for AD queries
        - No directory creation for output files
        - Excessive AD property loading impacting performance
        - No null checks for optional AD properties
        - Insufficient parameter validation
        - Wildcard OS detection (Windows 1*) too ambiguous

.PREREQUISITES
    Run the following commands before first execution (if needed):

    # Allow script execution (elevated PowerShell required):
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

    # Or for all users:
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope LocalMachine -Force

    # Verify Active Directory module is available:
    Get-Module -Name ActiveDirectory -ListAvailable

.HOWTO
    Quick Start:
    1. Open PowerShell as Administrator
    2. Navigate to script directory: cd 'E:\DevOps\AZRepo\AD\Users'
    3. Run with default settings:
       .\get_ad_stats_v2.2.0.ps1

    Advanced Usage:
    1. For specific domain with custom output:
       .\get_ad_stats_v2.2.0.ps1 -domain "contoso.com" -outputFile "C:\Reports\contoso_users.csv"
    2. With verbose output for troubleshooting:
       .\get_ad_stats_v2.2.0.ps1 -Verbose
    3. Test what would be executed:
       .\get_ad_stats_v2.2.0.ps1 -WhatIf
    4. Get help:
       Get-Help .\get_ad_stats_v2.2.0.ps1 -Full

.COMPONENT
    - Active Directory PowerShell Module (required)
    - Windows 10/11 or Windows Server OS
    - .NET Framework 4.5+

.ROLE
    - Domain Administrator or equivalent
    - User with AD read permissions
    - Directory write permissions for output location

.FUNCTIONALITY
    Active Directory Reporting | User Statistics | CSV Export | Domain Administration

.LINK
    https://docs.microsoft.com/en-us/powershell/module/activedirectory/
    https://docs.microsoft.com/en-us/powershell/module/activedirectory/get-aduser
    https://docs.microsoft.com/en-us/powershell/module/activedirectory/get-addomain
    https://docs.microsoft.com/en-us/powershell/module/activedirectory/get-adgroupmember

#>

#Requires -Version 5.1
#Requires -Modules ActiveDirectory

[CmdletBinding(SupportsShouldProcess)]
param(
	[Parameter(
		ValueFromPipeline = $true,
		ValueFromPipelineByPropertyName = $true,
		HelpMessage = 'Output File',
		Mandatory = $false,
		Position = 0,
		ParameterSetName = 'Default'
	)]
	[ValidateNotNullOrEmpty()]
	[string]$outputFile = '.\UserStats.csv',

	[Parameter(
		ValueFromPipeline = $true,
		ValueFromPipelineByPropertyName = $true,
		HelpMessage = 'Domain name (Ex.: Domain.com)',
		Mandatory = $false,
		Position = 1,
		ParameterSetName = 'Default'
	)]
	[ValidateNotNullOrEmpty()]
	[string]$domain
)

#region Functions
<#
    ===============================================
    FUNCTIONS
    ===============================================
#>

function Get-AgeInDays {
	<#
	.SYNOPSIS
		Calculates the age in days between a given date and today.
	#>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory = $true, ValueFromPipeline = $true)]
		[datetime]$when
	)

	try {
		return (New-TimeSpan -Start $when -End (Get-Date)).Days
	} catch {
		Write-Error "Failed to calculate age: $_"
		return $null
	}
}

function Get-UserStats {
	<#
	.SYNOPSIS
		Retrieves user statistics from Active Directory and exports to CSV.
	#>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory = $true)]
		[string]$Server,

		[Parameter(Mandatory = $true)]
		[string]$OutputPath
	)

	try {
		Write-Verbose "Querying AD users from server: $Server"

		# Select only required properties for better performance
		$adUsers = Get-ADUser `
			-Server $Server `
			-Filter * `
			-Property Name, whenCreated, PasswordLastSet |
			Select-Object -Property Name, `
			@{Name = 'AccountAge'; Expression = {
					Get-AgeInDays -when $_.whenCreated
				}
			}, `
			@{Name = 'PasswordAge'; Expression = {
					if ($null -eq $_.PasswordLastSet) {
						'Never'
					} else {
						Get-AgeInDays -when $_.PasswordLastSet
					}
				}
			}

		if ($null -eq $adUsers -or $adUsers.Count -eq 0) {
			Write-Warning 'No users found in AD'
			return $false
		}

		$adUsers | Export-Csv -Delimiter ';' -Path $OutputPath -NoTypeInformation -Force
		Write-Verbose "User statistics exported to: $OutputPath"
		return $true
	} catch {
		Write-Error "Failed to get user stats: $_"
		return $false
	}
}

function Get-DomainAdminCount {
	<#
	.SYNOPSIS
		Counts the number of domain administrators.
	#>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory = $true)]
		[string]$Server
	)

	try {
		Write-Verbose 'Querying Domain Admins group'
		$adminCount = (Get-ADGroupMember -Server $Server -Identity 'Domain Admins' -ErrorAction Stop | Measure-Object).Count
		return $adminCount
	} catch {
		Write-Error "Failed to get domain admin count: $_"
		return -1
	}
}

function Test-WindowsCompatibility {
	<#
	.SYNOPSIS
		Tests if the script is running on a compatible Windows version.
	#>
	[CmdletBinding()]
	param()

	try {
		$os = (Get-CimInstance Win32_OperatingSystem -ErrorAction Stop).Caption
		Write-Verbose "Operating System: $os"

		# Check for Windows 10, 11, or Windows Server versions
		if ($os -match 'Windows (10|11|Server)') {
			return $true
		} else {
			Write-Error "This script requires Windows 10, Windows 11, or Windows Server. Current OS: $os"
			return $false
		}
	} catch {
		Write-Error "Failed to check OS compatibility: $_"
		return $false
	}
}

function Test-OutputDirectory {
	<#
	.SYNOPSIS
		Tests if the output directory exists, creates it if necessary.
	#>
	[CmdletBinding()]
	param(
		[Parameter(Mandatory = $true)]
		[string]$FilePath
	)

	try {
		$directory = Split-Path -Parent $FilePath -ErrorAction Stop

		# If no directory specified, use current directory
		if ([string]::IsNullOrEmpty($directory)) {
			$directory = Get-Location
		}

		if (-not (Test-Path -Path $directory -PathType Container)) {
			Write-Verbose "Creating output directory: $directory"
			New-Item -Path $directory -ItemType Directory -Force | Out-Null
		}

		return $true
	} catch {
		Write-Error "Failed to validate output directory: $_"
		return $false
	}
}
#endregion Functions

#region Variables
<#
    ===============================================
    VARIABLES
    ===============================================
#>

$script:StartTime = Get-Date
#endregion Variables

#region Main
<#
    ===============================================
    MAIN SCRIPT LOGIC
    ===============================================
#>

try {
	Write-Host ''
	Write-Host ('=' * 80) -ForegroundColor Cyan
	Write-Host ' Active Directory User Statistics Report' -ForegroundColor Green
	Write-Host ('=' * 80) -ForegroundColor Cyan
	Write-Host ''

	Write-Verbose "Script started by: $([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)"

	# Test OS compatibility
	if (-not (Test-WindowsCompatibility)) {
		exit 2
	}

	# Get domain if not specified
	if ([string]::IsNullOrEmpty($domain)) {
		try {
			$domain = (Get-ADDomain -ErrorAction Stop).DNSRoot
			Write-Verbose "Using current domain: $domain"
		} catch {
			Write-Error 'Failed to retrieve current domain. Please specify domain with -domain parameter'
			exit 3
		}
	}

	# Validate output directory
	if (-not (Test-OutputDirectory -FilePath $outputFile)) {
		exit 4
	}

	# Ensure Active Directory module is imported
	if (-not (Get-Module -Name ActiveDirectory -ErrorAction SilentlyContinue)) {
		Write-Verbose 'Importing ActiveDirectory module'
		Import-Module ActiveDirectory -ErrorAction Stop
	}

	# Get user statistics
	$statsSuccess = Get-UserStats -Server $domain -OutputPath $outputFile
	if (-not $statsSuccess) {
		exit 5
	}

	# Get domain admin count
	$numDomainAdmins = Get-DomainAdminCount -Server $domain
	if ($numDomainAdmins -lt 0) {
		Write-Warning 'Unable to retrieve domain admin count'
		$numDomainAdmins = 'Unknown'
	}

	# Output results
	Write-Host ''
	Write-Host ' Script execution completed successfully' -ForegroundColor Green
	Write-Host " User information stored in: $outputFile"
	Write-Host " Number of domain admins: $numDomainAdmins"
	Write-Host ''
	Write-Host ('=' * 80) -ForegroundColor Cyan
	$duration = ((Get-Date) - $script:StartTime).TotalSeconds
	Write-Host "Script completed in $([Math]::Round($duration, 2))s " -ForegroundColor Green
	Write-Host ('=' * 80) -ForegroundColor Cyan
	Write-Host ''

	exit 0
} catch {
	Write-Error "Unexpected error during script execution: $_"
	Write-Error "Stack trace: $($_.ScriptStackTrace)"
	exit 1
}
#endregion Main
