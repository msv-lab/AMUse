import os
import subprocess
import json
from amuse.spoon_bridge.spoon_bridge import SpoonBridge
from amuse.utils.logger import Logger


def find_file_path(folder_path, file_pattern):
    """Find the file path using the find command."""
    try:
        result = subprocess.check_output(
            ["find", folder_path, "-wholename", f"*{file_pattern}"], text=True
        )
        # Return the first match
        return result.splitlines()[0]
    except subprocess.CalledProcessError as e:
        print(f"Error finding file: {e}")
        return None
    except IndexError:
        print(f"Error finding file: No match found")
        return None


def find_method_line_number(file_path, method_signature):
    """Find the line number of the method in the file."""
    method_name = method_signature.split("(")[0]
    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
        for i, line in enumerate(file, 1):
            if method_name in line and all(
                param in line
                for param in method_signature.split("(")[1].replace(")", "").split(", ")
            ):
                return i
    return None


def process_locations(input_file, output_file, root_folder):
    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for line in infile:
            parts = line.strip().split("|")
            if len(parts) == 3:
                folder_path = os.path.join(
                    root_folder, "/".join(parts[0].split(".")[:-1]), "checkout"
                )
                file_path = find_file_path(folder_path, parts[1])
                if file_path:
                    line_number = find_method_line_number(file_path, parts[2])
                    if line_number:
                        outfile.write(
                            f"{parts[0]}, {folder_path}, {file_path}, {line_number}\n"
                        )


def generate_facts_from_json(json_file_path, api_resource_sig):
    """Generate the facts for the given json file."""

    # load json file
    with open(json_file_path, "r") as infile:
        json_data = json.load(infile)

    cache_dirs = []

    # for each object in json file, read the file and generate facts
    if api_resource_sig not in json_data:
        raise Exception(f"API resource signature {api_resource_sig} not found")
    for obj in json_data[api_resource_sig]:
        cache_dirs.append(generate_facts_for_object(obj))

    return cache_dirs, len(json_data[api_resource_sig])


def generate_facts_for_object(obj):
    """Generate the facts for the given object."""
    id_ = obj["id"]
    file_path = obj["file_path"]
    api_line_no = obj["api_line_no"]
    cache_dir = os.path.join("/root/amuse/evaluation/cache", id_.replace(".", "/"))
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    args = [
        "--mode",
        "INTRA_PROC",
        "--target-path",
        file_path,
        "--file-path",
        file_path,
        "--line-no",
        str(api_line_no),
        "--root-folder",
        cache_dir,
    ]
    try:
        Logger.info(f"Generating facts of {file_path}\n")
        p = SpoonBridge.run_factor(args)
        p.check_returncode()
        Logger.info(f"Generated facts are written to {cache_dir}\n")
        Logger.debug(p.stdout)

    except Exception as e:
        Logger.error(f"Failed to generate facts of {cache_dir}\n")
        Logger.error(e)

    # find the only folder in the cache_dir
    facts_dir = None
    for folder in os.listdir(cache_dir):
        if os.path.isdir(os.path.join(cache_dir, folder)):
            facts_dir = os.path.join(cache_dir, folder)
            break

    return facts_dir


api_sig_map = {
    "java.util@Iterator@hasNext+java.util@Iterator@next": "java.util.Iterator.next",
    "java.util.Map@get": "java.util.Map.get",
    "java.util@Scanner@hasNext+java.util@Scanner@next": "java.util.Scanner.next",
    "android.app@Dialog@dismiss+android.app@Dialog@isShowing": "android.app.ProgressDialog.dismiss",
    "java.io@DataOutputStream+java.io@DataOutputStream@close": "java.io.DataOutputStream.<init>",
    "java.lang.String": "java.lang.String.<init>",
    "java.lang.String@getBytes": "java.lang.String.getBytes",
    "java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream": "java.io.ByteArrayOutputStream.toByteArray",
    "java.lang.Long.parseLong": "java.lang.Long.parseLong",
    "java.lang.Short.parseShort": "java.lang.Short.parseShort",
    "android.database@Cursor@close+android.database.sqlite@SQLiteDatabase@query": "android.database.sqlite.SQLiteDatabase.query",
    "java.net.URLDecoder@decode": "java.net.URLDecoder.decode",
    "org.kohsuke.args4j.spi.Parameters.getParameter": "org.kohsuke.args4j.spi.Parameters.getParameter",
    "java.util.StringTokenizer.nextToken": "java.util.StringTokenizer.nextToken",
    "android.content.Context": "android.content.Context.<init>",
    "java.io.File.createNewFile": "java.io.File.createNewFile",
    "android.content.pm.ApplicationInfo.loadIcon": "android.content.pm.ApplicationInfo.loadIcon",
    "android.content.res.TypedArray.getString": "android.content.res.TypedArray.getString",
    "android.os.Environment.getExternalStorageState": "android.os.Environment.getExternalStorageState",
    "java.lang.Byte.parseByte": "java.lang.Byte.parseByte",
    "org.kohsuke.args4j.spi.Parameters.getParameter": "org.kohsuke.args4j.spi.Parameters.getParameter",
    "java.sql.Statement.setFetchSize": "java.sql.Statement.setFetchSize",
    "java.io.RandomAccessFile.close": "java.io.RandomAccessFile.close",
}


def extract_method_content_for_object(api_sig, obj):
    id_ = obj["id"]
    file_path = obj["file_path"]
    api_line_no = obj["api_line_no"]
    api = api_sig_map.get(api_sig, api_sig)

    cache_dir = os.path.join("/root/mubench/methods", api + "_" + id_)

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    args = [
        "--mode",
        "PRINT",
        "--target-path",
        file_path,
        "--file-path",
        file_path,
        "--line-no",
        str(api_line_no),
        "--root-folder",
        cache_dir,
    ]
    try:
        Logger.info(f"Printing the method of {file_path}\n")
        p = SpoonBridge.run_factor(args)
        p.check_returncode()
        Logger.info(f"The method is written to {cache_dir}\n")
        Logger.debug(p.stdout)

    except Exception as e:
        Logger.error(f"Failed to print the method of {cache_dir}\n")
        Logger.error(e)

    return cache_dir


if __name__ == "__main__":
    generate_facts_from_json(
        "/root/amuse/mubench.json",
        "java.util@Scanner@hasNext+java.util@Scanner@next",
    )

    # # load the mubench.json file
    # with open("/root/amuse/mubench.json", "r") as infile:
    #     json_data = json.load(infile)

    # # for each object in json file, read the file and save the method content
    # for api_sig in json_data:
    #     for obj in json_data[api_sig]:
    #         extract_method_content_for_object(api_sig, obj)

    # # load the mubench.json file
    # with open("/root/amuse/evaluation/mubench.json", "r") as infile:
    #     json_data = json.load(infile)

    # # for each object in json file, read the file and save the method content
    # for api_sig in json_data:
    #     if api_sig not in [
    #         "java.net.URLDecoder@decode",
    #         "java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream",
    #         "java.io@DataOutputStream+java.io@DataOutputStream@close",
    #         "java.util@Scanner@hasNext+java.util@Scanner@next",
    #         "android.app@Dialog@dismiss+android.app@Dialog@isShowing",
    #         "android.database@Cursor@close+android.database.sqlite@SQLiteDatabase@query",
    #     ]:
    #         continue
    #     for obj in json_data[api_sig]:
    #         generate_facts_from_json("/root/amuse/evaluation/mubench.json", api_sig)
