# VS Code PowerShell 配置文件
# 位置: ~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1

# 设置输出编码为UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'

# VS Code Shell Integration
if ($env:TERM_PROGRAM -eq "vscode") {
    # 在这里可以添加VS Code特定的配置
    Write-Host "VS Code终端已启动" -ForegroundColor Green
}

# 如果你想禁用Shell Integration提示
# $env:VSCODE_SHELL_INTEGRATION = $null
