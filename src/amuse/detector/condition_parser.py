from dataclasses import dataclass, fields
import dataclasses
import json
import re
from typing import Optional, Union, List
from parsy import regex, string, seq, generate


@dataclass
class Argument:
    value: Union[int, str]


@dataclass
class Method:
    name: str
    arguments: Optional[List[Argument]]


@dataclass
class Variable:
    name: str


@dataclass
class MethodInvocation:
    variable_name: str
    method: Method


@dataclass
class Condition:
    lhs: Union[MethodInvocation, Variable]
    operator: str
    rhs: Union[MethodInvocation, str, int, bool]


@dataclass
class String:
    value: str


@dataclass
class Number:
    value: str


@dataclass
class FieldAccess:
    variable_name: Variable
    field: str


@dataclass
class StaticVar:
    value: str


@dataclass
class MathExpression:
    lhs: Union[Variable, Number]
    operator: str
    rhs: Union[Variable, Number]


@dataclass
class Negation:
    content: Union[MethodInvocation, Condition, Variable, "Negation", FieldAccess]


character = regex("[a-zA-Z]")
number = regex("[0-9]")
variable_name = regex("(_|\$|[a-zA-Z])[a-zA-Z0-9_]*")
number_no_dict = regex("[0-9]+")
numbers = seq(value=regex("[0-9]+")).combine_dict(Number)
padding = regex(r"\s*")  # optional whitespace
static_variable = seq(value=regex("([^.)]+\.)+([^.)]+)")).combine_dict(StaticVar)


OPEN_BRACKET = string("(")
CLOSE_BRACKET = string(")")
EQUALITY = string("==")
NOT_EQUAL = string("!=")
LESS_THAN = string("<")
LESS_EQUAL = string("<=")
MORE_THAN = string(">")
MORE_EQUAL = string(">=")
NEGATION = string("!")
BOOL = string("true") | string("false")

PLUS = string("+")
MINUS = string("-")
MULTIPLY = string("*")
DIVIDE = string("/")

OR = string("||")
AND = string("&&")

SINGLE_QUOTATION = string("'")
DOUBLE_QUOTATION = string('"')

SINGLE_QUOTATION | DOUBLE_QUOTATION

MATH_OPERATOR = PLUS | MINUS | MULTIPLY | DIVIDE

CONDITIONAL_OPERATOR = (
    EQUALITY
    | NOT_EQUAL
    | LESS_EQUAL
    | MORE_EQUAL
    | LESS_THAN
    | MORE_THAN
    | AND
    | OR
    | string("instanceof")
)


variable = seq(name=padding.then(variable_name).skip(padding)).combine_dict(Variable)

string_text = seq(
    _pre=SINGLE_QUOTATION, value=regex("[^']+").optional(), _post=SINGLE_QUOTATION
).combine_dict(String) | seq(
    _pre=DOUBLE_QUOTATION, value=regex('[^"]+').optional(), _post=DOUBLE_QUOTATION
).combine_dict(
    String
)


def transform_args(arguments):
    output = []
    for arg in arguments:
        output.append(
            json.dumps(
                {
                    "class_content": dataclasses.asdict(arg),
                    "class_name": type(arg).__name__,
                }
            )
        )
    return output


@generate
def arg_gen():
    result = yield (
        instance_invocation
        | static_variable
        | method
        | variable
        | numbers
        | string_text
    ).map(
        # lambda x: d(x)
        lambda x: json.dumps(
            {"class_content": dataclasses.asdict(x), "class_name": type(x).__name__}
        )
    )

    return result


def classFromArgs(className, argDict):
    fieldSet = {f.name for f in fields(className) if f.init}
    filteredArgDict = {k: v for k, v in argDict.items() if k in fieldSet}
    return className(**filteredArgDict)


def convert_back_to_dataclass(x):
    transformed = []
    for item in x:
        obj = None
        if item:
            obj = json.loads(item)

        if obj and obj["class_name"]:
            transformed.append(
                classFromArgs(globals()[obj["class_name"]], obj["class_content"])
            )
        else:
            transformed.append(item)
    return transformed


arguments = (
    arg_gen.many()
    .concat()
    .sep_by(padding.then(padding + string(",") + padding).skip(padding))
    .map(lambda x: convert_back_to_dataclass(x))
)

