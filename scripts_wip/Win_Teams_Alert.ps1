<#
Microsoft Teams notifications
Submitted by Insane Technologies / David Rudduck
requires
- agent {{agent.hostname}}
- client {{client.name}}
- site {{site.name}}
- user {{agent.logged_in_user}}
- reboot {{agent.needs_reboot}}
- patches {{agent.patches_last_installed}}
- alert_time {{alert.alert_time}}
- message {{alert.message}}
- severity {{alert.severity}}
#>
param (
  [string] $agent,
  [string] $client,
  [string] $site,
  [string] $user,
  [string] $reboot,
  [string] $patches,
  [string] $time,
  [string] $message,
  [string] $severity
)

$webhookurl = 'ADDYOURMSTEAMSWEBHOOKURLHERE'

if($severity -eq "error"){
  $colour = 'ff0000'
}
if($severity -eq "warning"){
  $color = 'ffa500'
}
if($severity -eq "info"){
  $colour = 'ffff00'
}

$msteams_payload = '{"@context": "https://schema.org/extensions", "@type": "MessageCard", "summary": "TacticalRMM Alert", "themeColor": "' + $colour +'", '
$msteams_payload = $msteams_payload + '"text": "'

if($time) {
  $msteams_payload = $msteams_payload + '<b>Alert Time:</b> ' + $time +'<br>'
}

$msteams_payload = $msteams_payload + '<b>Client:</b> ' + $client +'<br>'
$msteams_payload = $msteams_payload + '<b>Site:</b> ' + $site +'<br>'
$msteams_payload = $msteams_payload + '<b>Device:</b> ' + $agent +'<br>'
if($user) {
  $msteams_payload = $msteams_payload + '<b>User:</b> ' + $user +'<br>'
}
if($reboot) {
  $msteams_payload = $msteams_payload + '<b>Device has pending reboot</b><br>'
}
if($patches) {
  $msteams_payload = $msteams_payload + '<b>Patches were last applied:</b> ' + $patches +'<br>'
}
$msteams_payload = $msteams_payload + $message + '"}'

# Write-Output $msteams_payload
Invoke-RestMethod -Method post -ContentType 'Application/Json' -Body $msteams_payload -Uri $webhookurl
