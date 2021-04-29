$root="c:\users"
$users=get-childitem -path $root -exclude administrator, public
foreach ($user in $users)
 {
 $folder= join-path -path $user -childpath "downloads\*"
 Get-childitem $folder -recurse | remove-item -force
 }