method = seq(
    name=padding.then(regex("[^\)(, ]+")),
    _=OPEN_BRACKET.skip(padding),
    arguments=arguments.optional(),
    _post=padding.then(CLOSE_BRACKET),
).combine_dict(Method)

instance_invocation = seq(
    variable_name=padding.then(variable_name).skip(padding),
    _=string("."),
    method=method,
).combine_dict(MethodInvocation)


fieldaccess = seq(
    variable_name=variable_name, _=string("."), field=regex("[^\)( ]+")
).combine_dict(FieldAccess)


possible_condition = padding + OPEN_BRACKET + (
    instance_invocation | fieldaccess | method | variable
) + padding + CLOSE_BRACKET | (instance_invocation | fieldaccess | method | variable)

math_expression = seq(
    lhs=variable | numbers,
    _=padding,
    operator=MATH_OPERATOR,
    _e=padding,
    rhs=variable | numbers,
).combine_dict(MathExpression)


@generate
def condition():
    return (
        yield (
            seq(_=NEGATION.skip(padding), content=possible_condition).combine_dict(
                Negation
            )
            | math_expression
            | instance_invocation
            | fieldaccess
            | method
            | variable
        )
    )


@generate
def partials_c():
    yield (padding)
    lhs = yield (partials_condition)
    yield (padding)
    operator = yield (CONDITIONAL_OPERATOR)
    yield (padding)
    rhs = yield (partials_condition)
    yield (padding)

    return {"lhs": lhs, "operator": operator, "rhs": rhs}


q = OPEN_BRACKET.then(condition | numbers).skip(CLOSE_BRACKET) | (condition | numbers)


@generate
def t():
    yield (padding)
    lhs = yield (q)
    yield (padding)
    operator = yield (CONDITIONAL_OPERATOR)
    yield (padding)
    rhs = yield (q)
    yield (padding)

    return {"lhs": lhs, "operator": operator, "rhs": rhs}


partials_condition = (
    q
    | (OPEN_BRACKET + padding)
    .then(t.combine_dict(Condition))
    .skip(padding + CLOSE_BRACKET)
    | t.combine_dict(Condition)
)


@generate
def partials():
    yield (padding)
    lhs = yield (partials_condition)
    yield (padding)
    operator = yield (CONDITIONAL_OPERATOR)
    yield (padding)
    rhs = yield (partials_condition)
    yield (padding)

    return {"lhs": lhs, "operator": operator, "rhs": rhs}


negated_partials = seq(
    _=NEGATION.skip(padding),
    content=(OPEN_BRACKET + padding)
    .then(partials.combine_dict(Condition))
    .then(padding + CLOSE_BRACKET + padding),
).combine_dict(Negation)

bracketable_partials = (OPEN_BRACKET + padding).then(
    partials.combine_dict(Condition)
).skip(padding + CLOSE_BRACKET) | partials.combine_dict(Condition)

consts_x = negated_partials | bracketable_partials | condition

bracketable_consts = (
    (OPEN_BRACKET + padding).then(consts_x).skip(padding + CLOSE_BRACKET)
)


@generate
def consts():
    yield (padding)
    x = (
        partials.combine_dict(Condition)
        | negated_partials
        | condition
        | bracketable_consts
    )
    yield padding
    return x


@generate
def negated():
    yield (NEGATION)
    yield (OPEN_BRACKET + padding)
    content = yield (parser)
    yield (padding + CLOSE_BRACKET + padding)

    return {"content": content}


test = seq(a=partials, operator=CONDITIONAL_OPERATOR, b=partials)

parser = negated.combine_dict(Negation) | consts


