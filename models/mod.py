import os
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, ClassVar

from source.messaging import InternalError, log
import source.core as core
from source.constants import Property, DEFINITION_CLASSES, Transfer, Change, MOD_DEF_FILE_NAME, MAIN_DIRECTORY
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

    # --- THE BRIDGE ---
    # Maps the dynamic Property string (e.g., 'ancestor') to the hardcoded Python attribute ('overrides')
    _PROPERTY_MAP: ClassVar[dict] = {
        Property.TRANSFER_TYPE: 'transfer_type',
        Property.NAME: 'name',
        Property.GAME: 'game',
        Property.LAUNCH: 'launch',
        Property.ACTIVE: 'active',
        Property.OVERRIDES: 'overrides',
        Property.OVERRODE_BY: 'overrode_by',
        Property.DESCRIPTION: 'description',
        Property.CHANGES: 'changes'
    }

    def __getattr__(self, item):
        """ Intercepts dynamic lookups like `getattr(mod, Property.OVERRIDES)` """
        if item in self.__class__._PROPERTY_MAP:
            # If item is 'ancestor', it maps to 'overrides' and returns self.overrides safely!
            return getattr(self, self.__class__._PROPERTY_MAP[item])
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        """ Intercepts dynamic sets like `setattr(mod, Property.OVERRIDES, value)` """
        if hasattr(self.__class__, '_PROPERTY_MAP') and key in self.__class__._PROPERTY_MAP:
            super().__setattr__(self.__class__._PROPERTY_MAP[key], value)
        else:
            super().__setattr__(key, value)

    @classmethod
    def from_dict(cls, data: dict, directory: str = "") -> 'Mod':
        """ Automatically maps all JSON keys to the correct class attributes! """
        kwargs = {attr_name: data[prop_key]
                  for prop_key, attr_name in cls._PROPERTY_MAP.items()
                  if prop_key in data}
        return cls(directory=directory, **kwargs)

    def to_dict(self) -> dict:
        """ Automatically builds the JSON dict using the Property constants! """
        return {prop_key: getattr(self, attr_name)
                for prop_key, attr_name in self._PROPERTY_MAP.items()}

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
            raise InternalError("The provided path is defined as an exception.")

        file_path = f'{mod_directory}/{MOD_DEF_FILE_NAME}'
        if not os.path.isfile(file_path):
            raise InternalError(f'No definition found under {mod_directory}')

        with open(file_path, 'r') as definition_buffer:
            raw_dict = json.load(definition_buffer)
            return cls.from_dict(raw_dict, directory=mod_directory)

    def save(self) -> None:
        """ Saves the mod's current state to its definition file. """
        if not self.directory:
            raise InternalError("Cannot save Mod: No directory specified.")
        file_path = f'{self.directory}/{MOD_DEF_FILE_NAME}'
        with open(file_path, 'w') as definition_buffer:
            json.dump(self.to_dict(), definition_buffer, indent=4)
        log.info(f'definition saved in {self.directory}')

    def edit(self, **kwargs) -> 'Mod':
        """ Updates the mod's attributes and saves the changes. """
        if Property.NAME in kwargs or "name" in kwargs:
            raise InternalError(
                "Cannot change mod name via simple edit. Use LibraryManager.rename_mod() instead."
            )
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                log.warning(f"Attempted to edit unrecognized property '{key}'")
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
                file_path = f'{MAIN_DIRECTORY}/{mod_file}'
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

    def _resolve_attach_dependencies(self, check_type: str) -> None:
        """ Step 1: Handles override detection and ancestor attachment logic. """
        ancestor_mod = LibraryManager.detect_override(self)
        if ancestor_mod:
            self.edit(overrides=ancestor_mod.name)
            ancestor_mod.edit(overrode_by=self.name)

        if Property.OVERRIDES in check_type:
            if not os.path.isdir(self.directory):
                raise InternalError('path not recognized')
            if self.active and check_type != 'pass':
                raise InternalError('activation of active mod aborted')

            ancestor_mod_object = LibraryManager.check_relative(self, Property.OVERRIDES)
            if ancestor_mod_object:
                if not ancestor_mod_object.attach():
                    raise InternalError('ancestor mod not attached')

    def generate_attach_plan(self) -> list:
        """ Step 2: Generates a manifest of file transfers without touching the disk. """
        plan = []
        transfer_type = Transfer.MOVE if self.transfer_type == DEFINITION_CLASSES[0] else Transfer.COPY

        comparison_dict = self.changes.copy()
        if not comparison_dict and os.path.isfile(f"{self.directory}/comparison_{self.name}.json"):
            with open(f"{self.directory}/comparison_{self.name}.json") as comp_buffer:
                comparison_dict = json.load(comp_buffer)

        if not comparison_dict:
            raise InternalError('comparison missing')

        # Build the exact list of moves needed
        for path_key, change_data in comparison_dict.items():
            file_path_source = f"{core.state.install_path}/{path_key}"
            file_path_game = f"{core.state.install_path}/{'/'.join(path_key.split('/')[:-1])}"
            file_path_archive = f"{core.state.archive}/{self.name}/{'/'.join(path_key.split('/')[:-1])}"
            file_path_mod = f"{self.directory}/{path_key}"

            status = change_data[0]
            if status == Change.UNCHANGED:
                continue
            elif status == Change.CHANGED:
                plan.append({'src': file_path_source, 'dst': file_path_archive, 'type': transfer_type})
                plan.append({'src': file_path_mod, 'dst': file_path_game, 'type': transfer_type})
            elif status == Change.ADDED:
                plan.append({'src': file_path_mod, 'dst': file_path_game, 'type': transfer_type})
            elif status == Change.REMOVED:
                plan.append({'src': file_path_source, 'dst': file_path_archive, 'type': transfer_type})

        return plan

    def _execute_transfer_plan(self, plan: list, error_sensitive: bool = True) -> None:
        """ Step 3: Loops through any provided plan and strictly executes it. """
        for step in plan:
            transfer_switch(step['src'], step['dst'], step['type'], error_sensitive)

    def attach(self, check_type: str = 'ancestor', dry_run: bool = False):
        """ Attaches the mod to the game directory, routing files and managing archives. """
        error_sensitive = (check_type != 'pass')

        # 1. Resolve relational links and ancestor dependencies
        self._resolve_attach_dependencies(check_type)

        # 2. Archive Setup
        archive_dir = f"{core.state.archive}/{self.name}"
        if not os.path.isdir(archive_dir):
            os.makedirs(archive_dir, exist_ok=True)

        # 3. Generate the Transfer Plan
        plan = self.generate_attach_plan()

        # If the UI just wants a report, we hand the plan back instantly and stop here!
        if dry_run:
            return plan

        # 4. Execute the Plan
        try:
            self._execute_transfer_plan(plan, error_sensitive)
        except InternalError:
            log.warning(f'{self.name} CANCELLED\n')
            self.detach(transfer=Transfer.REMOVE, check_type='pass')
            return False

        # 5. Finalize State
        self.edit(active=True)
        log.info(f'{self.name} attached successfully')
        return True

    def _resolve_detach_dependencies(self, transfer: Transfer, check_type: str) -> Transfer:
        """ Step 1: Resolves the actual transfer method and handles heir dependencies. """
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory, exist_ok=True)

        resolved_transfer = transfer

        # Resolve "REMOVE" into either MOVE or DELETE based on the mod's class and state
        if transfer == Transfer.REMOVE:
            if not self.active and check_type != 'pass':
                raise InternalError('deactivation of inactive mod aborted')

            if self.transfer_type == DEFINITION_CLASSES[0]:
                resolved_transfer = Transfer.MOVE
            elif self.transfer_type == DEFINITION_CLASSES[1] and self.check_library():
                resolved_transfer = Transfer.MOVE
            elif self.transfer_type == DEFINITION_CLASSES[1]:
                resolved_transfer = Transfer.DELETE

        if not self.changes:
            raise InternalError('comparison missing')

        # If this mod is overridden by a child (heir), the heir must be detached first
        if Property.OVERRODE_BY in check_type:
            heir_mod = LibraryManager.check_relative(self, Property.OVERRODE_BY)
            if heir_mod:
                if not heir_mod.detach(transfer=Transfer.REMOVE):
                    raise InternalError('heir mod not retrieved')

        return resolved_transfer

    def generate_detach_plan(self, transfer: Transfer) -> list:
        """ Step 2: Generates a manifest of files to route back to the library/archive. """
        plan = []

        for path_key, change_data in self.changes.items():
            file_path_source = f"{core.state.install_path}/{path_key}"
            file_path_game = f"{core.state.install_path}/{'/'.join(path_key.split('/')[:-1])}"
            file_path_mod = f"{self.directory}/{'/'.join(path_key.split('/')[:-1])}"
            file_path_archive = f"{core.state.archive}/{self.name}/{path_key}"

            status = change_data[0]
            if status == Change.UNCHANGED:
                continue

            elif status == Change.CHANGED:
                # Equivalent to the original: if transfer in Transfer:
                plan.append({'src': file_path_source, 'dst': file_path_mod, 'type': transfer})

                if transfer in (Transfer.MOVE, Transfer.DELETE):
                    plan.append({'src': file_path_archive, 'dst': file_path_game, 'type': Transfer.MOVE})

            elif status == Change.ADDED:
                plan.append({'src': file_path_source, 'dst': file_path_mod, 'type': transfer})

            elif status == Change.REMOVED:
                if transfer in (Transfer.MOVE, Transfer.DELETE):
                    plan.append({'src': file_path_archive, 'dst': file_path_game, 'type': Transfer.MOVE})

        return plan

    def detach(self, transfer: Transfer = Transfer.COPY, check_type: str = 'hash, heir', dry_run: bool = False):
        """ Formally mod_reverse(). Detaches the mod, routing files back to the library/archive. """
        error_sensitive = (check_type != 'pass')

        # 1. Resolve dependencies and figure out the exact transfer method
        resolved_transfer = self._resolve_detach_dependencies(transfer, check_type)

        # 2. Generate the Transfer Plan
        plan = self.generate_detach_plan(resolved_transfer)

        # If the UI just wants a preview, hand the plan back instantly!
        if dry_run:
            return plan

        # 3. Execute the Plan (reusing the exact same method from attach!)
        try:
            self._execute_transfer_plan(plan, error_sensitive)
        except InternalError:
            log.warning(f'{self.name} CANCELLED\n')

            # Rollback: If detachment fails, attempt to forcibly re-attach
            self.attach(check_type='pass')
            return False

        # 4. Finalize State
        self.edit(active=False)
        log.info(f'{self.name} detach successfully')
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
                except InternalError:
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
            raise InternalError(message='unrecognized criteria')

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
            raise InternalError('Cannot rename mod: Mod directory is unknown.')

        list_mods = [_ for _ in os.listdir(core.state.library) if _ not in core.state.exceptions]
        if new_name in list_mods:
            raise InternalError(f'rename_mod error: name {new_name} is already in use')

        old_name = mod.name

        for sibling_name in list_mods:
            sibling_path = f'{core.state.library}/{sibling_name}'
            try:
                sibling_mod = Mod.load(sibling_path)
                if sibling_mod.overrides == old_name:
                    sibling_mod.edit(overrides=new_name)
                if sibling_mod.overrode_by == old_name:
                    sibling_mod.edit(overrode_by=new_name)
            except InternalError:
                pass  # Skip folders without definitions

        new_directory = f"{'/'.join(mod.directory.split('/')[:-1])}/{new_name}"
        os.rename(src=mod.directory, dst=new_directory)

        mod.name = new_name
        mod.directory = new_directory
        mod.save()

        return mod
