@echo off
for /f "tokens=1-4 delims=/ " %%a in ("%date% %time%") do (
    set msg=Greg-commit %%a-%%b-%%c_%%d
)
git add .
git commit -m "%msg%"
git push