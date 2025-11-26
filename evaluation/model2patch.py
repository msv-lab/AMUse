import re
import json
import copy
import os

from symlog.shortcuts import (
    Fact,
    String,
    Number,
    SymbolicConstant,
    SymbolicSign,
)
from symlog.souffle import pprint, SymbolicNumberWrapper, SymbolicStringWrapper, parse


SYM = "symbol"
NUM = "number"

PLUS = "+"
MINUS = "-"

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")

"""
Parse the model data from the given string.
"""


def parse_model_data(model_str):
    # Split the entire string into separate models based on "Model X" headers
    models = re.split(r"Model \d+", model_str)

    # Remove the first element if it's empty (which happens if the split regex is at the start of the string)
    if models[0].strip() == "":
        models.pop(0)

    # Prepare a dictionary to hold all models
    parsed_models = []

    # Regex pattern to find variable assignments and flow statements
    var_pattern = re.compile(
        r"(\w+\(.*?\)\.\s*|[\w]+)\s*=\s*(True|False|[\-\d\.]+|\".*?\")"
    )
    # Iterate through each model string
    for model in models:
        # Dictionary to hold the variables for this model
        model_vars = {}

        # Find all matches in the current model string
        for match in var_pattern.finditer(model):
            key, value = match.groups()
            value = value.strip()

            # Try to convert the value into int, float, or boolean if applicable
            if value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit() and value.count(".") < 2:
                value = float(value)
            elif value == "True":
                value = True
            elif value == "False":
                value = False
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]  # Remove the quotes around strings

            # Add the variable to the dictionary
            model_vars[key] = value

        # Append the current model's variables dictionary to the list
        parsed_models.append(model_vars)

    return parsed_models


def load_repair_template(api_signature):
    """Load the repair template for the api_signature."""
    repair_templates = json.load(
        open("/root/amuse/evaluation/repair_templates.json", "r")
    )

    for template in repair_templates:
        if template == api_signature:
            return repair_templates[template]


def find_slg_sym_const(slg_sym_consts, name):
    for slg_sym_const in slg_sym_consts:
        if slg_sym_const.name == name:
            return slg_sym_const
    return None


def parse_template(api_signature, slg_sym_consts):
    template_symlog_type_map = {
        "number": NUM,
        "symbol": SYM,
    }

    template = load_repair_template(api_signature)
    if not template:
        raise Exception(f"Repair template for {api_signature} not found")

    # construct the repair template
    added_facts = template["added_facts"]
    symbolic_facts = template["symbolic_facts"]

    # get the added facts
    slg_facts = set()
    for fact in added_facts:
        args = fact["args"]
        slg_args = []
        for arg in args:
            if arg["type"] == "symbolic_constant":
                # find the symbolic constant from slg_sym_consts
                slg_sym_const = find_slg_sym_const(slg_sym_consts, arg["val"])
                if not slg_sym_const:
                    raise Exception(f"Symbolic constant {arg['val']} not found")
                slg_args.append(slg_sym_const)
            elif arg["type"] == "string":
                slg_args.append(String(arg["val"]))
            elif arg["type"] == "number":
                slg_args.append(Number(arg["val"]))
            else:
                raise Exception(f"Unknown type: {arg['type']}")
        slg_fact = Fact(fact["name"], slg_args)
        if fact["symbolic"] is True:
            slg_fact = SymbolicSign(slg_fact)
        slg_facts.add(slg_fact)

    # get the domain constraints
    domain_constraints = template["domain_constraints"]
    slg_domain_constraints = {}
    for constraint in domain_constraints:
        symconst_names = constraint["name"].replace(" ", "").split(",")
        sym_consts = tuple(
            [
                find_slg_sym_const(slg_sym_consts, symconst_name)
                for symconst_name in symconst_names
            ]
        )
        domain = constraint["domain"]
        slg_domain_constraints[sym_consts] = domain

    return slg_sym_consts, slg_facts, symbolic_facts, slg_domain_constraints


def get_sym_consts_in_template(api_signature):
    template_symlog_type_map = {
        "number": NUM,
        "symbol": SYM,
    }

    template = load_repair_template(api_signature)
    if not template:
        raise Exception(f"Repair template for {api_signature} not found")
        # return None

    # construct the repair template
    symbolic_constants = template["symbolic_constants"]
    added_facts = template["added_facts"]
    symbolic_facts = template["symbolic_facts"]

    # add the symbolic constants
    slg_sym_consts = [
        SymbolicConstant(
            symbolic_constant["name"],
            template_symlog_type_map[symbolic_constant["type"]],
        )
        for symbolic_constant in symbolic_constants
    ]

    return slg_sym_consts


