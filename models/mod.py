import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

import source.core as core
import source.shared as s
from source.shared import MOD_DEF_FILE_NAME
from source.constants import Property, log, DEFINITION_CLASSES, Transfer, Change
from source.modificator import initiate_comparison, hash_file, transfer_switch, TEST


@dataclass
class Mod:
    """ A formal data structure representing a Mod definition. """

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
    def create(cls, name: str, changes_source: str = '', **kwargs) -> 'Mod':
        """ Replaces mod_new and definition_write. Creates a new mod from scratch. """
        mod_directory = f'{core.state.library}/{name}'
        if not os.path.isdir(mod_directory):
            os.mkdir(mod_directory)

        active, changes = initiate_comparison(mod_directory, changes_source=changes_source)

        new_mod = cls(
            name=name,
            transfer_type=DEFINITION_CLASSES[0],
            active=active,
            changes=changes,
            directory=mod_directory
        )
        for key, value in kwargs.items():
            if hasattr(new_mod, key):
                setattr(new_mod, key, value)
        new_mod.save()
        return new_mod

    @classmethod
    def load(cls, mod_directory: str) -> 'Mod':
        """
        Loads a Mod definition directly from a folder path.
        """
        if not mod_directory:
            raise ValueError("A directory path must be provided to load a Mod.")
        if mod_directory in core.state.exceptions:
            raise s.InternalError("The provided path is defined as an exception.")

        file_path = f'{mod_directory}/{MOD_DEF_FILE_NAME}'
        if not os.path.isfile(file_path):
            raise s.InternalError(f'No definition found under {mod_directory}')

        with open(file_path, 'r') as definition_buffer:
            raw_dict = json.load(definition_buffer)
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
                "Cannot change mod name via simple edit. Use LibraryManager.rename_mod() instead."
            )
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                log(f"Warning: Attempted to edit unrecognized property '{key}'")
        self.save()
        return self

    # --- MOD OPERATION CAPABILITIES ---

    def check_library(self) -> bool:
        """ Returns True if any tracked file is missing from the library folder. """
        for file in self.changes:
            if not os.path.isfile(f"{self.directory}/{file}"):
                return True
        return False

    def detect_changes(self) -> dict:
        """ Inspects if the files of the mod have been changed from their original hashes. """
        changes_dict = {}
        for mod_file, change_data in self.changes.items():
            if self.active:
                file_path = f'{s.MAIN_DIRECTORY}/{mod_file}'
            else:
                file_path = f'{self.directory}/{mod_file}'

            if os.path.isfile(file_path):
                file_hash = hash_file(file_path)
                # change_data[1] is the expected old hash
                if change_data[1] != file_hash:
                    if len(change_data) == 3:
                        if change_data[2] != file_hash:
                            changes_dict[mod_file] = [Change.CHANGED, file_hash]
                    else:
                        changes_dict[mod_file] = [Change.CHANGED, file_hash]
            else:
                changes_dict[mod_file] = [Change.REMOVED, '0']
        return changes_dict

    def attach(self, check_type: str = 'ancestor') -> bool:
        """ Attaches the mod to the game directory, routing files and managing archives. """
        error_sensitive = True
        transfer = Transfer.MOVE

        # 1. Check for overrides
        ancestor_mod = LibraryManager.detect_override(self)
        if ancestor_mod:
            self.edit(overrides=ancestor_mod.name)
            ancestor_mod.edit(overrode_by=self.name)

        if Property.OVERRIDES in check_type:
            if not os.path.isdir(self.directory):
                raise s.InternalError('path not recognized')
            if self.active and check_type != 'pass':
                raise s.InternalError('activation of active mod aborted')

            if self.transfer_type == DEFINITION_CLASSES[0]:
                transfer = Transfer.MOVE
            elif self.transfer_type == DEFINITION_CLASSES[1]:
                transfer = Transfer.COPY

            ancestor_mod_object = LibraryManager.check_relative(self, Property.OVERRIDES)
            if ancestor_mod_object:
                if not ancestor_mod_object.attach():
                    raise s.InternalError('ancestor mod not attached')
        elif check_type == 'pass':
            error_sensitive = False

        # 2. Archive Setup
        archive_dir = f"{core.state.archive}/{self.name}"
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir, exist_ok=True)

        comparison_dict = self.changes.copy()
        if not comparison_dict and os.path.isfile(f"{self.directory}/comparison_{self.name}.json"):
            with open(f"{self.directory}/comparison_{self.name}.json") as comp_buffer:
                comparison_dict = json.load(comp_buffer)
        if not comparison_dict:
            raise s.InternalError('comparison missing')

        # 3. Transfer Routing
        try:
            for path_key, change_data in comparison_dict.items():
                file_path_source = f"{core.state.install_path}/{path_key}"
                file_path_game = f"{core.state.install_path}/{'/'.join(path_key.split('/')[:-1])}"
                file_path_archive = f"{core.state.archive}/{self.name}/{'/'.join(path_key.split('/')[:-1])}"
                file_path_mod = f"{self.directory}/{path_key}"

                status = change_data[0]
                if status == Change.UNCHANGED:
                    continue
                elif status == Change.CHANGED:
                    transfer_switch(file_path_source, file_path_archive, transfer, error_sensitive)
                    transfer_switch(file_path_mod, file_path_game, transfer, error_sensitive)
                elif status == Change.ADDED:
                    transfer_switch(file_path_mod, file_path_game, transfer, error_sensitive)
                elif status == Change.REMOVED:
                    transfer_switch(file_path_source, file_path_archive, transfer, error_sensitive)
        except s.InternalError:
            log(f'mod_attach {self.name} CANCELLED\n')
            self.detach(transfer=Transfer.REMOVE, check_type='pass')
            return False

        if TEST:
            raise s.InternalError('Test phase: mod_attach not applied')

        self.edit(active=True)
        log(f'mod_attach {self.name}\n')
        return True

    def detach(self, transfer: Transfer = Transfer.COPY, check_type: str = 'hash, heir') -> bool:
        """ Formally mod_reverse(). Detaches the mod, routing files back to the library/archive. """
        error_sensitive = True
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory, exist_ok=True)

        if transfer == Transfer.REMOVE:
            if not self.active and check_type != 'pass':
                raise s.InternalError('deactivation of inactive mod aborted')
            if self.transfer_type == DEFINITION_CLASSES[0]:
                transfer = Transfer.MOVE
            elif self.transfer_type == DEFINITION_CLASSES[1] and self.check_library():
                transfer = Transfer.MOVE
            elif self.transfer_type == DEFINITION_CLASSES[1]:
                transfer = Transfer.DELETE

        if not self.changes:
            raise s.InternalError('comparison missing')

        if Property.OVERRODE_BY in check_type:
            heir_mod = LibraryManager.check_relative(self, Property.OVERRODE_BY)
            if heir_mod:
                if not heir_mod.detach(transfer=Transfer.REMOVE):
                    raise s.InternalError('heir mod not retrieved')
        elif check_type == 'pass':
            error_sensitive = False

        try:
            for path_key, change_data in self.changes.items():
                file_path_source = f"{core.state.install_path}/{path_key}"
                file_path_game = f"{core.state.install_path}/{'/'.join(path_key.split('/')[:-1])}"
                file_path_mod = f"{self.directory}/{'/'.join(path_key.split('/')[:-1])}"
                file_path_archive = f"{core.state.archive}/{self.name}/{path_key}"

                status = change_data[0]
                if status == Change.UNCHANGED:
                    continue
                elif status == Change.CHANGED:
                    if transfer in Transfer:
                        transfer_switch(file_path_source, file_path_mod, transfer, error_sensitive)
                    if transfer in (Transfer.MOVE, Transfer.DELETE):
                        transfer_switch(file_path_archive, file_path_game, Transfer.MOVE, error_sensitive)
                elif status == Change.ADDED:
                    transfer_switch(file_path_source, file_path_mod, transfer, error_sensitive)
                elif status == Change.REMOVED:
                    if transfer in (Transfer.MOVE, Transfer.DELETE):
                        transfer_switch(file_path_archive, file_path_game, Transfer.MOVE, error_sensitive)
        except s.InternalError:
            log(f'mod_reverse {self.name} CANCELLED\n')
            self.attach(check_type='pass')
            return False

        if TEST:
            raise s.InternalError('under TEST phase: mod_reverse not applied')

        self.edit(active=False)
        log(f'mod_reverse {self.name}\n')
        return True

    def retrieve(self) -> bool:
        """ Wrapper for detaching via REMOVE. """
        return self.detach(transfer=Transfer.REMOVE)

    def reload(self) -> bool:
        if self.retrieve():
            return self.attach()
        return False

    def extract(self) -> None:
        self.detach(transfer=Transfer.COPY)


