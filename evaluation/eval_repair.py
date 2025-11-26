from gen_fact import generate_facts_from_json, generate_facts_for_object
from utils import longest_paths

import os
import json
import subprocess
from z3 import Solver, sat, unsat, unknown, Or
import time

from symlog.logger import get_logger

from symlog.shortcuts import (
    Fact,
    String,
    Number,
    parse,
    SymbolicConstant,
    load_facts,
    SymbolicSign,
    symex,
    concretise_facts,
)
from symlog.souffle import (
    NUM,
    SYM,
    String as SouffleString,
    Number as SouffleNumber,
    Program,
    run_program,
    SymbolicNumberWrapper,
    SymbolicStringWrapper,
)

Logger = get_logger(__name__)


def complete_program(program_path):
    """Complete the program by adding `include` files."""
    with open(program_path, "r") as infile:
        program = infile.read()

    # add include files
    # check the lines starting with `#include`
    lines = program.split("\n")
    for line in lines:
        if line.startswith("#include"):
            # get the file path
            file_path = line.split(" ")[1].strip('"')
            # read the file and insert the content at the beginning of the program
            with open(file_path, "r") as infile:
                program = infile.read() + "\n" + program

    # drop the lines starting with `#include` in the program
    lines = program.split("\n")
    program = "\n".join(
        [line for line in lines if not line.startswith("#include")]
    ).strip()

    # write the completed program to the file named `completed_program.dl`
    new_program_path = os.path.join(
        os.path.dirname(program_path), "completed_program.dl"
    )
    with open(new_program_path, "w") as outfile:
        outfile.write(program)

    return new_program_path


def run_analyser_on_project(analyser_program_path, project_path):
    """Run the analyser on the project."""
    try:
        subprocess.run(
            [
                "souffle",
                analyser_program_path,
                "-F",
                project_path,
                "-D",
                project_path,
                "-w",
            ],
            check=True,
        )
    except Exception as e:
        Logger.error(f"Failed to run the analyser on {project_path}\n")
        Logger.error(e)


