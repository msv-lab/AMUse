from subprocess import Popen, PIPE
import json
from pathlib import Path
import itertools
import csv

from amuse.souffle import parse, Souffle, Rule, Literal, Program, pprint
from amuse.souffle.souffle_parser import (
    Variable,
    Unification,
    Literal,
    Rule,
    Program,
    String,
    Number,
)
from amuse.utils.logger import Logger

SYM = "symbol"
NUM = "number"


def load_facts(
    directory,
    declarations,
    fact_names,
    check_func,
):
    facts_pattern = Path(directory).glob("*.facts")
    csv_pattern = Path(directory).glob("*.csv")

    facts = list()
    target_files = itertools.chain(facts_pattern, csv_pattern)
    for file in target_files:
        relation_name = file.stem

        if fact_names and relation_name not in fact_names:
            continue  # skip non-input facts

        with file.open() as csvfile:
            reader = csv.reader(csvfile, delimiter="\t")
            for row in reader:
                try:
                    facts.append(
                        Rule(
                            Literal(
                                relation_name,
                                [
                                    to_symlog_arg(
                                        ra,
                                        declarations[relation_name][idx],
                                        check_func,
                                    )
                                    for idx, ra in enumerate(row)
                                ],
                                True,
                            ),
                            [],
                        )
                    )
                except KeyError:
                    Logger.info(
                        f"Relation {relation_name} is not declared in the program.",
                        exc_info=False,
                    )
                    exit(1)
                except IndexError:
                    Logger.error(
                        f"Too many arguments for relation {relation_name}.",
                        exc_info=False,
                    )
                    exit(1)
    return facts


def to_symlog_arg(
    raw_arg,
    decl_type,
    check_func=None,
):
    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    if check_func:
        raw_arg = check_func(raw_arg)

    if decl_type == SYM:
        return String(raw_arg)
    elif decl_type == NUM:
        try:
            return Number(int(raw_arg))
        except ValueError:
            Logger.error(
                f"Argument {raw_arg} is not a valid number for type {decl_type}.",
                exc_info=False,
            )
    else:
        raise ValueError(f"unknown type {type(raw_arg)}")


def escape_invalid_json_chars(json_str):
    return json_str.replace("\\;", "\\\\;")


def base_provenance(program_path, facts_folder, target_fact_str):
    """Returns the provenance of the given fact in the given program."""

    # # construct the full program
    # with open(program_path, "r") as f:
    #     program_str = f.read()
    #     program = parse(program_str)

    # # if the program has include directives, load the included programs
    # if program.include:
    #     for include in program.include:
    #         directive = str(include).strip('"')
    #         with open(directive, "r") as f:
    #             program_str += f.read()

    #     program = parse(program_str)

    # facts = (
    #     load_facts(facts_folder, program.declarations, program.inputs, None)
    #     if not facts_folder == ""
    #     else []
    # )

    # program = Program(
    #     program.declarations,
    #     program.inputs,
    #     program.outputs,
    #     [],
    #     program.rules + facts,
    # )

    # # save the program to a file
    # new_program_path = "debug_program.dl"
    # with open(new_program_path, "w") as f:
    #     f.write(pprint(program))

    # debug
    new_program_path = program_path

    try:
        cmd = [
            "souffle",
            "-t",
            "explain",
            new_program_path,
            "-w",
        ]

        try:
            interactive_process = Popen(
                cmd,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
            )

            commands = [
                f"setdepth {1e9}",  # set a large number
                "format json",
                "explain "
                + "".join(
                    target_fact_str.rsplit(".", 1)
                ).strip(),  # remove the '.' for identifying a fact and \n.
            ]
            output, errors = interactive_process.communicate(
                "\n".join(commands).encode()
            )

            if interactive_process.returncode != 0:
                raise RuntimeError(
                    f"'souffle' command failed with error: {errors.decode()}"
                )
        except Exception as e:
            print(f"Error executing external command: {e}")
            raise

        try:
            output = escape_invalid_json_chars(output.decode())
            data = json.loads(output)
        except json.JSONDecodeError:
            print("Error parsing JSON output from Souffle")
            return None

        assert "proof" in data, "Bug in Souffle?"

        # debug: dump the json output to a file
        with open("output.json", "w") as f:
            json.dump(data, f, indent=4)

        if "Tuple not found" in str(data["proof"]) or "Relation not found" in str(
            data["proof"]
        ):
            return None

    except IOError as e:
        print(f"File operation error: {e}")
        raise


if __name__ == "__main__":
    # program_path = "/root/amuse/debug_analyser2.dl"
    # target_fact_str = 'may_not_call_name_followed_til_exit("android.database.sqlite.SQLiteDatabase.query", 3, "com.meiji.toutiao.database.dao.MediaChannelDao.queryIsExist(java.lang.String)", "android.database.Cursor.close")'

    # program_path = "/root/amuse/cache/javax.swing@JFrame@pack+javax.swing@JFrame@setVisible/synthe_program_4.dl"

    # target_fact_str = 'must_call_preceded("java.awt.Window.setVisible(boolean)", 4, "edu.stanford.nlp.trees.tregex.gui.InputPanel.displayTsurgeonHelp()", "java.awt.Window.pack()", 2, "edu.stanford.nlp.trees.tregex.gui.InputPanel.displayTsurgeonHelp()")'

    # facts_folder = "/root/amuse/cache/javax.swing@JFrame@pack+javax.swing@JFrame@setVisible/raw_19"

    # base_provenance(program_path, facts_folder, target_fact_str)

    # program_path = "/root/amuse/cache/javax.swing@JFrame@pack+javax.swing@JFrame@setVisible/synthe_program_4.dl"

    # target_fact_str = 'may_not_call_preceded_simple("java.awt.Window.setVisible(boolean)", "errorWindow", 22, "org.fourthline.cling.support.shared.Main$5.run()", "java.awt.Window.pack()", "errorWindow", 19, "org.fourthline.cling.support.shared.Main$5.run()")'

    # facts_folder = "/root/amuse/cache/javax.swing@JFrame@pack+javax.swing@JFrame@setVisible/raw_3"

    program_path = "/root/amuse/tmp/negated.dl"

    target_fact_str = 'correct_usage("java.io.ByteArrayOutputStream.toByteArray()", 9, "baos", "org.apache.gora.accumulo.store.PartitionTest.encl(long)", 1)'

    facts_folder = ""

    base_provenance(program_path, facts_folder, target_fact_str)
