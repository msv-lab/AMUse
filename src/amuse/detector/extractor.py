import re
import json
from pathlib import Path
from subprocess import run
from amuse.config import config
from amuse.detector.condition_parser import (
    generate_condition_facts,
    simple_conjunction_parser,
)
from parsy import ParseError


methods = {}
relationships = {}

FACTS = Path("/root/amuse/src/amuse/detector/facts")

global project_type
flow = "flow"
start = "start"
final = "final"
label = "label"
instance_call = "instance_call"
method = "method"
variable = "variable"
defined = "defined"
assign = "assign"
value = "value"
depth = "depth"
depth_statement = "depth_statement"
assign_type = "assign_type"
instance_variables = "instance_variables"
initialisation = "initialisation"
condition = "condition"
arguments = "arguments"
argument = "argument"
condition_variable = "condition_variable"
condition_expression = "condition_expression"
negated_condition_expression = "negated_condition_expression"
predicate_condition = "predicate_condition"
negated_predicate_condition = "negated_predicate_condition"
negated_condition = "negated_condition"
null_check = "null_check"
not_null_check = "not_null_check"
try_file = "try"
exceptions = "exceptions"
exceptions_pos = "exceptions_pos"
throw = "throw"
exceptions_hierarchy = "exceptions_hierarchy"
return_file = "return"
return_value = "return_value"
assert_file = "assert"
conjunction = "conjunction"
disjunction = "disjunction"
static_method = "static_method"

useMethodNameFacts = (
    True  # name the fact file as datalog declaration or the method name
)

# path = sys.argv[1]

COMPILE_JAVA_FILE = [
    "javac",
    "-cp",
    "/root/amuse/src/amuse/detector/*:/root/amuse/src/ammuse/detector/",
    "/root/amuse/src/amuse/detector/GetExceptionsHierarchy.java",
]
RUN_JAVA_FILE = [
    "java",
    "-cp",
    "/root/amuse/src/amuse/detector/*:/root/amuse/src/amuse/detector/",
    "GetExceptionsHierarchy",
]
# "-cp", "/root/amuse/src/ammuse/detector/*:/root/amuse/src/ammuse/detector/",


