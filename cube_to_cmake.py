import os
import shutil
import argparse

def create_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def flush_drivers_folder(dir):
    if not os.path.exists(dir):
        os.mkdir(dir)
    else:
        shutil.rmtree(dir)
        os.mkdir(dir)

    os.mkdir(os.path.join(dir, "include"))
    os.mkdir(os.path.join(dir, "src"))


def contain_ext(ext, filenames):
    extensions = set()

    for file in filenames:
        extensions.add(os.path.splitext(file)[1])
    if ext in extensions:
        return True
    else:
        return False


def is_include_folder(filenames):
    return contain_ext('.h', filenames)


def is_src_folder(filenames):
    return contain_ext('.c', filenames) or contain_ext('.cpp', filenames) or contain_ext('.s', filenames) \
           or contain_ext('.S', filenames)


def remove_device_intermediate_folders(dir):
    index = dir.find("/st/")
    if index >= 0:
        index = index + 4
        end_index = 0
        while end_index < index + 4:
            end_index = dir.find("/", index)

        mcu = dir[index:end_index]
        return dir.replace('/st/' + mcu + '/', '/')
    else:
        return dir


def remove_include_folder_from_path(dir):
    dir = dir.replace('/inc/', '/')
    dir = remove_device_intermediate_folders(dir)
    head, tail = os.path.split(dir)
    if tail == "include" or tail == "includes" or tail == "inc":
        return head
    else:
        return dir


def remove_src_folder_from_path(dir):
    head, tail = os.path.split(dir)
    if tail == "source" or tail == "sources" or tail == "src":
        return head
    else:
        return dir


def add_to_includes(drivers_dir, cube_dir, include_dir, files):
    common_prefix = os.path.commonprefix([cube_dir, include_dir])
    relative_path = os.path.relpath(include_dir, common_prefix)

    target_dir = os.path.join(drivers_dir, "include", relative_path.lower())
    target_dir = remove_include_folder_from_path(target_dir)
    create_dir(target_dir)

    for file in files:
        shutil.copyfile(include_dir + os.path.sep + file, target_dir + os.path.sep + file)


def add_to_src(drivers_dir, cube_dir, src_dir, files):
    common_prefix = os.path.commonprefix([cube_dir, src_dir])
    relative_path = os.path.relpath(src_dir, common_prefix)

    target_dir = os.path.join(drivers_dir, "src", relative_path.lower())
    target_dir = remove_src_folder_from_path(target_dir)
    create_dir(target_dir)

    for file in files:
        shutil.copyfile(src_dir + os.path.sep + file, target_dir + os.path.sep + file)


class CmakeFile(object):
    def __init__(self, path, dirnames):
        self.path = path
        self.dirnames = dirnames

    def write_local_var(self, file, var_name):
        file.write("# Set local variables{0}".format(os.linesep))
        file.write("set(localVar{0}".format(os.linesep))
        file.write("  ${{{0}}}{1}".format(var_name, os.linesep))
        file.write("  ){0}".format(os.linesep))
        file.write(os.linesep)

    def write_var_update(self, file, var_name):
        file.write("# Update the project lists{0}".format(os.linesep))
        file.write("set({0} ${{localVar}} CACHE INTERNAL \"\"){1}".format(var_name, os.linesep))
        file.write(os.linesep)

    def write_sub_dirs(self, file):
        for dir in self.dirnames:
            file.write("add_subdirectory({0}){1}".format(dir, os.linesep))

    def write_to_file(self):
        if os.path.exists(self.path):
            if len(dirnames) > 0:
                text_file = open(os.path.join(self.path, "CMakeLists.txt"), "w")
                self.write_sub_dirs(text_file)
                text_file.close()


class CmakeFileSrc(CmakeFile):
    def __init__(self, path, dirnames, filenames):
        super().__init__(path, dirnames)
        self.filenames = filenames

    def write_src_to_var(self, file):
        file.write("# Add specific source to the list{0}".format(os.linesep))
        file.write("list(APPEND localVar{0}".format(os.linesep))
        for src_file in self.filenames:
            file.write("  ${{CMAKE_CURRENT_SOURCE_DIR}}/{0}{1}".format(src_file, os.linesep))
        file.write("  ){0}".format(os.linesep))
        file.write(os.linesep)

    def write_to_file(self):
        if os.path.exists(self.path):
            if len(filenames) > 0:
                text_file = open(os.path.join(self.path, "CMakeLists.txt"), "w")
                self.write_local_var(text_file, "STM32_SOURCES")
                self.write_src_to_var(text_file)
                self.write_var_update(text_file, "STM32_SOURCES")
                self.write_sub_dirs(text_file)
                text_file.close()


class CmakeFileInc(CmakeFile):
    def __init__(self, path, dirnames, filenames):
        super().__init__(path, dirnames)
        self.filenames = filenames

    def write_inc_to_var(self, file):
        file.write("# Add specific directories to the list{0}".format(os.linesep))
        file.write("list(APPEND localVar{0}".format(os.linesep))
        file.write("  ${{CMAKE_CURRENT_SOURCE_DIR}}{0}".format(os.linesep))
        file.write("  ){0}".format(os.linesep))
        file.write(os.linesep)

    def write_to_file(self):
        if os.path.exists(self.path):
            if len(filenames) > 0:
                text_file = open(os.path.join(self.path, "CMakeLists.txt"), "w")
                self.write_local_var(text_file, "STM32_INC_DIRECTORIES")
                self.write_inc_to_var(text_file)
                self.write_var_update(text_file, "STM32_INC_DIRECTORIES")
                self.write_sub_dirs(text_file)
                text_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--cube', required=True, type=str, help="Path to cube sw4stm32 project")
    parser.add_argument('--cmake', required=True, type=str, help="Path to cmake project")

    args = parser.parse_args()
    cube_path = args.cube
    cmake_path = args.cmake

    cube_drivers = os.path.join(cube_path, "Drivers")
    cube_startup = os.path.join(cube_path, "startup")

    drivers_dir = os.path.join(cmake_path, "system")
    flush_drivers_folder(drivers_dir)

    # Copy startup folder
    driver_startup = os.path.join(drivers_dir, "startup")
    create_dir(driver_startup)
    for file in next(os.walk(cube_startup))[2]:
        shutil.copyfile(cube_startup + os.path.sep + file, driver_startup + os.path.sep + file)

    # Copy and reorder Drivers folder
    for (dirpath, dirnames, filenames) in os.walk(cube_drivers):
        if is_include_folder(filenames):
            add_to_includes(drivers_dir, cube_drivers, dirpath, filenames)

        if is_src_folder(filenames):
            add_to_src(drivers_dir, cube_drivers, dirpath, filenames)

    # Copy system_stm32f0xx.c file
    shutil.copyfile(os.path.join(cube_path, "Src") + os.path.sep + "system_stm32f0xx.c", os.path.join(drivers_dir, "src") + os.path.sep + "system_stm32f0xx.c")

    # Create CMakeFiles
    for (dirpath, dirnames, filenames) in os.walk(drivers_dir):
        if len(filenames) == 0:
            file = CmakeFile(dirpath, dirnames)
            file.write_to_file()
        elif is_src_folder(filenames):
            file = CmakeFileSrc(dirpath, dirnames, filenames)
            file.write_to_file()
        elif is_include_folder(filenames):
            file = CmakeFileInc(dirpath, dirnames, filenames)
            file.write_to_file()
