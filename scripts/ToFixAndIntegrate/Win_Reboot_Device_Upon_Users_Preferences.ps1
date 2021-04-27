#Reboot Device Upon The User’s Preferences: Wait, reboot at 18:00 or reboot now. The prompt mesage and colors can be changed upon your choice


$days = 7
$system = Get-WmiObject win32_operatingsystem

if($system.ConvertToDateTime($system.LastBootUpTime) -lt (Get-Date).AddDays(-$days)){
    #---------------------------------------------- 
#region Import Assemblies 
#---------------------------------------------- 
[void][Reflection.Assembly]::Load('System.Windows.Forms, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089') 
[void][Reflection.Assembly]::Load('System.Data, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089') 
[void][Reflection.Assembly]::Load('System.Drawing, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a') 
#endregion Import Assemblies 
 
 
#Define a Param block to use custom parameters in the project 
#Param ($CustomParameter) 
 
function Main { 
<# 
    .SYNOPSIS 
        The Main function starts the project application. 
     
    .PARAMETER Commandline 
        $Commandline contains the complete argument string passed to the script packager executable. 
     
    .NOTES 
        Use this function to initialize your script and to call GUI forms. 
         
    .NOTES 
        To get the console output in the Packager (Forms Engine) use:  
        $ConsoleOutput (Type: System.Collections.ArrayList) 
#> 
    Param ([String]$Commandline) 
         
    #-------------------------------------------------------------------------- 
    #TODO: Add initialization script here (Load modules and check requirements) 
     
     
    #-------------------------------------------------------------------------- 
     
    if((Call-MainForm_psf) -eq 'OK') 
    { 
         
    } 
     
    $global:ExitCode = 0 #Set the exit code for the Packager 
} 
 
 
 
 
 
 
 
#endregion Source: Startup.pss 
 
#region Source: MainForm.psf 
function Call-MainForm_psf 
{ 
 
    #---------------------------------------------- 
    #region Import the Assemblies 
    #---------------------------------------------- 
    [void][reflection.assembly]::Load('System.Windows.Forms, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089') 
    [void][reflection.assembly]::Load('System.Data, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089') 
    [void][reflection.assembly]::Load('System.Drawing, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b03f5f7f11d50a3a') 
    #endregion Import Assemblies 
 
    #---------------------------------------------- 
    #region Generated Form Objects 
    #---------------------------------------------- 
    [System.Windows.Forms.Application]::EnableVisualStyles() 
    $MainForm = New-Object 'System.Windows.Forms.Form' 
    $panel2 = New-Object 'System.Windows.Forms.Panel' 
    $ButtonCancel = New-Object 'System.Windows.Forms.Button' 
    $ButtonSchedule = New-Object 'System.Windows.Forms.Button' 
    $ButtonRestartNow = New-Object 'System.Windows.Forms.Button' 
    $panel1 = New-Object 'System.Windows.Forms.Panel' 
    $labelITSystemsMaintenance = New-Object 'System.Windows.Forms.Label' 
    $labelSecondsLeftToRestart = New-Object 'System.Windows.Forms.Label' 
    $labelTime = New-Object 'System.Windows.Forms.Label' 
    $labelInOrderToApplySecuri = New-Object 'System.Windows.Forms.Label' 
    $timerUpdate = New-Object 'System.Windows.Forms.Timer' 
    $InitialFormWindowState = New-Object 'System.Windows.Forms.FormWindowState' 
    #endregion Generated Form Objects 
 
    #---------------------------------------------- 
    # User Generated Script 
    #---------------------------------------------- 
    $TotalTime = 1500 #in seconds 
     
    $MainForm_Load={ 
        #TODO: Initialize Form Controls here 
        $labelTime.Text = "{0:D2}" -f $TotalTime #$TotalTime 
        #Add TotalTime to current time 
        $script:StartTime = (Get-Date).AddSeconds($TotalTime) 
        #Start the timer 
        $timerUpdate.Start() 
    } 
     
     
    $timerUpdate_Tick={ 
        # Define countdown timer 
        [TimeSpan]$span = $script:StartTime - (Get-Date) 
        #Update the display 
        $labelTime.Text = "{0:N0}" -f $span.TotalSeconds 
        $timerUpdate.Start() 
        if ($span.TotalSeconds -le 0) 
        { 
            $timerUpdate.Stop() 
            Restart-Computer -Force 
        } 
         
    } 
     
    $ButtonRestartNow_Click = { 
        # Restart the computer immediately 
        Restart-Computer -Force 
    } 
     
    $ButtonSchedule_Click={ 
        # Schedule restart for 6pm
        if(Get-ScheduledTask -TaskName "auto shutdown my computer" -ErrorAction SilentlyContinue){Get-ScheduledTask -TaskName "auto shutdown my computer" | Unregister-ScheduledTask -Confirm:$false}
        if((schtasks /create /sc once /tn "auto shutdown my computer" /tr "shutdown /r /d p:1:1 /c 'Initiating reboot since the device has not been rebooted for 7 days'" /st 18:00) -like "*Success*"){
            $SetT=Get-ScheduledTask -TaskName "auto shutdown my computer"
            $SetT.Triggers[0].EndBoundary=[DateTime]::Now.Date.ToString("yyyy-MM-dd")+"T"+"19:00:00"
            $SetT.Settings.DeleteExpiredTaskAfter ='PT0S'
            Set-ScheduledTask -InputObject $SetT
        }
        $MainForm.Close() 
    } 
     
    $ButtonCancel_Click={ 
        #TODO: Place custom script here 
        $MainForm.Close() 
    } 
     
    $labelITSystemsMaintenance_Click={ 
        #TODO: Place custom script here 
         
    } 
     
    $panel2_Paint=[System.Windows.Forms.PaintEventHandler]{ 
    #Event Argument: $_ = [System.Windows.Forms.PaintEventArgs] 
        #TODO: Place custom script here 
         
    } 
     
    $labelTime_Click={ 
        #TODO: Place custom script here 
         
    } 
        # --End User Generated Script-- 
    #---------------------------------------------- 
    #region Generated Events 
    #---------------------------------------------- 
     
    $Form_StateCorrection_Load= 
    { 
        #Correct the initial state of the form to prevent the .Net maximized form issue 
        $MainForm.WindowState = $InitialFormWindowState 
    } 
     
    $Form_StoreValues_Closing= 
    { 
        #Store the control values 
    } 
 
     
    $Form_Cleanup_FormClosed= 
    { 
        #Remove all event handlers from the controls 
        try 
        { 
            $ButtonCancel.remove_Click($buttonCancel_Click) 
            $ButtonSchedule.remove_Click($ButtonSchedule_Click) 
            $ButtonRestartNow.remove_Click($ButtonRestartNow_Click) 
            $panel2.remove_Paint($panel2_Paint) 
            $labelITSystemsMaintenance.remove_Click($labelITSystemsMaintenance_Click) 
            $labelTime.remove_Click($labelTime_Click) 
            $MainForm.remove_Load($MainForm_Load) 
            $timerUpdate.remove_Tick($timerUpdate_Tick) 
            $MainForm.remove_Load($Form_StateCorrection_Load) 
            $MainForm.remove_Closing($Form_StoreValues_Closing) 
            $MainForm.remove_FormClosed($Form_Cleanup_FormClosed) 
        } 
        catch [Exception] 
        { } 
    } 
    #endregion Generated Events 
 
    #---------------------------------------------- 
    #region Generated Form Code 
    #---------------------------------------------- 
    $MainForm.SuspendLayout() 
    $panel2.SuspendLayout() 
    $panel1.SuspendLayout() 
    # 
    # MainForm 
    # 
    $MainForm.Controls.Add($panel2) 
    $MainForm.Controls.Add($panel1) 
    $MainForm.Controls.Add($labelSecondsLeftToRestart) 
    $MainForm.Controls.Add($labelTime) 
    $MainForm.Controls.Add($labelInOrderToApplySecuri) 
    $MainForm.AutoScaleDimensions = '6, 13' 
    $MainForm.AutoScaleMode = 'Font' 
    $MainForm.BackColor = 'White' 
    $MainForm.ClientSize = '373, 279' 
    $MainForm.MaximizeBox = $False 
    $MainForm.MinimizeBox = $False 
    $MainForm.Name = 'MainForm' 
    $MainForm.ShowIcon = $False 
    $MainForm.ShowInTaskbar = $False 
    $MainForm.StartPosition = 'CenterScreen' 
    $MainForm.Text = 'MSP Name' 
    $MainForm.TopMost = $True 
    $MainForm.add_Load($MainForm_Load) 
    # 
    # panel2 
    # 
    $panel2.Controls.Add($ButtonCancel) 
    $panel2.Controls.Add($ButtonSchedule) 
    $panel2.Controls.Add($ButtonRestartNow) 
    $panel2.BackColor = 'ScrollBar' 
    $panel2.Location = '0, 205' 
    $panel2.Name = 'panel2' 
    $panel2.Size = '378, 80' 
    $panel2.TabIndex = 9 
    $panel2.add_Paint($panel2_Paint) 
    # 
    # ButtonCancel 
    # 
    $ButtonCancel.Location = '250, 17' 
    $ButtonCancel.Name = 'ButtonCancel' 
    $ButtonCancel.Size = '77, 45' 
    $ButtonCancel.TabIndex = 7 
    $ButtonCancel.Text = 'Wait' 
    $ButtonCancel.UseVisualStyleBackColor = $True 
    $ButtonCancel.add_Click($buttonCancel_Click) 
    # 
    # ButtonSchedule 
    # 
    $ButtonSchedule.Font = 'Microsoft Sans Serif, 8.25pt, style=Bold' 
    $ButtonSchedule.Location = '139, 17' 
    $ButtonSchedule.Name = 'ButtonSchedule' 
    $ButtonSchedule.Size = '105, 45' 
    $ButtonSchedule.TabIndex = 6 
    $ButtonSchedule.Text = 'Reboot at 18:00' 
    $ButtonSchedule.UseVisualStyleBackColor = $True 
    $ButtonSchedule.add_Click($ButtonSchedule_Click) 
    # 
    # ButtonRestartNow 
    # 
    $ButtonRestartNow.Font = 'Microsoft Sans Serif, 8.25pt, style=Bold' 
    $ButtonRestartNow.ForeColor = 'DarkRed' 
    $ButtonRestartNow.Location = '42, 17' 
    $ButtonRestartNow.Name = 'ButtonRestartNow' 
    $ButtonRestartNow.Size = '91, 45' 
    $ButtonRestartNow.TabIndex = 0 
    $ButtonRestartNow.Text = 'Reboot' 
    $ButtonRestartNow.UseVisualStyleBackColor = $True 
    $ButtonRestartNow.add_Click($ButtonRestartNow_Click) 
    # 
    # panel1 
    # 
    $panel1.Controls.Add($labelITSystemsMaintenance) 
    $panel1.BackColor = '22, 54, 36' 
    $panel1.Location = '0, 0' 
    $panel1.Name = 'panel1' 
    $panel1.Size = '375, 67' 
    $panel1.TabIndex = 8 
    # 
    # labelITSystemsMaintenance 
    # 
    $labelITSystemsMaintenance.Font = 'Microsoft Sans Serif, 14.25pt' 
    $labelITSystemsMaintenance.ForeColor = 'White' 
    $labelITSystemsMaintenance.Location = '11, 18' 
    $labelITSystemsMaintenance.Name = 'labelITSystemsMaintenance' 
    $labelITSystemsMaintenance.Size = '269, 23' 
    $labelITSystemsMaintenance.TabIndex = 1 
    $labelITSystemsMaintenance.Text = 'MSP Name' 
    $labelITSystemsMaintenance.TextAlign = 'MiddleLeft' 
    $labelITSystemsMaintenance.add_Click($labelITSystemsMaintenance_Click) 
    # 
    # labelSecondsLeftToRestart 
    # 
    $labelSecondsLeftToRestart.AutoSize = $True 
    $labelSecondsLeftToRestart.Font = 'Microsoft Sans Serif, 9pt, style=Bold' 
    $labelSecondsLeftToRestart.Location = '87, 176' 
    $labelSecondsLeftToRestart.Name = 'labelSecondsLeftToRestart' 
    $labelSecondsLeftToRestart.Size = '155, 15' 
    $labelSecondsLeftToRestart.TabIndex = 5 
    $labelSecondsLeftToRestart.Text = 'Seconds to reboot :' 
    # 
    # labelTime 
    # 
    $labelTime.AutoSize = $True 
    $labelTime.Font = 'Microsoft Sans Serif, 9pt, style=Bold' 
    $labelTime.ForeColor = '192, 0, 0' 
    $labelTime.Location = '237, 176' 
    $labelTime.Name = 'labelTime' 
    $labelTime.Size = '43, 15' 
    $labelTime.TabIndex = 3 
    $labelTime.Text = '00:60' 
    $labelTime.TextAlign = 'MiddleCenter' 
    $labelTime.add_Click($labelTime_Click) 
    # 
    # labelInOrderToApplySecuri 
    # 
    $labelInOrderToApplySecuri.Font = 'Microsoft Sans Serif, 9pt' 
    $labelInOrderToApplySecuri.Location = '12, 84' 
    $labelInOrderToApplySecuri.Name = 'labelInOrderToApplySecuri' 
    $labelInOrderToApplySecuri.Size = '350, 83' 
    $labelInOrderToApplySecuri.TabIndex = 2 
    $labelInOrderToApplySecuri.Text = 'Every 7 days your PC should be restarted for maintenance and updates.

If this does not fit, you can press wait or restart at. 6:00 p.m.' 
    # 
    # timerUpdate 
    # 
    $timerUpdate.add_Tick($timerUpdate_Tick) 
    $panel1.ResumeLayout() 
    $panel2.ResumeLayout() 
    $MainForm.ResumeLayout() 
    #endregion Generated Form Code 
 
    #---------------------------------------------- 
 
    #Save the initial state of the form 
    $InitialFormWindowState = $MainForm.WindowState 
    #Init the OnLoad event to correct the initial state of the form 
    $MainForm.add_Load($Form_StateCorrection_Load) 
    #Clean up the control events 
    $MainForm.add_FormClosed($Form_Cleanup_FormClosed) 
    #Store the control values when form is closing 
    $MainForm.add_Closing($Form_StoreValues_Closing) 
    #Show the Form 
    return $MainForm.ShowDialog() 
 
} 
#endregion Source: MainForm.psf 
 
#Start the application 
Main ($CommandLine) 
}else{
    Write-Host "Machine was rebooted less than $days days ago"

}