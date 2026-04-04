import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any

import source.core as core
import source.shared as s
from source.shared import MOD_DEF_FILE_NAME
from source.modificator import Property, log, Transfer, DEFINITION_CLASSES, initiate_comparison


@dataclass
class Mod:
    """ A formal data structure representing a Mod definition. """

    # TODO: mods should have be able to override more than one mod.
    transfer_type: str = ""
    name: str = ""
    game: str = ""
    launch: str = ""
    active: bool = False
    overrides: str = ""
    overrode_by: str = ""
    description: str = ""
    changes: Dict[str, Any] = field(default_factory=dict)
    directory: str = ""

    @classmethod
    def from_dict(cls, data: dict, directory: str = "") -> 'Mod':
        """ Creates a Mod instance from a loaded JSON dictionary. """
        return cls(
            transfer_type=data.get(Property.TRANSFER_TYPE, ""),
            name=data.get(Property.NAME, ""),
            game=data.get(Property.GAME, ""),
            launch=data.get(Property.LAUNCH, ""),
            active=data.get(Property.ACTIVE, False),
            overrides=data.get(Property.OVERRIDES, ""),
            overrode_by=data.get(Property.OVERRODE_BY, ""),
            description=data.get(Property.DESCRIPTION, ""),
            changes=data.get(Property.CHANGES, {}),
            directory=directory
        )

    def to_dict(self) -> dict:
        """ Converts the Mod instance back into a dictionary for JSON saving. """
        return ({
            Property.TRANSFER_TYPE: self.transfer_type,
            Property.NAME: self.name,
            Property.GAME: self.game,
            Property.LAUNCH: self.launch,
            Property.ACTIVE: self.active,
            Property.OVERRIDES: self.overrides,
            Property.OVERRODE_BY: self.overrode_by,
            Property.DESCRIPTION: self.description,
            Property.CHANGES: self.changes
        })

    @classmethod
    def create(cls, name: str, changes_source: str = '') -> 'Mod':
        """ Replaces mod_new and definition_write. Creates a new mod from scratch. """
        mod_directory = f'{core.library}/{name}'

        # 1. Create the physical folder
        if not os.path.isdir(mod_directory):
            os.mkdir(mod_directory)

        # 2. Run the comparison logic (assuming initiate_comparison is decoupled from UI)
        active, changes = initiate_comparison(mod_directory, changes_source=changes_source)

        # 3. Instantiate the dataclass
        new_mod = cls(
            name=name,
            transfer_type=DEFINITION_CLASSES[0],
            active=active,
            changes=changes,
            directory=mod_directory
        )

        # 4. Save to disk and return
        new_mod.save()
        return new_mod

    @classmethod
    def load(cls, mod_directory: str) -> 'Mod':
        """
        Loads a Mod definition directly from a folder path.
        """
        if not mod_directory:
            raise ValueError("A directory path must be provided to load a Mod.")

        if mod_directory in core.exceptions:
            raise s.InternalError("The provided path is defined as an exception.")

        file_path = f'{mod_directory}/{MOD_DEF_FILE_NAME}'

        if not os.path.isfile(file_path):
            raise s.InternalError(f'No definition found under {mod_directory}')

        with open(file_path, 'r') as definition_buffer:
            raw_dict = json.load(definition_buffer)
            # Use the internal from_dict constructor to build the object
            return cls.from_dict(raw_dict, directory=mod_directory)

    def save(self) -> None:
        """ Saves the mod's current state to its definition file. """
        if not self.directory:
            raise s.InternalError("Cannot save Mod: No directory specified.")

        file_path = f'{self.directory}/{MOD_DEF_FILE_NAME}'
        with open(file_path, 'w') as definition_buffer:
            json.dump(self.to_dict(), definition_buffer, indent=4)
        log(f'definition saved in {self.directory}')

    def edit(self, **kwargs) -> 'Mod':
        """ Updates the mod's attributes and saves the changes. """
        if Property.NAME in kwargs or "name" in kwargs:
            raise s.InternalError(
                "Cannot change mod name via simple edit. Use rename_mod() to safely update folders and links."
            )

        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                log(f"Warning: Attempted to edit unrecognized property '{key}'")

        self.save()
        return self

    # --- Wrapper methods for external routing ---

    def retrieve(self) -> bool:
        from source.modificator import mod_reverse
        try:
            mod_reverse(mod_object=self, transfer=Transfer.REMOVE)
            return True
        except s.InternalError:
            return False

    def attach(self) -> bool:
        from source.modificator import mod_attach
        try:
            mod_attach(self)
            return True
        except s.InternalError:
            try:
                mod_attach(mod_directory=f"{core.library}/{self.name}")
                return True
            except s.InternalError:
                return False

    def reload(self) -> bool:
        if self.retrieve():
            return self.attach()
        return False

    def extract(self) -> None:
        from source.modificator import mod_reverse
        mod_reverse(mod_object=self, transfer=Transfer.COPY)


def rename_mod(mod: Mod, new_name: str) -> Mod:
    """
    Safely renames a mod's physical directory and updates all dependent
    ancestor/heir links across the entire mod library.
    """
    if not mod.directory:
        raise s.InternalError('Cannot rename mod: Mod directory is unknown.')

    list_mods = [_ for _ in os.listdir(core.library) if _ not in core.exceptions]

    # 1. Prevent overwriting an existing mod
    if new_name in list_mods:
        raise s.InternalError(f'rename_mod error: name {new_name} is already in use')

    old_name = mod.name

    # 2. Update dependent mods across the library
    for sibling_name in list_mods:
        sibling_path = f'{core.library}/{sibling_name}'
        sibling_mod = Mod.load(sibling_path)

        # If the sibling depends on the old name, update it to the new name
        if sibling_mod.overrides == old_name:
            sibling_mod.edit(overrides=new_name)

        if sibling_mod.overrode_by == old_name:
            sibling_mod.edit(overrode_by=new_name)

    # 3. Rename the physical directory on disk
    new_directory = f"{'/'.join(mod.directory.split('/')[:-1])}/{new_name}"
    os.rename(src=mod.directory, dst=new_directory)

    # 4. Update the current Mod object's internal state and save it
    mod.name = new_name
    mod.directory = new_directory
    mod.save()

    return mod
