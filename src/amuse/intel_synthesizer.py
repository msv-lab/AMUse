from prompt import datalog_basics, pattern_prompt_template


synthesis_prompt_template = (
    datalog_basics
    + """


{patterns}

Next, according to the given patterns, write the Souffle Datalog rules to describe them.
First, identify the API elements and their relations. Then, write the Datalog rules to describe the relations.
For each pattern description, the subject(s) and object(s) are usually API elements. 
When you describe the relation between API elements, please use the following for the common relations:

Call-order: Assume the API method is called at 'x' in 'x_meth' and another necessary method is called at 'y' in 'y_meth'. If the necessary method must be called after the API method, their relation is:
post_dom(x, x_meth, y, y_meth), 
meaning that for all paths starting from the node 'x' in 'x_meth' to the exit node, they must go through 'y' in 'y_meth'. 
Conversely, if the necessary method must be called before the API method, their relation is: 
dom(x, x_meth, y, y_meth), 
meaning that for all paths from the entry node to 'x' in 'x_meth', they must go through 'y' in 'y_meth'.

Condition-check: Assume the API method is called at 'x' in 'x_meth' and the necessary method is called at 'y' in 'y_meth', with its return value assigned to a variable 'var' also at 'y' in 'y_meth'. For this pattern, the relation is: 
assigned(var, y, y_meth),
v_condition(var, y, y_meth),
sat_transition(y, y_meth, x1, x1_meth), 
dom(x, x_meth, x1, x1_meth),
call(the_api, x, the_var_call_the_api, x_meth). // the API call

Return value check: Assume the API method is called at 'label_call' in 'x_meth' with its return value assigned to a variable 'var' also at 'label_call' in 'x_meth', and the 'var' is used at 'label_use' in 'y_meth'.
For this pattern, the relation is:
call(the_api, label_call, the_var_call_the_api, x_meth), // the API call
assigned(ret_var, label_call, x_meth), // the return value of the API method is assigned to 'ret_var' at 'label_call' in 'x_meth'.
v_condition(ret_var, label_check, x0_meth),
sat_transition(label_check, x0_meth, label_sat, x1_meth),
dom(label_use, y_meth, label_sat, x1_meth), // 'label_use' in 'y_meth' is dominated by 'label_sat' in 'x1_meth'
(actual_argument(_, ret_var, label_use, _, y_meth);
call(_, label_use, ret_var, y_meth)).

Input value check: Assume the API method is called at 'x' in 'x_meth' with its argument 'arg_i' needing to satisfy a certain condition. For this pattern, when arg_i is a variable the relation is:
actual_argument(the_api, arg_i, x, _, x_meth), // the argument 'arg_i' of the API method
variable(arg_i, x_meth), // 'arg_i' is a variable
v_condition(arg_i, x, x_meth),
sat_transition(x0, x0_meth, x1, x1_meth),
dom(x, x_meth, x1, x1_meth),
call(the_api, x, the_var_call_the_api, x_meth). // the API call

When arg_i is a constant, the relation is:
actual_argument(the_api, arg_i, x, _, x_meth), // the argument 'arg_i' of the API method
value(arg_i, x, x_meth), // 'arg_i' is a constant
v_condition(arg_i, x, x_meth), // the condition that 'arg_i' should satisfy
call(the_api, x, the_var_call_the_api, x_meth). // the API call

Exception handling: Assume the API method is called at 'x' in 'x_meth', with the try-catch structure at 'x0' and 'x1'. For this pattern, the relation is: 
flow_reach(x0, x_meth, x, x_meth), flow_reach(x, x_meth, x1, x_meth).


The above relations are common; you can define your own conditions and relations. Your Datalog rules should strictly follow the provided template. Note, v_condition(var, label, in_meth) is not a predefined relation. You must *implement* it according to the API if your rules require it.
Please only output the Datalog rules and do not include any other information.
It is normal to have multiple correct usage patterns for an API. If you have multiple correct usage patterns, please think twice and only keep the most prevalent ones.

Template:
correct_usage_i("{api}", label1, var1, in_meth) :- 
    call("{api}", label1, var1, in_meth), 
    yourOwnDefinedCondition1(...),
    ...

yourOwnDefinedCondition1(...):- //replace the name with a suitable condition name
    ...

v_condition(var1, label_2, in_meth):- 
    ...

"""
)

call_order_formalization_prompt_template = """

{call_order_pattern}

Given the above usage pattern for the API {api}, please formalize the involved call-order relation as: some API element must be followed or preceded by another API element. Please follow the template below:

Template:

call-order description: the formalized description of the call-order relation
first API element: the first API element
second API element: the second API element
relation: the relation between the first and second API elements, i.e., 'must be followed by' or 'must be preceded by'


Please only output the information required in the template and do not include any other information.

"""


call_order_synthesis_prompt_template = (
    datalog_basics
    + """

{call_order_formalized_pattern}

Given the above usage pattern for the API {api}, please refer to the following templates to write the Souffle Datalog rules to describe the call-order relation between the API elements. 
If the API element is a description of a group of methods, please concretize it into all the methods in the group, and write the Datalog rules for each pair of concretized API elements.
Please concretize as many API elements as possible.

Call-order templates:

1. If the relation is 'must be followed by', the template is:

// replace 'first_api_element' and 'second_api_element' with the qualified names of the actual API methods
correct_usage_{i}("{api}", label1, var1, in_meth) :- 
    call(first_api_element, label1, var1, in_meth), 
    post_dom(label1, in_meth, label2, in_meth),
    call(second_api_element, label2, var2, in_meth). 

2. If the relation is 'must be preceded by', the template is:

// replace 'first_api_element' and 'second_api_element' with the qualified names of the actual API methods
correct_usage_{i}("{api}", label1, var1, in_meth) :-
    call(first_api_element, label1, var1, in_meth),
    dom(label1, in_meth, label2, in_meth),
    call(second_api_element, label2, var2, in_meth).


Please only output the Datalog rules and do not include any other information.

"""
)


