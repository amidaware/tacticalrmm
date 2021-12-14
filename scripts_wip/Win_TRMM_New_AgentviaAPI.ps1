# From Chase 12/14/2021

function Create-TacticalRMMClient {
    
    param(
        $APIKey,
        $Customer,
        $Site,
        $URL
    )

    $Headers = @{
        "Content-Type" = "application/json"
        "X-API-KEY"    = $APIKey
    }

    $AllClients = Invoke-RestMethod -Uri "$URL/clients/" -Headers $Headers -Method GET -UseBasicParsing

    $ClientCheck = ($AllClients | Where name  -eq $Customer)

    if (!$ClientCheck) {

        $CreateClientBody = @"
    {
                "client": {"name": "$Customer"},
                "site": {"name": "Unspecified"},
                "custom_fields": []
    }
"@

        Invoke-RestMethod -URI "$URL/clients/" -Headers $Headers -Method Post -Body $CreateClientBody -UseBasicParsing | Out-Null

        $NewSearch = Invoke-RestMethod -Uri "$URL/clients/" -Headers $Headers -Method GET -UseBasicParsing
    
        $ClientID = ($NewSearch | Where { $_.name -eq $Customer }).id
        $ClientName = ($NewSearch | Where { $_.name -eq $Customer }).name
        $ClientSites = ($NewSearch | Where { $_.name -eq $Customer }).sites

    }
    else {
        $ClientID = $ClientCheck.ID
        $ClientName = $ClientCheck.Name
        $ClientSites = $ClientCheck.Sites
    }

    $SiteCheck = ($ClientSites | Where Name -eq $Site)

    if (!$SiteCheck) {

        $CreateSiteBody = @"
        {
                 "site": {"client": $ClientID, "name": "$Site"},
                "custom_fields": []
        }
"@

        Invoke-RestMethod -Uri "$URL/clients/sites/" -Headers $Headers -Method POST -Body $CreateSiteBody -UseBasicParsing | Out-Null

        $SiteNewSearch = (Invoke-RestMethod -Uri "$URL/clients/$ClientID/" -Headers $Headers -Method GET -UseBasicParsing).sites
        $SiteID = ($SiteNewSearch | Where name -eq $Site).id
    }

    
    
    $Output = @()
    $Output += New-Object -TypeName psobject -Property @{ClientID = "$ClientID"; SiteID = "$SiteID" }
    
    Write-Output $Output

}