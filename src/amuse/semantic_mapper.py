from amuse.souffle import parse
from collections import namedtuple

# Valid semantics
SEMANTICS = [
    "call_signature",
    "call_name",
    "label",
    "in_method",
    "argument",
    "cond_call_var",
]

Location = namedtuple("Location", ["predicate", "arg_index"])


class SemanticMapper:
    def __init__(self, component_rules_path) -> None:
        self._component_rules = self.load_component_rules(component_rules_path)

    def load_component_rules(self, component_rules_path):
        with open(component_rules_path, "r") as f:
            component_rules = parse(f.read())
        return component_rules

    def map(self):
        """Create two maps:
        1. semantic meaning of an argument to its location in the rules.
        2. location to semantic meaning.
        """

        location_to_semantics = {}
        semantics_to_location = {}

        semantics_to_location["call_signature"] = [
            Location("call", 0),
            Location("must_call_followed_before_exit", 0),
            Location("must_call_followed_before_exit", 3),
            Location("must_call_followed", 0),
            Location("must_call_followed", 3),
            Location("must_call_preceded_after_entry", 0),
            Location("must_call_preceded_after_entry", 3),
            Location("must_call_preceded", 0),
            Location("must_call_preceded", 3),
            Location("condition_dominate", 0),
        ]

        semantics_to_location["call_name"] = [
            Location("call_name", 0),
            Location("must_call_name_followed_before_exit", 0),
            Location("must_call_name_followed_before_exit", 3),
        ]

        semantics_to_location["label"] = [
            Location("call", 1),
            Location("call_name", 1),
            Location("must_call_followed_before_exit", 1),
            Location("must_call_name_followed_before_exit", 1),
            Location("must_call_followed", 1),
            Location("must_call_followed", 4),
            Location("must_call_preceded_after_entry", 1),
            Location("must_call_preceded", 1),
            Location("must_call_preceded", 4),
            Location("condition_dominate", 1),
            Location("condition_dominate", 4),
        ]

        semantics_to_location["in_method"] = [
            Location("call", 3),
            Location("call_name", 3),
            Location("must_call_followed_before_exit", 2),
            Location("must_call_name_followed_before_exit", 2),
            Location("must_call_followed", 2),
            Location("must_call_followed", 5),
            Location("must_call_preceded_after_entry", 2),
            Location("must_call_preceded", 2),
            Location("must_call_preceded", 5),
            Location("condition_dominate", 2),
            Location("condition_dominate", 5),
        ]

        semantics_to_location["argument"] = [
            Location("actual_argument", 1),
        ]

        semantics_to_location["cond_call_var"] = [
            Location("condition_dominate", 3),
            Location("call", 2),
        ]

        # check if the semantics are valid
        for semantic in semantics_to_location:
            if semantic not in SEMANTICS:
                raise ValueError(f"Semantic {semantic} is not defined")

        # create the reverse mapping from location to semantics
        for semantic, locations in semantics_to_location.items():
            for location in locations:
                if location not in location_to_semantics:
                    location_to_semantics[location] = semantic
                else:
                    if location_to_semantics[location] != semantic:
                        raise ValueError(
                            f"Location {location} is mapped to multiple semantics"
                        )

        return location_to_semantics, semantics_to_location
