# Lord-of-the-Mods
# Manual Tests:

## big_unpack
CMD x64 (venv)

```CMD
set PYTHONPATH=%CD%\build\src\cppy_bridge
```

```CMD
python scripts\big_unpack.py "L:\Lord-of-the-Mods\tests\big-example\ini.big" -o "L:\Lord-of-the-Mods\tests\big-example\extracted_ini"
```

## big_pack
CMD x64 (venv)

```CMD
set PYTHONPATH=%CD%\build\src\cppy_bridge
```

```CMD
python scripts\big_pack.py "L:\Lord-of-the-Mods\tests\big-example\extracted_ini" -o "L:\Lord-of-the-Mods\tests\big-example\repacked_ini.big"
```


