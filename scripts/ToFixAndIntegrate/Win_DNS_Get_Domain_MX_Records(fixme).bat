@echo off
rem Get's the MX records for a domain
rem To use a variable instaed of having to put the domain into the script
rem change line 6 to `set domain="\{[DOMAIN]\}" (remove backslashes)

set domain="PUT DOMAIN TO CHECK HERE"

nslookup -type=mx %doamin%