class StatementParser:
    def __init__(self, root):
        self.root = root

        self.depth = 0
        self.negated = False
        self.output = {
            "conditions": [],  # format == != < >
            "predicates": [],  # single block ie x !x
            "negated_conditions": [],
            "negated_predicates": [],
            "conjunctions": [],
            "disjunctions": [],
        }

        self.opposite_operator = {
            "<": ">=",
            ">": "<=",
            ">=": "<",
            "<=": ">",
            "==": "!=",
            "!=": "==",
            "true": "false",
            "false": "true",
            "&&": "&&",
            "||": "||",
        }

    def get_facts(self):
        return self.output.copy()

    def get_output(self, property):
        return self.output[property].copy()

    def get_opposite(self, operator):
        return self.opposite_operator[operator]

    def args_to_str(self, args):
        arguments = []
        for arg in args:
            result = self.visit(arg)
            if result == None:
                return None
            arguments.append(result)
        return arguments

    def visit_FieldAccess(self, node):
        output_str = "{}.{}".format(node.variable_name, node.field)
        if self.root == node:
            self.output["predicates"].append(["{}".format(output_str)])
            self.output["predicates"].append(["!!{}".format(output_str)])
            self.output["conditions"].append(["{}".format(output_str), "==", "true"])
            self.output["conditions"].append(["{}".format(output_str), "!=", "false"])

            # self.output["negated_conditions"].append("{} != true".format(output_str))
            # self.output["negated_conditions"].append("{} == false".format(output_str))
            self.output["negated_predicates"].append(["!{}".format(output_str)])

            return

        return output_str

    def visit_MethodInvocation(self, node):
        method_call = self.visit(node.method)
        output_str = "{}.{}".format(node.variable_name, method_call)
        if self.root == node:
            self.output["conditions"].append(
                ["{}".format(output_str), "!= false", "true"]
            )
            self.output["conditions"].append(["{}".format(output_str), "==", "true"])

            self.output["predicates"].append(["{}".format(output_str)])
            self.output["predicates"].append(["!!{}".format(output_str)])
            self.output["negated_predicates"].append(["!{}".format(output_str)])
            return

        return output_str

    def visit_Variable(self, node):
        if self.root == node:
            self.output["conditions"].append(["{}".format(node.name), "!=", "false"])
            self.output["conditions"].append(["{}".format(node.name), "==", "true"])

            self.output["predicates"].append(["{}".format(node.name)])
            self.output["predicates"].append(["!!{}".format(node.name)])
            return

        return node.name

    def visit_Number(self, node):
        return node.value

    def visit_String(self, node):
        if (node.value) == None:
            return "''"

        return str(node.value)

    def visit_MathExpression(self, node):
        return "{} {} {}".format(
            self.visit(node.lhs), node.operator, self.visit(node.rhs)
        )

    def visit_Method(self, node):
        arguments = self.args_to_str(node.arguments)

        string_args = ""
        if arguments:
            string_args = ",".join(arguments)

        if self.root == node:
            output_str = "{}({})".format(node.name, string_args)
            self.output["conditions"].append(["{}".format(output_str), "!=", "false"])
            self.output["conditions"].append(["{}".format(output_str), "==", "true"])

            self.output["predicates"].append(["{}".format(output_str)])
            self.output["predicates"].append(["!!{}".format(output_str)])
            self.output["negated_predicates"].append(["!{}".format(output_str)])
            return

        return "{}({})".format(node.name, string_args)

    def visit_Negation(self, node):
        x = self.visit(node.content)
        if type(self.root).__name__ == "Negation":
            # when the content is already condition no need to add true or false
            if type(node.content).__name__ == "Condition":
                self.output["predicates"].append(["!({})".format(x)])
                self.output["predicates"].append(["!!!({})".format(x)])
                self.output["negated_conditions"].append(x)
            else:
                self.output["predicates"].append(["!{}".format(x)])
                self.output["predicates"].append(["!!!{}".format(x)])
                self.output["negated_predicates"].append(["{}".format(x)])

                # if not (type(node.content).__name__ == "Condition"):
                self.output["conditions"].append(["({})".format(x), "==", "false"])
                self.output["conditions"].append(["({})".format(x), "!=", "true"])
            return
        return "!({})".format(x)

    def visit_Condition(self, node):
        lhs = self.visit(node.lhs)
        operator = node.operator
        rhs = self.visit(node.rhs)

        if len(lhs) > 1:
            lhs = "".join(lhs)

        if len(rhs) > 1:
            rhs = "".join(rhs)

        if self.root == node:
            connective = False
            if operator == "&&":
                self.output["conjunctions"].append([lhs, rhs])
                connective = True
            elif operator == "||":
                if len(lhs) > 1:
                    lhs = "".join(lhs)

                if len(rhs) > 1:
                    rhs = "".join(rhs)
                self.output["disjunctions"].append([lhs, rhs])
                connective = True
            if operator == "instanceof":
                connective = True

            self.output["conditions"].append([lhs, operator, rhs])
            if not connective:
                self.output["negated_conditions"].append(
                    [lhs, self.get_opposite(operator), rhs]
                )

            return

        return [lhs, operator, rhs]

    def default_visitor(self, node):
        if node == "":
            return None
        return node.value

    def get_node_type(self, node):
        method = re.search("'(.+)'", str(type(node))).group(1)
        search_type = re.search("[\S]+\.(.+)'>", str(type(node)))
        if search_type:
            node_type = search_type.group(1)
            return node_type
        return method

    def visit(self, node):
        method = "visit_" + self.get_node_type(node)
        return getattr(self, method, self.default_visitor)(node)


