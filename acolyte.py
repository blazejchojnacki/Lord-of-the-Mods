import source.modificator as modificator
import source.editor as editor
import source.constructor as constructor

# print(modificator.hash_file(r"O:\Lord-of-the-Mods\_LIBRARY\RotWK-test\RotWK\Readme.txt"))

# result = editor.spot_duplicates_in_file(
# r"O:\Lord-of-the-Mods\_LIBRARY\RotWK-test\RotWK\data\ini\isengardfactionarrows_modified.ini")

# result = editor.spot_duplicates_in_directory(
#     r"O:\Lord-of-the-Mods\_LIBRARY\RotWK-test\RotWK\data\ini\isengardfactionarrows_modified.ini",
#     r"O:\Lord-of-the-Mods\_LIBRARY\RotWK-test\RotWK\data\ini")

result, delimiters = constructor.load_file(
    r"O:\Lord-of-the-Mods\_LIBRARY\RotWK-test\RotWK\data\ini\isengardfactionarrows_modified.ini")

print(result)