class LibraryManager:
    """ Handles multi-mod operations like scanning, sorting, and linking across the library. """

    @staticmethod
    def get_all_mods() -> List[Mod]:
        mods = []
        for name in os.listdir(core.state.library):
            if name not in core.state.exceptions:
                try:
                    mods.append(Mod.load(f"{core.state.library}/{name}"))
                except s.InternalError:
                    pass  # Safely ignore folders that don't have valid definitions
        return mods

    @staticmethod
    def select_mods(**criteria) -> List[Mod]:
        """ Replaces mods_select. Filters the library by provided keyword attributes. """
        selected = []
        for mod in LibraryManager.get_all_mods():
            if mod.transfer_type in DEFINITION_CLASSES[:2]:
                if criteria:
                    # Match all provided criteria to the mod's attributes
                    match = all(getattr(mod, key, None) == val for key, val in criteria.items())
                    if match:
                        selected.append(mod)
                else:
                    selected.append(mod)
        return selected

    @staticmethod
    def sort_mods(criteria: str = Property.OVERRIDES, mods: List[Mod] = None) -> dict:
        if mods is None:
            mods = LibraryManager.select_mods()

        if criteria == Property.OVERRIDES:
            sorted_dict = {}
            for mod_parent in mods:
                for mod in mods:
                    if mod.name == getattr(mod_parent, criteria, None):
                        sorted_dict[mod_parent.name] = str(mods.index(mod))
                        break
            return sorted_dict
        else:
            raise s.InternalError(message='unrecognized criteria')

    @staticmethod
    def check_relative(mod: Mod, relation: str) -> Optional[Mod]:
        """ Fetches the actual Mod object for an ancestor or heir. """
        if relation == Property.OVERRODE_BY and mod.overrode_by:
            heir_dir = f"{core.state.library}/{mod.overrode_by}"
            if os.path.isfile(f"{heir_dir}/{MOD_DEF_FILE_NAME}"):
                heir = Mod.load(heir_dir)
                if heir.active:
                    return heir
        elif relation == Property.OVERRIDES and mod.overrides:
            ancestor_dir = f"{core.state.library}/{mod.overrides}"
            if os.path.isfile(f"{ancestor_dir}/{MOD_DEF_FILE_NAME}"):
                ancestor = Mod.load(ancestor_dir)
                if not ancestor.active:
                    return ancestor
        return None

    @staticmethod
    def detect_override(mod: Mod) -> Optional[Mod]:
        """ Scans the active library to see if the given mod overrides any existing files. """
        new_changes = mod.changes
        active_mods = LibraryManager.select_mods(active=True)

        for active_mod in active_mods:
            if mod.overrides == active_mod.name:
                return active_mod

        for active_mod in active_mods:
            if not active_mod.overrode_by:
                for active_file in active_mod.changes:
                    if active_file.strip('../') in new_changes:
                        return active_mod
        return None

    @staticmethod
    def rename_mod(mod: Mod, new_name: str) -> Mod:
        """ Safely renames a mod's directory and recursively updates sibling links. """
        if not mod.directory:
            raise s.InternalError('Cannot rename mod: Mod directory is unknown.')

        list_mods = [_ for _ in os.listdir(core.state.library) if _ not in core.state.exceptions]
        if new_name in list_mods:
            raise s.InternalError(f'rename_mod error: name {new_name} is already in use')

        old_name = mod.name

        for sibling_name in list_mods:
            sibling_path = f'{core.state.library}/{sibling_name}'
            try:
                sibling_mod = Mod.load(sibling_path)
                if sibling_mod.overrides == old_name:
                    sibling_mod.edit(overrides=new_name)
                if sibling_mod.overrode_by == old_name:
                    sibling_mod.edit(overrode_by=new_name)
            except s.InternalError:
                pass  # Skip folders without definitions

        new_directory = f"{'/'.join(mod.directory.split('/')[:-1])}/{new_name}"
        os.rename(src=mod.directory, dst=new_directory)

        mod.name = new_name
        mod.directory = new_directory
        mod.save()

        return mod
