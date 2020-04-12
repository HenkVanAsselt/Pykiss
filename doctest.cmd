@echo off

cd kiss

set filename=doctestfiles.txt

grep -l ">>>" *.py > %filename%
echo *************************
echo Files with ">>>" doctest
type %filename%
echo *************************

FOR /F %x IN (%filename) DO (
	echo "%x"
	IF "%x" == "tracetool.py" (
		ECHO Skipping %x
	) ELSE (	
		echo Doctest %x
		python -m doctest %x
	)
)

cd ..
