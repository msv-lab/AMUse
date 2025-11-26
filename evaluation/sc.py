from openai import OpenAI
import os
from collections import Counter


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
            id_ = method.split("_")[1]
            method_path = method_folder + "/" + method + "/" + "method_content.facts"
            if not os.path.exists(method_path):
                continue
            with open(method_path, "r") as file:
                lines = file.readlines()
                buggy_snippets_list.append(("\n".join(lines), id_))
    return buggy_snippets_list


def generate_output(api, buggy_snippet, example_snippets, num_samples=1):

    prompt = f"Given these examples of correct usages of {api} API:\n{example_snippets}\nFix API misuse in the following code and give corrected code:\n{buggy_snippet}"
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an API misuse repair tool"},
            {"role": "user", "content": prompt},
        ],
        n=num_samples,
        #   temperature=0.7,
        #   top_p=1
    )
    return completion


def generate_multiple_outputs(api, buggy_snippet, example_snippets, num_samples):
    outputs = []
    response = generate_output(api, buggy_snippet, example_snippets, num_samples)
    for i in range(num_samples):
        output = response.choices[i].message.content

        # strip the ``` from the output
        if "```" in output:
            output = output.split("```")[1].split("```")[0].replace("java\n", "")
        outputs.append(output)

    # for _ in range(num_samples):
    #     output = generate_output(api, buggy_snippet, example_snippets).choices[0].message.content
    #     # strip the ``` from the output
    #     if "```" in output:
    #         output = output.split("```")[1].split("```")[0].replace("java\n", "")
    #     outputs.append(output)
    return outputs


def majority_voting(outputs):
    counter = Counter(outputs)
    most_common_output, _ = counter.most_common(1)[0]
    return most_common_output


def self_consistency(api, buggy_snippet, example_snippets, num_samples=10):
    outputs = generate_multiple_outputs(
        api, buggy_snippet, example_snippets, num_samples
    )
    consistent_output = majority_voting(outputs)
    return consistent_output


if __name__ == "__main__":
    for api_examples_path in os.listdir("./"):
        if api_examples_path.endswith("_examples.txt"):

            api = api_examples_path.split("_")[0]
            example_snippets = get_snippets(api + "_examples.txt")
            buggy_snippets = get_buggy_snippets_by_api(api)

            for buggy_snippet, id_ in buggy_snippets:
                consistent_output = self_consistency(
                    api, buggy_snippet, example_snippets
                )
                output_file = api + "_" + id_ + "_result.txt"

                with open(output_file, "w") as output:
                    output.write(consistent_output + "\n")

                print(f"Output for {api} API with id {id_} is saved in {output_file}")
