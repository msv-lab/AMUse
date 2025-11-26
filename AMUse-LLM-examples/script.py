from openai import OpenAI
import sys

def get_snippets(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()
        return "\n".join(lines)

api = sys.argv[1]

buggy_snippets = get_snippets(api+"_buggy.txt")
example_snippets = get_snippets(api+"_examples.txt")

prompt = f"Given these examples of correct usages of {api} API:\n{example_snippets}\nFix API misuse in the following code and give corrected code:\n{buggy_snippets}"

client = OpenAI()

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are an API misuse repair tool"},
    {"role": "user", "content": prompt}
  ]
)

output_file = api + "_result.txt"

with open(output_file, "a") as output:
    output.write(completion.choices[0].message.content+"\n")
Collapse