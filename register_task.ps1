# 매일 12:00에 claim.py 실행 (이미 담은 주는 스크립트가 알아서 건너뜀).
# PC가 꺼져 있었으면 켜진 뒤 바로 실행. 관리자 권한 불필요.
$root = $PSScriptRoot
$py   = Join-Path $root ".venv\Scripts\pythonw.exe"
$act  = New-ScheduledTaskAction -Execute $py -Argument "claim.py" -WorkingDirectory $root
$trig = New-ScheduledTaskTrigger -Daily -At 12:00
$set  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
Register-ScheduledTask -TaskName "Unity Free Asset" -Action $act -Trigger $trig -Settings $set -Force | Out-Null
Write-Host "등록 완료: 작업 스케줄러 > 'Unity Free Asset' (매일 12:00)"
