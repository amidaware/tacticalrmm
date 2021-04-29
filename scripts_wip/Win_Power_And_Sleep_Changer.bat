@echo off

REM Power and Sleep Settings Script

REM ac = Plugged in
REM dc = Running on battery
REM Number at the end of each command is in minutes, 0 means never

REM Standby = Sleep
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0

REM Monitor = Monitor
powercfg /change monitor-timeout-ac 0
powercfg /change monitor-timeout-dc 0

REM Hibernate = Hibernate, only used on machines that have hibernate enabled, most use sleep now
powercfg /change hibernate-timeout-ac 0
powercfg /change hibernate-timeout-dc 0