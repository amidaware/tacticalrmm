<#
.Synopsis
   Detect if object exists and gives error
.DESCRIPTION
   Long description
.EXAMPLE
   Example of how to use this cmdlet
.EXAMPLE
   Another example of how to use this cmdlet
#>

If ((Test-Path -Path "C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Tactical RMM Agent.lnk" -PathType Leaf) -eq $false ) {
    
    Write-Output "No Shortcut"
    exit 0

}
Else {

    Write-Output 'Shortcut Exists'
    exit 1
} 

Exit $LASTEXITCODE

# function Verb-Noun
# {
#     [CmdletBinding()]
#     [Alias()]
#     [OutputType([int])]
#     Param
#     (
#         # Param1 help description
#         [Parameter(Mandatory=$true,
#                    ValueFromPipelineByPropertyName=$true,
#                    Position=0)]
#         $Param1,

#         # Param2 help description
#         [int]
#         $Param2
#     )

#     Begin
#     {
#     }
#     Process
#     {
#     }
#     End
#     {
#     }
# }