def is_number(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_correct_usage_facts(facts_dir):
    incorrect_usage_path = os.path.join(facts_dir, "incorrect_usage.csv")
    if not os.path.exists(incorrect_usage_path):
        Logger.error(f"{incorrect_usage_path} not found")
        return
    correct_usage_facts = []
    with open(incorrect_usage_path, "r") as infile:
        incorrect_usage_lines = infile.readlines()
        for line in incorrect_usage_lines:
            correct_usage_fact = Fact(
                "correct_usage",
                [
                    String(arg) if not is_number(arg) else Number(int(arg))
                    for arg in line.strip().split("\t")
                ],
            )
            correct_usage_facts.append(correct_usage_fact)
    return frozenset(correct_usage_facts)


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


def generate_models(s):
    result = []
    while s.check() == sat:
        model = s.model()
        result.append(model)
        # Create a new constraint that blocks the current model
        block = []
        for d in model:
            c = d()
            block.append(c != model[d])
        s.add(Or(block))
    return result


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
        if fact["symbolic"] == True:
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
        # raise Exception(f"Repair template for {api_signature} not found")
        Logger.error(f"Repair template for {api_signature} not found")
        return None

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


def get_domain_constraints_in_template(api_signature, slg_sym_consts):
    _, _, _, slg_domain_constraints = parse_template(api_signature, slg_sym_consts)
    return slg_domain_constraints


def get_symbolic_sign_facts_in_template(
    api_signature, project_facts_path, analyser_program
):
    """Get the symbolised facts from the original facts according to the repair template."""

    api_template = {
        "sym_flow_template": [
            "java.sql@PreparedStatement@executeQuery+java.sql@ResultSet@close",
            "java.io.DataOutputStream.writeLong@java.io.DataOutputStream.flush@java.io.DataOutputStream",
            "android.database@Cursor@close+android.database.sqlite@SQLiteDatabase@query",
            "java.util@Iterator@hasNext+java.util@Iterator@next",
            "java.io.PrintWriter@close",
            "java.util@Scanner@hasNext+java.util@Scanner@next",
            "android.app@Dialog@dismiss+android.app@Dialog@isShowing",
            "java.io@DataOutputStream+java.io@DataOutputStream@close",
        ],
        "sym_flow_template_2": [
            # "java.util@Iterator@hasNext+java.util@Iterator@next",
        ],
    }

    real_api_sig_map = {
        "java.util@Iterator@hasNext+java.util@Iterator@next": "java.util.Iterator.next()",
    }

    # load the facts
    ori_facts = load_facts(
        project_facts_path, analyser_program.declarations, analyser_program.inputs
    )

    # run the program to get auxiliary facts
    aux_program = Program(
        analyser_program.declarations,
        analyser_program.inputs,
        ["flow_reach", "var_dep"],
        analyser_program.rules,
        analyser_program.facts,
        analyser_program.symbols,
    )
    aux_facts = run_program(aux_program, ori_facts)

    all_facts = ori_facts | aux_facts

    def sym_flow_template(facts):
        starts = {f.head.args[0] for f in facts if f.head.name == "start"}
        finals = {f.head.args[0] for f in facts if f.head.name == "final"}
        catches = {
            (f.head.args[0], f.head.args[1]) for f in facts if f.head.name == "catch"
        }
        flow_facts = list(filter(lambda f: f.head.name == "flow", facts))
        # find the flow facts which do not connect with start and end to symbolise
        flow_facts_to_symbolise = set()
        for f in flow_facts:
            if (
                f.head.args[0] not in starts
                and f.head.args[1] not in finals
                and (f.head.args[0], f.head.args[1]) not in catches
            ):
                flow_facts_to_symbolise.add(f)

        return flow_facts_to_symbolise

    def sym_flow_template_2(ori_facts, aux_facts, real_api_sig):
        return set()

    for template_name, api_sigs in api_template.items():
        if api_signature in api_sigs:
            if template_name == "sym_flow_template":
                return sym_flow_template(ori_facts)
            elif template_name == "sym_flow_template_2":
                real_api_sig = real_api_sig_map[api_signature]
                return sym_flow_template_2(ori_facts, aux_facts, real_api_sig)
            else:  # sym_flow_template as the default
                return sym_flow_template(ori_facts)

    raise Exception(f"No template for api: {api_signature}")


def get_symbolic_sign_assigner(api_signature, added_slg_facts):
    # return the corresponding sign assigner for the api_signature

    api_signature_class1 = ["java.util@Iterator@hasNext+java.util@Iterator@next"]

    def assigner1(symbol_value_assigns, facts, added_slg_facts):
        # find the flows covered by the concretised added_slg_facts
        covered_flows = set()

        symbol_value_map = dict(symbol_value_assigns)

        # concretise the added_slg_facts
        concretised_added_slg_facts, _ = concretise_facts(
            added_slg_facts, symbol_value_map
        )

        # chain the flows from concretised added_slg_facts to form the longest paths
        added_flows = {f for f in concretised_added_slg_facts if f.head.name == "flow"}

        edges = [(f.head.args[0], f.head.args[1]) for f in added_flows]
        longest_paths_ = longest_paths(edges)

        # filter out the symbolic constants in the longest paths
        longest_paths_ = [
            [
                arg
                for arg in path
                if not (
                    isinstance(arg, SymbolicNumberWrapper)
                    or isinstance(arg, SymbolicStringWrapper)
                )
            ]
            for path in longest_paths_
        ]

        # for each longest path, find the flow facts from facts covered by the path
        for path in longest_paths_:
            for fact in facts:
                if fact.head.name == "flow" and (
                    fact.head.args[0],
                    fact.head.args[1],
                ) in zip(path, path[1:]):
                    covered_flows.add(fact)

        return {f: False for f in covered_flows}

    # if api_signature in api_signature_class1:
    return lambda x, y: assigner1(x, y, added_slg_facts)


def eval(mubench_json_path, synthesis_cache_folder, target_api_sig=None):
    mubench_json = json.load(open(mubench_json_path, "r"))

    Logger.info(f"Target API Signature: {target_api_sig}")
    Logger.info("=====================================")

    for api_sig in mubench_json:
        if target_api_sig:
            if api_sig != target_api_sig:
                continue
        analyser_program_path = os.path.join(
            synthesis_cache_folder, api_sig, "final_sat_program.dl"
        )
        if not os.path.exists(analyser_program_path):
            Logger.error(f"{api_sig} has no analyser program")
            continue

        # complete the program
        completed_program_path = complete_program(analyser_program_path)
        analyser_program = parse(completed_program_path)

        # get the symbolic constants for the api_sig to repair
        slg_sym_consts = get_sym_consts_in_template(api_sig)
        if not slg_sym_consts:
            Logger.error(f"No symbolic constants found for {api_sig}")
            continue

        # get the added facts for the api_sig to repair
        slg_facts = get_added_facts_in_template(api_sig, slg_sym_consts)

        # domain constraints
        domain_constraints = get_domain_constraints_in_template(api_sig, slg_sym_consts)

        for obj in mubench_json[api_sig]:

            # check if the model of the obj is already in the tmp folder
            if os.path.exists(f"tmp/{obj['id']}.model"):
                Logger.info(f"Repair for {obj['id']} already done")
                continue

            start_time = time.time()

            Logger.info(f"Repairing {obj['id']}")
            # generate facts
            facts_dir = generate_facts_for_object(obj)

            if not facts_dir:
                Logger.error(f"No facts found for {obj['id']}")
                continue

            # run the analyser on the facts to output incorrect_usage facts
            run_analyser_on_project(completed_program_path, facts_dir)

            # construct the correct_usage (target) facts according to incorrect_usage facts
            correct_usage_facts = get_correct_usage_facts(facts_dir)

            # load original facts
            facts = load_facts(
                facts_dir, analyser_program.declarations, analyser_program.inputs
            )

            # prepare the facts injected with symbolic facts for the repair
            sym_facts_from_original_facts = get_symbolic_sign_facts_in_template(
                api_sig, facts_dir, analyser_program
            )
            facts = {
                SymbolicSign(f) if f in sym_facts_from_original_facts else f
                for f in facts
            }
            all_facts = facts | slg_facts

            Logger.info(f"Computing constraints for {correct_usage_facts}.")

            # sign_assigner = get_symbolic_sign_assigner(api_sig, slg_facts)
            sign_assigner = None
            # repair one fact at a time
            repair_constraints = {}
            for correct_usage_fact in correct_usage_facts:
                Logger.info(f"Computing constraints for {correct_usage_fact}.")

                repair_constraints_ = symex(
                    analyser_program,
                    all_facts,
                    {correct_usage_fact},
                    domain_constraints,
                )

                if repair_constraints_ is None:
                    continue
                repair_constraints.update(repair_constraints_)

            end_time = time.time()

            if not repair_constraints:
                Logger.info(f"No repair found for {obj['id']}")
                continue

            Logger.info(
                f"Constraints computation for {obj['id']} done in {end_time - start_time}s"
            )

            # dump the models
            solver = Solver()
            with open(f"tmp/{obj['id']}.model", "w") as f:
                i = 0
                for k, v in repair_constraints.items():
                    solver.add(v.to_z3())
                    models = generate_models(solver)
                    if not models:
                        Logger.error(f"No model found for {obj['id']}")
                    for m in models:
                        f.write(f"Model {i}\n")
                        f.write(f"Model: {m}\n")
                        i += 1
                end_time = time.time()

                f.write(f"End to End Time: {end_time - start_time}s\n")

            Logger.info(f"Repair for {obj['id']} done in {time.time() - start_time}s")


if __name__ == "__main__":
    # load mubench.json and get all the api signatures
    mubench_json_path = "/root/amuse/evaluation/mubench.json"
    mubench_json = json.load(open(mubench_json_path, "r"))
    api_sigs = list(mubench_json.keys())
    # eval all the api signatures
    for api_sig in api_sigs:
        eval(
            mubench_json_path,
            "/root/amuse/cache",
            target_api_sig=api_sig,
        )
