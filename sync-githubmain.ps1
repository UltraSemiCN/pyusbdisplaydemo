# Sync GitLab master content onto GitHub githubmain as a linear child commit.
# Does NOT use --orphan (avoids unrelated-history roots).
# Usage:
#   .\sync-githubmain.ps1
#   .\sync-githubmain.ps1 -ForcePush   # only if remote was rewritten

[CmdletBinding()]
param(
    [switch]$ForcePush
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Assert-CleanWorktree {
    $status = & git.exe status --porcelain
    if ($status) {
        throw "Working tree is not clean. Commit or stash changes first."
    }
}

function Get-Tree([string]$ref) {
    return (& git.exe rev-parse "$ref^{tree}").Trim()
}

Assert-CleanWorktree

Write-Host "==> Fetch remotes"
& git.exe fetch gitlab
& git.exe fetch github --prune

$startBranch = (& git.exe branch --show-current).Trim()

Write-Host "==> Update local master from gitlab/master"
& git.exe checkout master
& git.exe merge --ff-only gitlab/master
if ($LASTEXITCODE -ne 0) {
    throw "master cannot fast-forward to gitlab/master. Resolve locally first."
}

if (-not (& git.exe rev-parse --verify githubmain 2>$null)) {
    throw "Local branch githubmain missing. Recreate it before syncing."
}

& git.exe checkout githubmain
& git.exe merge --ff-only github/githubmain 2>$null | Out-Null

$masterTree = Get-Tree "master"
$githubTree = Get-Tree "githubmain"
$masterShort = (& git.exe rev-parse --short master).Trim()

if ($masterTree -eq $githubTree) {
    Write-Host "OK: githubmain already matches master tree ($masterShort). Nothing to push."
    & git.exe checkout $startBranch
    if ($LASTEXITCODE -ne 0) { & git.exe checkout master }
    exit 0
}

Write-Host "==> Create linear sync commit (parent = current githubmain)"
$parent = (& git.exe rev-parse githubmain).Trim()
$msg = "Sync from master $masterShort"
$commit = (& git.exe commit-tree $masterTree "-p" $parent "-m" $msg).Trim()
if (-not $commit) {
    throw "git commit-tree failed"
}
& git.exe branch -f githubmain $commit
Write-Host ("New tip: " + $commit)

Write-Host "==> Push github githubmain"
if ($ForcePush) {
    & git.exe push github githubmain --force
} else {
    & git.exe push github githubmain
}
if ($LASTEXITCODE -ne 0) {
    throw "Push failed. If remote history diverged, re-run with -ForcePush after reviewing."
}

Write-Host "==> Verify"
& git.exe fetch github
$diff = & git.exe diff --stat master github/githubmain
if ($diff) {
    Write-Host $diff
    throw "master and github/githubmain trees still differ"
}
Write-Host ("githubmain commits: " + (& git.exe rev-list --count github/githubmain).Trim())
Write-Host "OK: synced and pushed."

& git.exe checkout master
if ($startBranch -and $startBranch -ne "master") {
    & git.exe checkout $startBranch 2>$null | Out-Null
}