def get_added_facts_in_template(api_signature, slg_sym_consts):
    _, slg_facts, _, _ = parse_template(api_signature, slg_sym_consts)
    return slg_facts


"""
Convert a z3 model to a patch.
"""


def model2patch(model_path, api_sig, template_path, patch_path):
    with open(model_path, "r") as f:
        model_str = f.read()

    parsed_models = parse_model_data(model_str)

    # get the symbolic constants for the api_sig to repair
    slg_sym_consts = get_sym_consts_in_template(api_sig)
    added_facts = get_added_facts_in_template(api_sig, slg_sym_consts)

    # instantiate the slg_facts with each parsed model
    patches = []
    for model in parsed_models:
        patch = {}
        for slg_fact in added_facts:
            new_args = []
            for arg in slg_fact.head.args:
                if isinstance(arg, SymbolicStringWrapper):
                    if arg.name in model:
                        new_args.append(String(model[arg.name]))
                    else:
                        new_args.append(arg)
                elif isinstance(arg, SymbolicNumberWrapper):
                    if arg.name in model:
                        new_args.append(Number(model[arg.name]))
                    else:
                        new_args.append(arg)
                else:
                    new_args.append(arg)
            new_fact = Fact(slg_fact.head.name, new_args)

            patch[pprint(new_fact).strip()] = True

        for k, v in model.items():
            if isinstance(v, bool):
                patch[k.strip()] = v

        patches.append(patch)

    return patches


def to_readable_patch(patch, api_sig, mubench_path, bug_id, patch_dir):
    # find the source file
    source_file_path = None
    with open(mubench_path, "r") as f:
        mubench_json = json.load(f)
        for bug in mubench_json[api_sig]:
            if bug["id"] == bug_id:
                source_file_path = bug["file_path"]
                break

    if not source_file_path or not os.path.exists(source_file_path):
        raise Exception(f"Source file {source_file_path} not found")

    with open(source_file_path, "r") as f:
        source_code_lines = f.readlines()

    # find the flowid line mapping file in the cache dir of the bug
    cache_dir = os.path.join(CACHE_DIR, bug_id.replace(".", "/"))

    flow_id_line_mapping_file = find_file_from_dir(
        cache_dir, "flow_id_line_mapping.facts"
    )

    # read the flowid_line map from the file
    flow_id_line_map = {}
    with open(flow_id_line_mapping_file, "r") as f:
        for line in f:
            parts = line.strip().split("\t")
            flow_id_line_map[int(parts[0])] = int(parts[1])

    # find facts should be added and removed
    to_add_facts = set()
    to_remove_facts = set()
    for fact_str, status in patch.items():
        predicate = fact_str.split("(")[0]

        fact = parse(fact_str).facts.pop()

        # remove the last argument of the fact if it is 1 (the deprecated symbolic sign)
        fact_args_obj = fact.head.args
        if pprint(fact_args_obj[-1]) == "1":
            fact_args_obj = fact_args_obj[:-1]
            fact = Fact(fact.head.name, fact_args_obj)
        fact_args = [pprint(arg) for arg in fact_args_obj]

        fact_str_w_tabs = "\t".join(fact_args).replace('"', "") + "\n"
        predicate_file = find_file_from_dir(cache_dir, f"{predicate}.facts")
        with open(predicate_file, "r") as f:
            lines = f.readlines()
        if (
            fact_str_w_tabs in lines and status is False
        ):  # need to remove the source code line corresponded by this fact
            to_remove_facts.add(pprint(fact))
        elif (
            fact_str_w_tabs not in lines and status is True
        ):  # need to add the source code line corresponded by this fact
            to_add_facts.add(pprint(fact))

    # find the source code lines to be added and removed
    diff = {}

    # added facts template 1: 1 call and 2 flow
    if set(f.split("(")[0].strip() for f in to_add_facts) == set(["call", "flow"]):

        call = [f for f in to_add_facts if f.split("(")[0].strip() == "call"][0]
        flows = [f for f in to_add_facts if f.split("(")[0].strip() == "flow"]

        source_code_patch = call2patch(call, flows, True, flow_id_line_map)

        diff.update(source_code_patch)

    b1 = False
    b2 = False
    if source_code_patch == {425: "+ oos.flush()\n"}:
        b1 = True
        print(diff)

    # removed facts template 1: a list of flow
    if set(f.split("(")[0].strip() for f in to_remove_facts) == set(["flow"]):
        for flow in to_remove_facts:
            source_code_patch = flow2patch(flow, False, flow_id_line_map)

            if source_code_patch == {426: MINUS}:
                b2 = True

            diff.update(source_code_patch)

    if b1 and b2 and len(to_remove_facts) == 2:
        print("debug")

    # if the number of changes is more than 2, ignore the patch
    if len(sorted(diff.items())) > 2:
        return

    # apply the diff to the source code
    modified_lines = apply_combined_diff(copy.deepcopy(source_code_lines), diff)

    # count the number of patches in the patch_path
    patch_files = os.listdir(patch_dir)
    patch_file_name = f"{len(patch_files) + 1}.diff"

    with open(os.path.join(patch_dir, patch_file_name), "w") as f:
        f.write("".join(modified_lines))


