# Switch the live profile README between design variants kept under designs/.
# Usage:  .\switch-design.ps1 badges   (classic badge-wall design)
#         .\switch-design.ps1 cards    (SVG card system, portfolio-brand design)
# Then review, and: git add -A; git commit -m "Switch README design to <name>"; git push
param(
    [Parameter(Mandatory)]
    [ValidateSet('badges', 'cards')]
    [string]$Design
)

$root = $PSScriptRoot
Copy-Item "$root\designs\$Design\README.md" "$root\README.md" -Force
Remove-Item "$root\assets\*" -Force
Copy-Item "$root\designs\$Design\assets\*" "$root\assets\" -Force

Write-Host "Switched README to '$Design' ($((Get-ChildItem "$root\assets").Count) assets). Commit and push to publish."
