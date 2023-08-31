@REM 不显示CMD窗口
if "%1"=="hide" goto CmdBegin
start mshta vbscript:createobject("wscript.shell").run("""%~0"" hide",0)(window.close)&&exit
:CmdBegin

@REM activate base & 
python ./AUTO_WALLPAPER_v2.py --source FengYun4BWallpaperProvider --interval 30 1> wallpaper_changer.log 2>&1