from openai import OpenAI
import os
from collections import Counter
import json


client = OpenAI(api_key="")


def get_snippets(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()
        return "\n".join(lines)


def get_buggy_snippets_by_api(api):
    method_folder = "/root/mubench/methods"
    buggy_snippets_list = []
    for method in os.listdir(method_folder):
        if api == method.split("_")[0]:
            id_ = "_".join(method.split("_")[1:])
            method_path = method_folder + "/" + method + "/" + "method_content.facts"
            if not os.path.exists(method_path):
                continue
            with open(method_path, "r") as file:
                lines = file.readlines()
                buggy_snippets_list.append(("\n".join(lines), id_))
    return buggy_snippets_list


def generate_output(api, num_samples=1):

    pattern_prompt = pattern_prompt_template.format(api=api)

    pattern_resp = (
        client.chat.completions.create(
            model="chatgpt-4o-latest",
            messages=[
                {"role": "system", "content": "You are an API misuse repair tool"},
                {"role": "user", "content": pattern_prompt},
            ],
            n=1,
            #   temperature=0.7,
            #   top_p=1
        )
        .choices[0]
        .message.content
    )

    print(pattern_resp)

    synthesis_prompt = synthesis_prompt_template.format(api=api, patterns=pattern_resp)

    completion = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {"role": "system", "content": "You are an API misuse repair tool"},
            {"role": "user", "content": synthesis_prompt},
        ],
        n=num_samples,
        #   temperature=0.7,
        #   top_p=1
    )

    return completion


def generate_multiple_outputs(api, num_samples):
    outputs = []
    response = generate_output(api, num_samples)
    for i in range(num_samples):
        output = response.choices[i].message.content

        # strip the ``` from the output
        if "```" in output:
            output = (
                output.split("```")[1]
                .split("```")[0]
                .replace("datalog\n", "")
                .replace("prolog\n", "")
                .strip()
            )
        outputs.append(output)

    return outputs


def majority_voting(outputs):
    counter = Counter(outputs)
    most_common_output, _ = counter.most_common(1)[0]
    return most_common_output


def self_consistency(api, num_samples=10):
    outputs = generate_multiple_outputs(api, num_samples)
    consistent_output = majority_voting(outputs)
    return consistent_output, outputs


def run(target_api=None, num_samples=10):

    output_file = f"rules_{target_api}.json"

    print(f"Generating rules for {target_api} API...")
    consistent_output, all_outputs = self_consistency(target_api, num_samples)

    # dump the consistent output and all outputs in a json file
    with open(output_file, "w") as output:
        json.dump(
            {
                "consistent_output": consistent_output,
                "all_outputs": all_outputs,
            },
            output,
        )


def print_consistent_output(json_file):
    """
    Prints the consistent output in a human-readable format.

    :param api: str, the name of the API
    :param id_: str, the ID of the snippet
    :param consistent_output: str, the consistent output to print
    """
    with open(json_file, "r") as file:
        data = json.load(file)
        consistent_output = data["consistent_output"]
        print(consistent_output)


def print_all_outputs(json_file):
    """
    Prints all outputs in a human-readable format.

    :param api: str, the name of the API
    :param id_: str, the ID of the snippet
    :param all_outputs: list, the list of all outputs to print
    """
    with open(json_file, "r") as file:
        data = json.load(file)
        all_outputs = data["all_outputs"]
        for i, output in enumerate(all_outputs):
            print(f"Output {i + 1}:")
            print(output)


def print_output(json_file):
    print_consistent_output(json_file)
    print_all_outputs(json_file)


if __name__ == "__main__":
    api = "java.io.ByteArrayOutputStream.toByteArray() and java.io.ObjectOutputStream"
    # run(api, 1)
    # print_output(f"rules_{api}.json")

    call_order_pattern = """
### usage pattern 2: Calling flush() on ObjectOutputStream before toByteArray()
**involved common constraints**: Call-order  
**description of the usage pattern**: After writing to `ObjectOutputStream`, you should call `ObjectOutputStream.flush()` before calling `ByteArrayOutputStream.toByteArray()`. This ensures that all the data has been written to the underlying `ByteArrayOutputStream`.
"""

    formalization_prompt = call_order_formalization_prompt_template.format(
        api=api,
        call_order_pattern=call_order_pattern,
    )

    # generate the formalized call order using the formalization prompt
    completion = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {"role": "system", "content": "You are an API misuse repair tool"},
            {"role": "user", "content": formalization_prompt},
        ],
        n=1,
    )

    formalized_call_order = completion.choices[0].message.content

    print(formalized_call_order)

    synthesis_prompt = call_order_synthesis_prompt_template.format(
        api=api,
        call_order_formalized_pattern=formalized_call_order,
        i=1,
    )

    completion = client.chat.completions.create(
        model="chatgpt-4o-latest",
        messages=[
            {"role": "system", "content": "You are an API misuse repair tool"},
            {"role": "user", "content": synthesis_prompt},
        ],
        n=1,
    )

    output = completion.choices[0].message.content
    print(output)