class Extractor:
    @staticmethod
    def extract_callgraph_facts(path):
        print("extracting the call graph now")
        print(path)
        global project_type
        f = open(str(path), "r")
        data = json.load(f)
        project_type = Extractor.define_proj_name(str(path))
        # Extractor.get_try_exception_hierchy(data)
        # Extractor.get_argument(data)
        # Extractor.get_arguments(data)
        # Extractor.get_exceptions(data)
        # Extractor.get_exceptions_pos(data) #TODO: define 'exceptions_pos' in base.dl
        # Extractor.get_flow(data)
        # Extractor.get_start(data)
        # Extractor.get_depth_hard_code(data)
        # Extractor.get_final(data)
        # Extractor.get_depth_with_statement(data)
        # Extractor.get_label(data)
        # Extractor.get_instance_call(data)
        # Extractor.get_method(data)
        # Extractor.get_variable(data) # possible remove this
        # Extractor.get_value(data)
        # Extractor.get_defined(data) # TODO: define 'defined' in base.dl
        # Extractor.get_initialisation(data)  # TODO: define constructor_call in base.dl
        # Extractor.get_condition(data)  # TODO: replace condition with if
        # Extractor.get_condition_variable(data)  # TODO: replace it with binary operator
        # Extractor.get_branch_flow(data)
        # get_condition_expression(data) # possibly remove
        # Extractor.get_negation_condition(data)  # possibly remove
        # Extractor.get_try(data)
        # Extractor.get_assert(data)
        # Extractor.get_not_null_check(data)  # possibly remove this TODO: replace it with if and binary operator
        # Extractor.get_return(data)
        # Extractor.get_assign(data) #TODO: replace it with assigned
        # Extractor.get_condition_expression(data)
        # Extractor.get_static_call(data)
        # Extractor.get_null_check(data) #TODO: replace it with if and binary operator
        # Extractor.get_variable_type(data)
        # Extractor.get_throws(data)
        # Extractor.get_instance_variables(data)
        # Extractor.get_return_value(data)
        f.close()

        # supplementary information

    @staticmethod
    def define_proj_name(path):
        path = re.search(
            str(config.output_root / config.json_facts_root) + "/(.+)", path
        ).group(1)
        return re.sub("\.(json)", "", path)

    @staticmethod
    def create_fact_file(datalog_type, element):
        fl = config.output_root / config.facts_root / project_type

        if useMethodNameFacts:
            signature = element["methodSignature"]
            p = str(re.search("#(\S+)", signature).group(1))
            fl = fl / p

            if not fl.exists():
                fl.mkdir(parents=True, exist_ok=True)
            fle = fl / str(datalog_type + ".facts")

        else:
            if not fl.exists():
                fl.mkdir(parents=True, exist_ok=True)
            fle = fl / str(datalog_type + ".facts")

        return open(fle, "w")

    @staticmethod
    def get_flow(data):
        for element in data:
            file = Extractor.create_fact_file(flow, element)

            graph = element["methodGraph"]
            lstGraph = re.split("\n", graph)

            for l in lstGraph:
                if re.search("\d+ \-\> \d+", l):
                    l = re.sub("\s*\-\>\s*", "\t", l)
                    l = re.sub("\s*\;", "", l)
                    l = re.sub("^\s*", "", l)
                    l = re.sub("\[.+\]", "", l)
                    file.write(l + "\n")

            file.close()

    @staticmethod
    def get_instance_variables(data):
        with open("instance_variables.txt") as f:
            lines = f.readlines()
            for element in data:
                file = Extractor.create_fact_file(instance_variables, element)
                graph = element["methodGraph"]
                lstGraph = re.split("\n", graph)
                for line in lines:
                    file.write(line + "\n")
                file.close()

    @staticmethod
    def get_start(data):
        for element in data:
            file = Extractor.create_fact_file(start, element)
            graph = element["methodGraph"]
            lstGraph = re.split("\n", graph)
            for l in lstGraph:
                if re.search("\d+ \-\> \d+", l):
                    l = re.sub("\s*", "", l)
                    l = re.sub("\-\>.*", "", l)
                    file.write(l + "\n")
                    break
            file.close()

    @staticmethod
    def get_branch_flow(data):
        for element in data:
            true_file = Extractor.create_fact_file("true_flow", element)
            false_file = Extractor.create_fact_file("false_flow", element)

            graph = element["methodGraph"]
            lstGraph = re.split("\n", graph)
            for l in lstGraph:
                if re.search('label="\((TRUE|FALSE) (\d+) (\d+)\)', l):
                    matches = re.findall("\((TRUE|FALSE) (\d+) (\d+)\)", l)
                    for x in matches:
                        branch = x[0]
                        condition = x[1]
                        next = x[2]
                        content = condition + "\t" + next + "\n"
                        if branch == "TRUE":
                            true_file.write(content)
                            continue
                        false_file.write(content)

            true_file.close()
            false_file.close()

    @staticmethod
    def get_final(data):
        for element in data:
            file = Extractor.create_fact_file(final, element)

            graph = element["methodGraph"]
            lstGraph = re.split("\n", graph)
            numbers = []
            for l in lstGraph:
                g = re.search(r"(\d+) \-\> (\d+)", l)
                if g:
                    numbers.append(g.group(1))
                    numbers.append(g.group(2))
            file.write(max(numbers))
            file.close()

    # @staticmethod
    # def get_label(data):
    #     for element in data:
    #         file = Extractor.create_fact_file(label, element)
    #         graph = element["methodGraph"]
    #         lstGraph = re.split("\n", graph)
    #         numbers = []
    #         for l in lstGraph:
    #             if re.search("\d+ \-\> \d+", l):
    #                 l = re.sub("\s*", "", l)
    #                 l = re.sub("\-\>.*", "", l)

    #                 numbers.append(l)
    #         num_list = [int(i) for i in numbers]
    #         sorted_num_list = sorted(num_list)
    #         for num in sorted_num_list:
    #             file.write(str(num) + "\n")
    #         file.close()
    @staticmethod
    def get_label(data):
        for element in data:
            file = Extractor.create_fact_file(label, element)
            graph = element["methodGraph"]
            lstGraph = re.split("\n", graph)
            numbers = []
            for l in lstGraph:
                if re.search("(\d+) \[shape", l):
                    numbers.append(re.search("(\d+) \[shape", l).group(1))
            num_list = [int(i) for i in numbers]
            sorted_num_list = sorted(num_list)
            for num in sorted_num_list:
                file.write(str(num) + "\n")
            file.close()

    @staticmethod
    def get_instance_call(data):
        for element in data:
            file = Extractor.create_fact_file(instance_call, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split('"];\n', extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)

                if re.search("class: ", lst):
                    matchObj = re.search("class: (.+), method: (.+)\(.*\)", lst)

                    method_call = matchObj.group(1) + "." + matchObj.group(2)

                    method = matchObj.group(2)

                    # in case the methods are called with chained methods, escape the brackets and dots
                    one = re.sub(r"\(", "\(", method)
                    two = re.sub(r"\)", "\)", one)
                    cleaned_method = re.sub(r"\.", "\.", two)

                    pattern = "!?([^\(\) ]+)\.{}".format(re.escape(cleaned_method))

                    if re.search(pattern, lst):
                        variable = re.search(pattern, lst).group(1)

                        file.write(
                            variable + "\t" + method_call + "\t" + node_label + "\n"
                        )
            file.close()

    @staticmethod
    def get_static_call(data):
        for element in data:
            file = Extractor.create_fact_file(static_method, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split('"];\n', extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)

                if re.search("class: ", lst):
                    matchObj = re.search("class: (.+), method: ([^()]+)\(.*\)", lst)

                    method_call = matchObj.group(1) + "." + matchObj.group(2)

                    file.write(method_call + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_depth_hard_code(data):
        for element in data:
            file = Extractor.create_fact_file(depth, element)

            for i in range(10 + 1):
                for x in range(i):
                    file.write(str(x) + "\t" + str(i) + "\n")

            file.close()

    @staticmethod
    def get_depth_with_statement(data):
        for element in data:
            file = Extractor.create_fact_file(depth_statement, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split('"];\n', extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)

                if re.search("(\d+) \d+ -", lst):
                    matchObj = re.search("(\d+) \d+ -", lst).group(1)

                    file.write(matchObj + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_argument(data):
        for element in data:
            file = Extractor.create_fact_file(argument, element)
            file.close()
            continue
            # no need to write by checking the graph
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for l in lstGraph:
                node_label = re.sub("\s*\[+.*", "", l)
                if re.search("(class).*(method)", l):
                    content = re.search("method: (.+)\((.+|)\)", l).group(2)

                    if len(content) != 0:
                        args = [arg.strip() for arg in content.split(",")]

                        for idx, arg in enumerate(args):
                            file.write(arg + "\t" + node_label + "\t" + str(idx) + "\n")

            file.close()

    @staticmethod
    def get_arguments(data):
        for element in data:
            file = Extractor.create_fact_file(arguments, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for l in lstGraph:
                node_label = re.sub("\s*\[+.*", "", l)
                if re.search("(class).*(method)", l):
                    content = re.search("method: (.+)\((.+|)\)", l).group(2)

                    if len(content) != 0:
                        args = [arg.strip() for arg in content.split(",")]

                        for arg in args:
                            file.write(arg + "\t" + node_label + "\n")

                        # if len(args) == 2 or len(args) > 2:
                        #   for index in range(0,2):
                        #     file.write(args[index] + "\t")
                        # else:
                        #   for arg in args:
                        #     file.write(arg + "\t" + " " + "\t")

                        # file.write(node_label + "\n")

            file.close()

    @staticmethod
    def get_try(data):
        for element in data:
            file = Extractor.create_fact_file(try_file, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                if re.search(r"label=\"CATCH", str(lst)):
                    node_label = re.sub("\s*\[+.*", "", lst)
                    new_regex = "([.\s\S]+[^\d]" + node_label.rstrip() + " \[shape=)"
                    filtered = re.search(new_regex, extracted).group(1)
                    try_line = re.findall("\d+.+TRY_.+];\n", filtered)[-1]
                    try_label = re.sub("\s*\[+.*", "", try_line)
                    file.write(try_label.rstrip() + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_exceptions_pos(data):
        for element in data:
            file = Extractor.create_fact_file(exceptions_pos, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                if re.search(r"label=\"CATCH", str(lst)):
                    node_label = re.sub("\s*\[+.*", "", lst)
                    exception_type = re.search(
                        'CATCH\s+\d+ \d+ - (.+) \S+ "]', str(lst)
                    ).group(1)
                    file.write(exception_type + "\t" + node_label + "\n")

            file.close()

    @staticmethod
    def get_throws(data):
        for element in data:
            file = Extractor.create_fact_file(throw, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                if re.search(r"label=\"CATCH", str(lst)):
                    node_label = re.sub("\s*\[+.*", "", lst)
                    exception_type = re.search(
                        "CATCH  \d+ \d+ - (.+?) ", str(lst)
                    ).group(1)
                    file.write(exception_type + "\t" + node_label + "\n")

            file.close()

    @staticmethod
    def get_exceptions(data):
        for element in data:
            file = Extractor.create_fact_file(exceptions, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                if re.search(r"label=\"CATCH", str(lst)):
                    node_label = re.sub("\s*\[+.*", "", lst)
                    exception_type = re.search(
                        'CATCH\s+\d+ \d+ - (.+) \S+ "]', str(lst)
                    ).group(1)
                    file.write(exception_type + "\n")

            file.close()

    @staticmethod
    def get_try_exception_hierchy(data):
        for element in data:
            file = Extractor.create_fact_file(exceptions_hierarchy, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                if re.search(r"label=\"CATCH", str(lst)):
                    node_label = re.sub("\s*\[+.*", "", lst)
                    exception_type = re.search(
                        'CATCH\s+\d+ \d+ - (.+) \S+ "]', str(lst)
                    ).group(1)
                    run(RUN_JAVA_FILE + [exception_type], stdout=file)
            file.close()

    @staticmethod
    def get_method(data):
        for element in data:
            file = Extractor.create_fact_file(method, element)
            graph = element["methodGraph"]
            lstGraph = re.split("\n", graph)
            for l in lstGraph:
                if re.search("(class).*(method)", l):
                    if (re.search("^[0-9]+\s*", l)) and (
                        Extractor.is_static_method(l) is False
                    ):
                        class_name = re.sub(".*\-\s(class)\:\s*", "", l)
                        class_name_2 = re.sub(",\s*(method).*", "", class_name)
                        method_name = re.sub(".*,\s*(method)\:\s*", "", class_name)
                        method_name_2 = re.sub('\s*"\];\s*$', "", method_name)
                        method_name_3 = re.sub("\(.*\)", "", method_name_2)
                        file.write(class_name_2 + "." + method_name_3 + "\n")
            file.close()

    @staticmethod
    def get_condition(data):
        for element in data:
            file = Extractor.create_fact_file(condition, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)

                if re.search("shape=diamond", lst):
                    # condition =re.search("\"(.*?)\"", lst).group(1).split(' - ')[1].strip()
                    file.write(node_label + "\n")
            file.close()

    @staticmethod
    def write_condition_parser(element, facts, node_label, output):
        for expression in facts:
            if expression[0][0] == "(" and expression[0][-1] == ")":
                expression[0] = expression[0][1:-1]

            output.write(
                expression[0]
                + "\t"
                + expression[1]
                + "\t"
                + expression[2]
                + "\t"
                + node_label
                + "\n"
            )

    @staticmethod
    def write_conjunction_disjunction(element, facts, node_label, output):
        for fact in facts:
            # splitted = fact.split(" ")
            output.write(fact[0] + "\t" + fact[1] + "\t" + node_label + "\n")

    @staticmethod
    def write_condition_predicate(element, facts, node_label, output):
        for predicate in facts:
            output.write(predicate[0] + "\t" + node_label + "\n")

    @staticmethod
    def generate_condition_results(data):  # we attempt to parse the conditions
        try:
            return generate_condition_facts(data)
        except IndexError:
            pass
        except ParseError:
            pass

        try:
            return simple_conjunction_parser(data)
        except IndexError:
            pass
        return None

    @staticmethod
    def get_condition_expression(data):
        for element in data:
            condition_file = Extractor.create_fact_file(condition_expression, element)
            negated_condition_file = Extractor.create_fact_file(
                negated_condition_expression, element
            )

            predicate_condition_file = Extractor.create_fact_file(
                predicate_condition, element
            )

            negated_predicate_condition_file = Extractor.create_fact_file(
                negated_predicate_condition, element
            )

            conjunction_file = Extractor.create_fact_file(conjunction, element)

            disjunction_file = Extractor.create_fact_file(disjunction, element)

            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                ok = False
                if re.search("shape=diamond", lst):
                    condition = re.search('label="\d+ \d+ - (.+) (- class:.+)"];', lst)
                    condition2 = re.search('label="\d+ \d+ - (.+) "];', lst)

                    if condition:
                        condition = condition.group(1)

                        ok = True

                    if condition2:
                        condition = condition2.group(1)
                        ok = True

                    # ok = True
                    # if condition:
                    #   content = condition.group(1)
                    #   if re.search('(.+) - ', content):
                    #     condition = re.search('(.+) - ',content)

                    #     if condition:
                    #       condition = re.search('(.+) - ',content).group(1)

                    #       ok = True
                    # else:
                    #   condition = re.search('label=\"\d+ - (.+) \"];', lst)

                    #   if condition:
                    #     condition = re.search('label=\"\d+ - (.+) \"];', lst).group(1)
                    #     ok = True

                    if ok:
                        result = Extractor.generate_condition_results(condition)
                        if result is not None:
                            Extractor.write_condition_parser(
                                element,
                                result["conditions"],
                                node_label,
                                condition_file,
                            )
                            Extractor.write_condition_parser(
                                element,
                                result["negated_conditions"],
                                node_label,
                                negated_condition_file,
                            )
                            # file.write(result + "\t" + node_label + "\n")

                            Extractor.write_condition_predicate(
                                element,
                                result["predicates"],
                                node_label,
                                predicate_condition_file,
                            )

                            Extractor.write_condition_predicate(
                                element,
                                result["negated_predicates"],
                                node_label,
                                negated_predicate_condition_file,
                            )

                            Extractor.write_conjunction_disjunction(
                                element,
                                result["conjunctions"],
                                node_label,
                                conjunction_file,
                            )
                            Extractor.write_conjunction_disjunction(
                                element,
                                result["disjunctions"],
                                node_label,
                                disjunction_file,
                            )

            condition_file.close()
            negated_condition_file.close()
            predicate_condition_file.close()
            negated_predicate_condition_file.close()
            conjunction_file.close()
            disjunction_file.close()

    @staticmethod
    def get_condition_variable(data):
        for element in data:
            file = Extractor.create_fact_file(condition_variable, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                matchObj = re.search(
                    " !?\(?(\S+) (!=|==|<|<=|>|>=) ([a-zA-Z_][^() ]*)\)?", lst
                )
                if matchObj:
                    # condition =re.search("\"(.*?)\"", lst).group(1).split(' - ')[1].strip()
                    variable = matchObj.group(1)
                    operator = matchObj.group(2)
                    rhs_variable = matchObj.group(3)
                    file.write(
                        variable
                        + "\t"
                        + operator
                        + "\t"
                        + rhs_variable
                        + "\t"
                        + node_label
                        + "\n"
                    )
            file.close()

    @staticmethod
    def get_assert(data):
        for element in data:
            file = Extractor.create_fact_file(assert_file, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                matchObj = re.search(
                    "assert \S+ (!=|==|<|<=|>|>=) ([a-zA-Z_][^() ]*)\)?", lst
                )
                if matchObj:
                    file.write(node_label + "\n")
            file.close()

    @staticmethod
    def get_negation_condition(data):
        for element in data:
            file = Extractor.create_fact_file(negated_condition, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)

                if re.search("class: ", lst):
                    matchObj = re.search("class: (\S+), method: (\S+)\(.*\)", lst)
                    # method_call = matchObj.group(1) + '.' + matchObj.group(2)

                    if not matchObj:
                        continue

                    pattern = r"!(.+)\.{}".format(re.escape(matchObj.group(2))).strip()
                    variableMatchObject = re.search(pattern, lst)

                    if variableMatchObject:
                        variable = variableMatchObject.group(1)

                        file.write(node_label + "\n")
                else:
                    variableMatchObject = re.search(r"!\((\S+)", lst)
                    if variableMatchObject:
                        variable = variableMatchObject.group(1)

                        file.write(node_label + "\n")
            file.close()

    @staticmethod
    def get_value(data):
        for element in data:
            file = Extractor.create_fact_file(value, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                if re.search("\[.+ - \S+ \S+ = (\S+)", lst):
                    value_assigned = re.search("\[.+ - \S+ \S+ = (\S+)", lst).group(1)
                    file.write(value_assigned + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_assign(data):
        for element in data:
            file = Extractor.create_fact_file(assign, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                if re.search("\[.+ - \S+ (\S+) =", lst):
                    assigned = re.search("\[.+ - \S+ (\S+) =", lst).group(1)
                    file.write(assigned + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_variable_type(data):
        for element in data:
            file = Extractor.create_fact_file(assign_type, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                if re.search("\[.+ - (\S+) (\S+) =", lst):
                    variable_type = re.search("\[.+ - (\S+) (\S+) =", lst).group(1)
                    assigned = re.search("\[.+ - (\S+) (\S+) =", lst).group(2)
                    file.write(variable_type + "\t" + assigned + "\n")
            file.close()

    @staticmethod
    def get_return(data):
        for element in data:
            file = Extractor.create_fact_file(return_file, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                if re.search("return ", lst):
                    # method_call = matchObj.group(1) + '.' + matchObj.group(2)
                    file.write(node_label + "\n")
            file.close()

    @staticmethod
    def get_return_value(data):
        for element in data:
            file = Extractor.create_fact_file(return_value, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                if re.search('return (.+) "\]; ', lst):
                    value = re.search('return (.+) "\]; ', lst).group(1)
                    # method_call = matchObj.group(1) + '.' + matchObj.group(2)
                    file.write(value + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_null_check(data):
        for element in data:
            file = Extractor.create_fact_file(null_check, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                matchObj = re.search("[\(]?(\S+) == null|null == (\S+)[\)]?", lst)
                if matchObj:
                    # condition =re.search("\"(.*?)\"", lst).group(1).split(' - ')[1].strip()
                    variable = ""
                    if matchObj.group(1) is not None:
                        variable = matchObj.group(1)
                    else:
                        variable = matchObj.group(2)
                    file.write(variable + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_not_null_check(data):
        for element in data:
            file = Extractor.create_fact_file(not_null_check, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                matchObj = re.search("shape=diamond.+ (\S+) != null", lst)
                if matchObj:
                    # condition =re.search("\"(.*?)\"", lst).group(1).split(' - ')[1].strip()
                    variable = matchObj.group(1)
                    file.write(variable + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_initialisation(data):
        for element in data:
            file = Extractor.create_fact_file(initialisation, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)
                intialisation_statement = re.search(r"new ([a-zA-Z\.0-9]+)", lst)
                if re.search("shape=rectangle", lst) and intialisation_statement:
                    content = intialisation_statement.group(1)
                    file.write(content + "\t" + node_label + "\n")
            file.close()

    @staticmethod
    def get_variable(data):
        for element in data:
            file = Extractor.create_fact_file(variable, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)
            unique_var = set()
            for lst in lstGraph:
                # we need to check for statement here for the default case in the switch statement
                if re.search("shape=rectangle", lst) and not re.search(
                    'label="\d+ \d+ (TRY|CATCH|FINALLY|STATEMENT)', lst
                ):
                    print(lst)
                    content = lst.split(" - ")[1]
                    if re.search(r"\S+ =", content):
                        variable_definition = (
                            re.search(r"\S+ =", content).group(0).split(" ")[0]
                        )
                        if variable_definition not in unique_var:
                            file.write(variable_definition + "\n")
                            unique_var.add(variable_definition)
                    elif re.search(r"\S+ \S+ \"", content):
                        declaration = (
                            re.search(r"\S+ \S+ \"", content).group(0).split(" ")[1]
                        )
                        if declaration not in unique_var:
                            file.write(declaration + "\n")
                            unique_var.add(declaration)
            file.close()

    @staticmethod
    def get_defined(data):
        for element in data:
            file = Extractor.create_fact_file(defined, element)
            graph = element["methodGraph"]
            extracted = re.search("([0-9]+ \[[\s\S]+\];\n)+", graph).group(0)
            lstGraph = re.split("\n", extracted)

            for lst in lstGraph:
                node_label = re.sub("\s*\[+.*", "", lst)

                if re.search("shape=rectangle", lst) and re.search(r"\S+ =", lst):
                    content = lst.split(" - ")[1]
                    variable_definition = re.search(r"\S+ =", content)

                    if variable_definition:
                        variable_definition = variable_definition.group(0).split(" ")[0]
                        file.write(variable_definition + "\t" + node_label + "\n")

            file.close()

    @staticmethod
    def is_static_method(line):
        result = False
        # Check for static method such as: java.nio.ByteBuffer.allocate(data.length)
        if re.search("(java)\..*\.[A-Z]+.*\..*\(.*\)", line):
            result = True
        return result