def test_parser(contents):
    for content in contents:
        tokenised = parser.parse(content)

        print(tokenised)

        visitor = StatementParser(root=tokenised)
        x = visitor.visit(tokenised)
        print(visitor.get_output("conditions"))
        print("predicates")
        print(visitor.get_output("predicates"))

        print("negated conditions")
        print(visitor.get_output("negated_conditions"))

        print("negated predicates")
        print(visitor.get_output("negated_predicates"))

        print("conjunctions")
        print(visitor.get_output("conjunctions"))

        print("disjunctions")
        print(visitor.get_output("disjunctions"))


def generate_condition_facts(condition):
    content = parser.parse(condition)
    visitor = StatementParser(content)
    visitor.visit(content)
    facts = visitor.get_facts()
    return facts


def simple_conjunction_parser(input):
    stack = []
    capture = []
    between = []
    index = 0

    output = None

    total_length = len(input)

    while True:
        if index == total_length:
            minimum = between[0]
            maximum = between[-1]
            print(maximum)

            lhs = input[: minimum + 1]
            rhs = input[maximum:]

            operator = "".join(capture)

            output = [lhs.strip(), operator.strip(), rhs.strip()]

            break

        if input[index] == "(":
            stack.append("0")
            index += 1
            continue

        elif input[index] == ")":
            stack.pop()
            index += 1
            continue

        if len(stack) == 0:
            capture += input[index]
            between += [index]

        index += 1

    return {
        "conditions": [output],
        "predicates": [],  # single block ie x !x
        "negated_conditions": [],
        "negated_predicates": [],
        "conjunctions": [],
        "disjunctions": [],
    }


if __name__ == "__main__":
    # very special case x("y", 1, 2, 3)
    statements = [
        "x",
        # "!x",
        # "x()",
        # "x('')"
        # "!str.hasNext()"
        # "!x",
        # "x(1,2,3)"
        # "itr.hasNext()",
        # "x.put('123')",
        # 'x.pur("123")',
        # "x(1,2, 3)",
        # "!itr.hasNext(1,x,y)",
        # "x(y(),t(),z)"
        # "x > 5",
        # "x.put('123') == x.flip('345')",
        # "x < 15",
        # "(x < 15)",
        # "x.put(123)",
        # "!(test.put(123) == 123)",
        # issue******
        # "!(!(test.put(123) != 123))",
        # "!d.isJsonNull()",
        # "!(d.isJsonNull())",
        # "options.containsKey(org.apache.accumulo.core.iterators.user.RegExFilter.ROW_REGEX)",
        # "x && y" # issue
        # "(maxStackFrames != null) && (i == maxStackFrames)", # issue
        # "(!hasStart) && (!hasEnd)", # issue
        # "(!hasStart) && y", #issue
        # "options.get(END_INCL) != null",
        # "(testVis.getLength() == 0) && (defaultVisibility.getLength() == 0)",
        # "(testVis.getLength() == 0)",
        # "isVerbose()",
        # "scanner.hasNextLine() && (!hasExited())", # issue ****
        # "input == null",
        # "len >= bb.remaining()",
        # "x >= 15",
        # "x.b", # //issue
        # "passKey == null",
        # "!x.b"
    ]

    for statement in statements:
        print(generate_condition_facts(statement))

    # test_parser(statements)
