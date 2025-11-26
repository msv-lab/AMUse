import re
from typing import Tuple, Dict, List, Set
from collections import defaultdict, namedtuple
from copy import deepcopy
from more_itertools import unique_everseen

from amuse.souffle import Souffle, parse
from amuse.utils.logger import Logger

# flow_id_map is a dictionary mapping the relation name to index of the flow_id
flow_id_index_map = {
    "start": 0,
    "final": 0,
    "label": 0,
    "define": -2,
    "static_method": -2,
    "instance_call": -2,
    "return": -2,
    "call": 0,
    "constructor_call": -2,
    "return_value": -2,
    "assigned": -2,
    "assign_type": -2,
    "assignment": -2,
    "value": -2,
    "actual_argument": -3,
    "formal_argument": -3,
    "if": -2,
    "unary_op": -2,
    "binary_op": -2,
    "conditional": -2,
}

Variable = namedtuple("Variable", ["name", "in_method_sig"])
# ArgWrapper = namedtuple("ArgWrapper", ["arg", "in_method_sig"])


class ArgWrapper(namedtuple("ArgWrapper", ["arg", "in_method_sig"])):
    def __repr__(self) -> str:
        return f"ArgWrapper({self.arg}, {self.in_method_sig})"

    def __str__(self) -> str:
        return f"ArgWrapper({self.arg}, {self.in_method_sig})"


