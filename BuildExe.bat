set path_to_python_virtual_environment=D:\venv3
IF EXIST dist\ (rd /s /q dist)
IF EXIST build\ (rd /s /q build)
IF EXIST file_copy_tool.spec (del /s /q file_copy_tool.spec)
%path_to_python_virtual_environment%\Scripts\pip install -r requirements.txt
pyinstaller --onefile --hiddenimport pandas --hiddenimport babel.numbers -p %path_to_python_virtual_environment%\Lib\site-packages .\file_copy_tool.py