def apply_combined_diff(source_lines, diff):
    # Sort changes by their line numbers
    changes = sorted(diff.items())
    offset = 0

    # Apply changes
    for index, action in changes:
        actual_index = index + offset
        if action.startswith("-"):

            source_lines[actual_index] = (
                "-" + source_lines[actual_index][1:]
            )  # remove the first space

            # debug:
            plus_index = None
            for a in changes:
                if "+" in a[1]:
                    plus_index = a[0]
            if "oos.close" in source_lines[actual_index] and plus_index:
                print(source_lines[actual_index])

            offset -= 1  # Decrease offset due to deletion
        elif action.startswith("+"):
            # find the number of spaces before the first character of the line
            spaces_minus1 = (
                len(source_lines[actual_index])
                - len(source_lines[actual_index].lstrip())
                - 1
            )
            # Insert the new line
            action = (
                "+" + spaces_minus1 * " " + action[2:]
            )  # Remove the "+" and the space
            source_lines.insert(actual_index, action)
            offset += 1  # Increase offset due to addition

    return source_lines


def find_file_from_dir(dir, file_name):
    flow_id_line_mapping_file = None
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file == file_name:
                flow_id_line_mapping_file = os.path.join(root, file)
                break
        if flow_id_line_mapping_file:
            break

    if not flow_id_line_mapping_file:
        raise Exception(f"{file_name} not found in {dir}")

    return flow_id_line_mapping_file


def call2patch(call, flows, status, flow_id_line_map):
    call_args = call.split("call(")[1].split(").")[0].split(", ")
    call_sig, label, var, in_method = call_args
    start = None
    end = None
    for flow in flows:
        flow_st, flow_ed, _ = flow.split("(")[1].split(").")[0].split(", ")
        if flow_st == label:
            end = flow_ed
        elif flow_ed == label:
            start = flow_st

    var = var.replace('"', "")
    call_sig = call_sig.replace('"', "")
    call_name = call_sig.split(".")[-1]

    call_str = f"{var}.{call_name}\n"
    if status:
        if int(end) not in flow_id_line_map:
            # find the latest flow id
            end_in_map = max(flow_id_line_map.keys())
            flow_id_line_map[int(end)] = flow_id_line_map[end_in_map] + 1
        return {flow_id_line_map[int(end)]: PLUS + " " + call_str}
    else:
        raise Exception("Not implemented")


def flow2patch(flow, status, flow_id_line_map):
    flow_args = flow.split("(")[1].split(").")[0].split(", ")
    start, end, method = flow_args

    if not status:
        return {flow_id_line_map[int(end)]: MINUS}
    else:
        raise Exception("Not implemented")


if __name__ == "__main__":
    model_path = "/root/amuse/tmp/jodatime.cc35fb2.269.model"
    patch_path = "patch.txt"
    patches = model2patch(
        model_path,
        "java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream",
        "/root/amuse/evaluation/repair_templates.json",
        patch_path,
    )

    # write the modified source code to the patch file
    bug_id = "jodatime.cc35fb2.269"
    patch_dir = os.path.join(os.path.dirname(__file__), "patch", f"{bug_id}")
    os.makedirs(patch_dir, exist_ok=True)

    for patch in patches:
        to_readable_patch(
            patch,
            "java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream",
            "/root/amuse/evaluation/mubench.json",
            bug_id,
            patch_dir,
        )

    # find the flow(7, 8, "org.joda.time.TestDateMidnight_Basics.testSerialization()", 1). which is False
    for patch in patches:
        if (
            'flow(7, 8, "org.joda.time.TestDateMidnight_Basics.testSerialization()", 1).'
            in patch
            and patch[
                'flow(7, 8, "org.joda.time.TestDateMidnight_Basics.testSerialization()", 1).'
            ]
            is False
        ):
            print(patch)