class APIElementsExtractor:
    @staticmethod
    def extract_api_elements(
        facts_path, api_instance, api_method_sig, api_flow_id, in_method_sig
    ) -> Tuple[
        Dict[str, List[List[str]]],
        Dict[str, List[List[str]]],
        Dict[str, List[List[str]]],
    ]:
        # extract the API class by splitting the method signature
        pattern = r"(?P<api_class>(?:[\w]+\.)+\w+)\.(?P<api_method>\w+\(\))"
        is_match = re.match(pattern, api_method_sig)
        if is_match:
            Logger.info(f"Extracting rough API elements from {facts_path}...")
            api_instance_elements = APIElementsExtractor.extract_api_instance_elements(
                facts_path, api_instance, in_method_sig
            )
            input_elements = APIElementsExtractor.extract_input_elements(
                facts_path, api_method_sig, api_flow_id, in_method_sig
            )
            output_elements = APIElementsExtractor.extract_output_elements(
                facts_path, api_flow_id, in_method_sig
            )

            Logger.info(f"Extracting rough API elements from {facts_path} Done!")
            return api_instance_elements, input_elements, output_elements

        else:
            raise Exception("API method signature not matched")

    @staticmethod
    def extract_api_instance_elements(
        facts_path: str, api_instance: str, in_method_sig: str
    ) -> Dict[str, List[List[str]]]:
        """Extract the API invocations issued by the api_instance interprocedurally."""
        Logger.info(f"Extracting API instance elements from {facts_path}...")
        api_instance_var = Variable(api_instance, in_method_sig)

        passed_in_instances = APIElementsExtractor.find_passed_in(
            facts_path, {api_instance_var}
        )
        target_instances = passed_in_instances.union(
            APIElementsExtractor.find_returned_to(facts_path, api_instance_var)
        )

        related_facts = APIElementsExtractor.extract_usage_facts(
            facts_path, target_instances
        )

        return related_facts

    @staticmethod
    def find_passed_in(facts_path: str, variables: Set[Variable]) -> Set[Variable]:
        variables = deepcopy(variables)  # avoid modifying the original set

        in_facts = Souffle.load_relations(facts_path)

        with open("/root/amuse/documentation/crafted_dl/analyser.dl", "r") as f:
            analyser_program = parse(f.read())

        out_facts = Souffle.run_program(analyser_program, in_facts)

        assert "data_flow_reach" in out_facts, "Bug?"

        data_reach_facts = out_facts["data_flow_reach"]

        # find all the data reach facts which contain the target_objects as the target
        other_vars = set(
            map(
                lambda x: Variable(x[0], x[1]),
                filter(
                    lambda x: any(
                        arg.name == x[0] and arg.in_method_sig == x[1]
                        for arg in variables
                    ),
                    data_reach_facts,
                ),
            )
        )

        return variables.union(other_vars)

    @staticmethod
    def find_returned_to(facts_path: str, ret_var: Variable) -> Set[Variable]:
        target_vars = set()
        target_vars.add(ret_var)

        in_facts = Souffle.load_relations(facts_path)

        with open("/root/amuse/documentation/crafted_dl/analyser.dl", "r") as f:
            analyser_program = parse(f.read())

        out_facts = Souffle.run_program(analyser_program, in_facts)

        assert "data_flow_reach" in out_facts, "Bug?"

        data_reach_facts = out_facts["data_flow_reach"]

        # find all the data reach facts which contain the target_objects as the target
        other_vars = set(
            map(
                lambda x: Variable(x[3], x[5]),
                filter(
                    lambda x: ret_var.name == x[3] and ret_var.in_method_sig == x[5],
                    data_reach_facts,
                ),
            )
        )

        target_vars = target_vars.union(other_vars)

        return target_vars

    @staticmethod
    def extract_input_elements(
        facts_path: str, api_method_sig: str, api_flow_id: int, in_method_sig: str
    ) -> Dict[str, List[List[str]]]:
        """
        Extract the input elements of the API method and the operations related to the input elements.
        """

        Logger.info(f"Extracting input elements from {facts_path}...")

        # load actual_argument.facts file. The format is: method_signature \t argument_value \t flow_id \t argument_index \t method_signature
        actual_argument_facts = Souffle.load_relations(facts_path, ["actual_argument"])

        api_arg_facts = {
            "actual_argument": list(
                filter(
                    lambda x: api_method_sig == x[0]
                    and str(api_flow_id) == x[2]
                    and in_method_sig == x[-1],
                    actual_argument_facts["actual_argument"],
                )
            )
        }

        # filter the arguments of the facts by the API method signature
        api_arguments = set(
            map(
                lambda x: Variable(
                    x[1], in_method_sig
                ),  # the argument value is at index 1
                api_arg_facts["actual_argument"],
            )
        )

        updated_api_arguments = APIElementsExtractor.find_passed_in(
            facts_path, api_arguments
        )

        related_facts = APIElementsExtractor.extract_usage_facts(
            facts_path, updated_api_arguments
        )

        # extra facts for the input arguments
        related_facts["actual_argument"] = api_arg_facts["actual_argument"]

        return related_facts

    @staticmethod
    def extract_output_elements(
        facts_path: str, api_flow_id: int, in_method_sig: str
    ) -> Dict[str, List[List[str]]]:
        """
        Extract the output elements of the API method and the operations related to the output elements.
        """

        Logger.info(f"Extracting output elements from {facts_path}...")
        # get the assinged object for the return value of the API method
        loaded_facts = Souffle.load_relations(facts_path, ["assigned"])

        target_vars = set()

        target_assigned_facts = {
            "assigned": list(
                filter(
                    lambda args: str(api_flow_id) == args[1]
                    and in_method_sig == args[-1],
                    loaded_facts["assigned"],
                )
            )
        }

        assigned_object_tup = tuple(
            map(
                lambda x: Variable(
                    x[0], in_method_sig
                ),  # the assigned object is at index 0
                target_assigned_facts["assigned"],
            )
        )

        if len(assigned_object_tup) == 0:
            return {}

        assigned_var = assigned_object_tup[0]

        target_vars = APIElementsExtractor.find_returned_to(facts_path, assigned_var)

        related_facts = APIElementsExtractor.extract_usage_facts(
            facts_path, target_vars
        )

        # extra facts for the returned object
        related_facts["assigned"] = target_assigned_facts["assigned"]

        return related_facts

    # @staticmethod
    # def extract_usage_facts(
    #     facts_path: str, target_vars: Set[Variable]
    # ) -> Dict[str, List[List[str]]]:
    #     """Extract the facts related to the API usage employed on the `target_vars`."""
    #     call_usage_facts = defaultdict(list)
    #     condition_usage_facts = defaultdict(list)
    #     check_usage_facts = defaultdict(list)

    #     # get the invocation, condition check related facts of target_vars
    #     call_condition_check_related_facts = Souffle.load_relations(
    #         facts_path,
    #         [
    #             "call",
    #             "instance_call",
    #             "constructor_call",
    #             "if",
    #             "unary_op",
    #             "binary_op",
    #             "conditional",
    #         ],
    #     )

    #     # get call related facts
    #     for relation_name, args_list in call_condition_check_related_facts.items():
    #         if relation_name not in ("call", "instance_call", "constructor_call"):
    #             continue
    #         call_usage_facts[relation_name] = list(
    #             filter(
    #                 lambda args: any(
    #                     any(var.name == arg for arg in args)
    #                     and any(var.in_method_sig == arg for arg in args)
    #                     for var in target_vars
    #                 ),
    #                 args_list,
    #             )
    #         )

    #     # get condition related facts
    #     for relation_name, args_list in call_condition_check_related_facts.items():
    #         if relation_name not in ("unary_op", "binary_op"):
    #             continue
    #         condition_usage_facts[relation_name] = list(
    #             filter(
    #                 lambda args: any(
    #                     any(var.name == arg for arg in args)
    #                     and any(var.in_method_sig == arg for arg in args)
    #                     for var in target_vars
    #                 ),
    #                 args_list,
    #             )
    #         )

    #     # get if/conditional related facts
    #     for relation_name, args_list in call_condition_check_related_facts.items():
    #         if relation_name not in ("if", "conditional"):
    #             continue
    #         for args in args_list:
    #             assert relation_name in flow_id_index_map, "Bug?"
    #             flow_id = args[flow_id_index_map[relation_name]]

    #             # check if the flow_id is in the condition_usage_facts
    #             if any(
    #                 any(
    #                     flow_id == cond_args[flow_id_index_map[cond_op]]
    #                     for cond_args in cond_args_list
    #                 )
    #                 for cond_op, cond_args_list in condition_usage_facts.items()
    #             ):
    #                 check_usage_facts[relation_name].append(args)

    #     usage_facts = {**call_usage_facts, **condition_usage_facts, **check_usage_facts}

    #     # unique the usage facts
    #     usage_facts = {
    #         relation_name: list(unique_everseen(args_list))
    #         for relation_name, args_list in usage_facts.items()
    #     }

    #     return usage_facts

    @staticmethod
    def extract_usage_facts(
        facts_path: str, target_vars: Set[Variable]
    ) -> Dict[str, List[List[str]]]:
        """Extract the facts related to the API usage employed on the `target_vars`."""
        # find facts related to the target_vars
        related_facts = defaultdict(list)
        all_facts = Souffle.load_relations(facts_path)

        # filter the facts by the target_vars
        for relation_name, args_list in all_facts.items():
            related_facts[relation_name] = list(
                filter(
                    lambda args: any(
                        any(var.name == arg for arg in args)
                        and any(var.in_method_sig == arg for arg in args)
                        for var in target_vars
                    ),
                    args_list,
                )
            )

        # find remaining facts representing the same elements as the related_facts represent.

        # filter the args of the related_facts which are: 1. of string type but not a function signature, 2. flow_id
        related_args = set()

        for relation_name, args_list in related_facts.items():
            for args in args_list:
                cur_method_sig = args[-1]

                if relation_name in flow_id_index_map:
                    assert relation_name in flow_id_index_map
                    flow_id = args[flow_id_index_map[relation_name]]
                    related_args.add(ArgWrapper(flow_id, cur_method_sig))

                for arg in args[
                    :-1
                ]:  # exclude the last arg which is the method signature
                    # if arg is a string but not a function signature and not a common const like "true", "false", "null", etc.
                    if isinstance(arg, str) and arg not in related_args and "." in arg:
                        related_args.add(ArgWrapper(arg, cur_method_sig))

        # filter the facts by the related_args
        for relation_name, args_list in all_facts.items():
            # skip flow, value, variable related facts
            if relation_name in (
                "flow",
                "value",
                "variable",
                "false_flow",
                "true_flow",
                "label",
            ):
                continue
            related_facts[relation_name].extend(
                list(
                    filter(
                        lambda x: any(
                            arg.arg in x and arg.in_method_sig == x[-1]
                            for arg in related_args
                        ),
                        args_list,
                    )
                )
            )

        # unique the related facts
        related_facts = {
            relation_name: list(unique_everseen(args_list))
            for relation_name, args_list in related_facts.items()
        }

        return related_facts
