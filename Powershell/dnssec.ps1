param(
    [string]$zone,
    [string]$do,
    [int]$verbose
)


#
#    If you know what you're doing, feel free to add any changes for personal/internal use
#    Notify the developer in case of any major changes or issues arises.
#
#    https://github.com/Torxed/Scripts
#


switch -Regex ($verbose) {
    [0] {
        "
        == ================================================================================= ==
        == Script by: Anton Hvornum (anton.hvornum@combitech.se - https://github.com/Torxed) ==
        == - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - ==

         Usage:

          .\dnssec.ps1
             This Will list all your zones and create a filter-file .\dnszones.txt which
             you can modify to your liking, this filter-file will be used if no
             -zone <name> is specified, so the filter-file is instead of the -zone parameter

          .\dnssec.ps1 -do [sign|unsign|resign] [-zone <name>] [-verbose <0|1|2>]
             This will either sign, unsign or resign a -zone <name> or all the zones
             listed in the filter-file 'dnszones.txt'.

          -do sign
             if called upon a already signed zone, resign will be initated in its place
          -do unsign
             will remove all associaced certificates to the zone/zones being unsigned
          -do resign
             will remove ONLY the ZSK for the associated zone/zones being resigned and
             a new ZSK will be generated in its place for resigning.


          -verbose 0|1|2
             where:
                0 (default) - Outputs everything
                1 - Everything except the help
                2 - Mutes everything except errors
        "
    }
}

function creatednsfilter {
    $zones = Get-DnsServerZone -ComputerName 127.0.0.1
    foreach ($zone in $zones) {
        # Write zones who: is NOT a system record, NOT a PTR record and is NOT TrustAnchors
        if ($zone.IsAutoCreated -eq $false -and $zone.IsReverseLookupZone -eq $false -and $zone.ZoneName -ne "TrustAnchors") {
            $zone.ZoneName >> ".\dnszones.txt"
        }
    }
}

$dns_entries = Get-WmiObject -namespace "root\MicrosoftDNS" -class MicrosoftDNS_Domain -ComputerName 127.0.0.1
if (Test-Path ".\dnszones.txt") {
    $zones = Get-Content .\dnszones.txt
} else {
    creatednsfilter
    $zones = Get-Content .\dnszones.txt
}

if ($do.Length -eq 0) {
    if ($zone.Length -eq 0) {
        if ($verbose -le 1){"This is all your zones (filtered by dnszones.txt)"}
    } else {
        if ($verbose -le 1) {"Verifying '" + $zone + "':"}
    }
}


function keys {
    param(
        [string]$zonename
    )
    
    ## List all the keys for the given zone
    $keys = Get-DnsServerSigningKey -ZoneName $zonename
    foreach ($key in $keys) {
        $key
    }
}

function refreshroot {
    if ($verbose -le 1){"root. <- Retriving root trust achor (This might take 30sec)"}
    
    $job = Start-Job { dnscmd /RetrieveRootTrustAnchors /f }
    Wait-Job $job -Timeout 30 #Timeout after 30 sec
    Stop-Job $job 
    $res = Receive-Job $job
    Remove-Job $job

    return $job.State
}

function sign {
    param(
        [string]$zonename
    )
    $issigned = Get-DnsServerZone -Name $zonename
    if ($issigned.IsSigned) {
        resign($zonename)
    } else {

        ## If using a Active Directory domain, transfer the kay-master role to this server
        # Reset-DnsServerZoneKeyMasterRole  –ZoneName $zonename -SeizeRole -Force 

        ## Use NSEC3 for proper denial of existance and security
        Set-DnsServerDnsSecZoneSetting -ZoneName $zonename -ComputerName 127.0.0.1 -DenialOfExistence NSec3 -DistributeTrustAnchor DnsKey -DSRecordGenerationAlgorithm Sha256 -EnableRfc5011KeyRollover $False -NSec3HashAlgorithm RsaSha1

        if ($verbose -le 1){$zonename + " <- Creating keys"}
        ## Add a KSK (Key Signing Key)
        Add-DnsServerSigningKey -ZoneName $zonename -ComputerName 127.0.0.1 -CryptoAlgorithm RsaSha256 -Type KeySigningKey 
 
        ## Add a ZSK (Zone Signing Key)
        Add-DnsServerSigningKey -ZoneName $zonename -ComputerName 127.0.0.1 -CryptoAlgorithm RsaSha256 -Type ZoneSigningKey
 
        if ($verbose -le 1){$zonename + " <- Signing"}
        ## Initiate a sign of zone
        Invoke-DnsServerZoneSign -ZoneName $zonename -Force
    }
}

function resign {
    param(
        [string]$zonename
    )
    $issigned = Get-DnsServerZone -Name $zonename
    if ($issigned.IsSigned) {
        if ($verbose -le 1){$zonename + " <- Unsigning for resign"}
        Invoke-DnsServerZoneUnsign -ZoneName $zonename -ComputerName 127.0.0.1 -Force

        ## Grab all current keys (incl active ones) and the coresponding certs
        $keys = Get-DnsServerSigningKey -ZoneName $zonename
        $store = new-object system.security.cryptography.x509certificates.x509Store 'MS-DNSSEC', 'LocalMachine'
        $store.Open('ReadWrite')
        $certs = @(dir cert:\LocalMachine\MS-DNSSEC)

        if ($verbose -le 1){$zonename + " <- Removing old ZSK (cleaning up)"}
        foreach ($key in $keys) {
            if ($key.KeyType -eq "ZoneSigningKey") {
                Remove-DnsServerSigningKey -KeyId $key.KeyId -ZoneName $zonename -Force
            }
        }
        foreach ($cert in $certs) {
            $certname = $cert.FriendlyName
            ## Important: Since the certificate store doesn't really handle
            ## -zone we check the friendly name for the zonename so we don't
            ## remove certificates belonging to another zone.
            ## We also check to make sure that it's a ZSK and not a KSK we're removing.
            if($certname.EndsWith("ZSK") -and $certname.StartsWIth($zonename)) {
                $store.Remove($cert)
            }
        }
        $store.close()
    
        if ($verbose -le 1){$zonename + " <- Creating new ZSK"}
        #Add a new ZSK 
        Add-DnsServerSigningKey -ZoneName $zonename -ComputerName 127.0.0.1 -CryptoAlgorithm RsaSha256 -Type ZoneSigningKey

        if ($verbose -le 1){$zonename + " <- Re-signing"}
        #Resign the zone with the newly added key 
        Invoke-DnsServerZoneSign -ZoneName $zonename -Force
    } else {
        if ($verbose -le 1){$zonename + " <- Zone already signed (call -do sign instead)"}
    }
}

function unsign {
    param(
        [string]$zonename
    )
    $issigned = Get-DnsServerZone -Name $zonename
    if ($issigned.IsSigned) {
        if ($verbose -le 1){$zonename + " <- Unsigning"}

        ## Unsign the zone
        Invoke-DnsServerZoneUnsign -ZoneName $zonename -ComputerName 127.0.0.1 -Force
    }

    if ($verbose -le 1){$zonename + " <- Removing keys"}
    ## Delete all keys and the coresponding certs
    $keys = Get-DnsServerSigningKey -ZoneName $zonename
    $store = new-object system.security.cryptography.x509certificates.x509Store 'MS-DNSSEC', 'LocalMachine'
    $store.Open('ReadWrite')
    $certs = @(dir cert:\LocalMachine\MS-DNSSEC)
    foreach ($key in $keys) {
        Remove-DnsServerSigningKey -KeyId $key.KeyId -ZoneName $zonename -Force
    }
    foreach ($cert in $certs) {
        $certname = $cert.FriendlyName
        ## Important: Since the certificate store doesn't really handle
        ## -zone we check the friendly name for the zonename so we don't
        ## remove certificates belonging to another zone.
        if($certname.StartsWIth($zonename)) {
            $store.Remove($cert)
        }
    }
    $store.close()
}

foreach ($dnsrecord in $dns_entries) {
    $zone_name = $dnsrecord.Name
    if ($zone.Length -gt 0 -and $zone_name -eq $zone) {
        if ($do -eq "sign") {
            sign($zone_name)
        } elseif ($do -eq "resign") {
            resign($zone_name)
        } elseif ($do -eq "unsign") {
            unsign($zone_name)
        } elseif ($do -eq "root") {
            $output = refreshroot
            if ($output -notcontains "Completed") {
                "[ERROR]  -!- Failed to retrieve the root CA. Run: 'dnscmd /RetrieveRootTrustAnchors' manually -!-"
            }
        } elseif ($do -eq "keys") {
            keys($zone_name)
        } else {
            $issigned = Get-DnsServerZone -Name $dnsrecord.Name
            if ($issigned.IsSigned) {
                if ($verbose -le 1){$dnsrecord.Name + " [Signed]"}
            } else {
                if ($verbose -le 1){$dnsrecord.Name + " [Unsigned]"}
            }
        }
    } elseif ($zone.Length -eq 0) {
        if ($zones –contains $zone_name) {
            if ($do -eq "sign") {
                sign($zone_name)
            } elseif ($do -eq "resign") {
                resign($zone_name)
            } elseif ($do -eq "unsign") {
                unsign($zone_name)
            } elseif ($do -eq "root") {
                $output = refreshroot
                if ($output -notcontains "Completed") {
                    "[ERROR]  -!- Failed to retrieve the root CA. Run: 'dnscmd /RetrieveRootTrustAnchors' manually -!-"
                }
            } elseif ($do -eq "keys") {
                keys($zone_name)
            } else {
                $issigned = Get-DnsServerZone -Name $dnsrecord.Name
                if ($issigned.IsSigned) {
                    if ($verbose -le 1){$dnsrecord.Name + " [Signed]"}
                } else {
                    if ($verbose -le 1){$dnsrecord.Name + " [Unsigned]"}
                }
            }
        }
    }
}
