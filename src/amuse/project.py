from functools import cached_property
import os
import shutil


class cd:
    def __init__(self, newPath):
        self.targetPath = os.path.expanduser(str(newPath))

    def __enter__(self):
        self.currentPath = os.getcwd()
        os.chdir(self.targetPath)

    def __exit__(self, _etype, _value, _traceback):
        os.chdir(self.currentPath)


class Utils:
    def remove_folder(folder):
        shutil.rmtree(folder, ignore_errors=True)

    def move_replace_folder(folder, target):
        if os.path.exists(target):
            Utils.remove_folder(target)
        shutil.move(folder, target)

    def copy_folder(folder, target):
        shutil.copytree(
            folder,
            target,
            symlinks=False,
            ignore=None,
            copy_function=shutil.copy2,
            ignore_dangling_symlinks=False,
            dirs_exist_ok=False,
        )


class MisuseProject:
    def __init__(self, project_config, root_folder):
        self.project = project_config
        self.root_folder = root_folder

    @property
    def id(self):
        return self.project.get("id")

    @property
    def fixed_name(self):
        return self.id + "_fixed"

    @property
    def unfixed_name(self):
        return self.id + "_unfixed"

    @property
    def revision(self):
        return self.project.get("revision")

    @property
    def method_name(self):
        method = self.project.get("method")

        if "," in method:
            return method.split(",")[0]
        return method

    @property
    def correct_method_line(self):
        return int(self.project.get("method_line"))

    @property
    def unfixed_method_line(self):
        return int(self.project.get("method_line_before"))

    @property
    def repo(self):
        return self.project.get("repo")

    @property
    def fixed_path(self):
        return "/".join([self.root_folder, self.id, self.fixed_name])

    @property
    def unfixed_path(self):
        return "/".join([self.root_folder, self.id, self.unfixed_name])

    @property
    def misuse_file_path(self):
        return self.project.get("file_path")

    @property
    def fixed_file_path(self):
        return "/".join([self.fixed_path, self.misuse_file_path])

    @property
    def unfixed_file_path(self):
        files = list(self.root_folder.glob("**/" + self.id + ".java"))
        return str(files[0])

    @property
    def build_system(self):
        return self.project.get("build_system")

    def _parse_method_block(self, f_path, line_start):
        with open(f_path) as f:
            lines = f.readlines()[line_start - 1 :]

            output = ""
            stack = []
            in_quotation = ""

            current_line = line_start

            for line in lines:
                for letter in line:
                    if letter == "'" and in_quotation == "":
                        in_quotation = letter

                    if letter == "'" and in_quotation == "'":
                        in_quotation = ""

                    if letter == '"' and in_quotation == "":
                        in_quotation = '"'

                    if letter == '"' and in_quotation == '"':
                        in_quotation = ""

                    if letter == "{":
                        stack.append("{")
                    elif letter == "}":
                        stack.pop()
                        if len(stack) == 0:
                            output += letter
                            break
                    output += letter
                else:
                    current_line += 1
                    continue
                return (output, current_line)

    @cached_property
    def method_line_end(self):
        (_, end_line) = self._parse_method_block(
            self.fixed_file_path, self.correct_method_line
        )
        return end_line

    @cached_property
    def before_method_line_end(self):
        (_, end_line) = self._parse_method_block(
            self.unfixed_file_path, self.unfixed_method_line
        )
        return end_line

    @cached_property
    def corrected_method(self):
        (content, _) = self._parse_method_block(
            self.fixed_file_path, self.correct_method_line
        )
        return content

    @cached_property
    def before_corrected_method(self):
        (content, _) = self._parse_method_block(
            self.unfixed_file_path, self.unfixed_method_line
        )
        return content

    def cleanup(self):
        Utils.remove_folder(self.root_folder)
