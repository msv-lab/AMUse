import os
import javalang
from openai import OpenAI
import json
import logging
from concurrent.futures import ThreadPoolExecutor
import backoff
from typing import List, Tuple, Dict
from pathlib import Path
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


class APIMisuseChecker:
    def __init__(self, api_key: str, batch_size: int = 10):
        self.client = OpenAI(api_key=api_key)
        self.batch_size = batch_size
        self.checkpoint_file = "checkpoint.json"
        self.results = self._load_checkpoint()

    def _load_checkpoint(self) -> List[Dict]:
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        return []

    def extract_functions(self, project_path: str) -> List[Tuple[str, int, str]]:
        functions = []
        for root, _, files in os.walk(project_path):
            for file in files:
                if not file.endswith(".java"):
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    tree = javalang.parse.parse(content)

                    # Convert content to lines for easier extraction
                    lines = content.splitlines()

                    for _, node in tree.filter(javalang.tree.MethodDeclaration):
                        if hasattr(node, "position") and node.position:
                            # javalang Position object has line and column attributes
                            start_line = node.position.line - 1  # Convert to 0-based

                            # Find method end by tracking braces
                            end_line = self.find_method_end(lines, start_line)

                            if end_line > start_line:
                                function_code = "\n".join(
                                    lines[start_line : end_line + 1]
                                )
                                functions.append(
                                    (file_path, start_line + 1, function_code)
                                )
                            else:
                                logger.warning(
                                    f"Could not find method end in {file_path}"
                                )

                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")

        return functions

    def find_method_end(self, lines: List[str], start_line: int) -> int:
        """Find the end line of method by tracking braces"""
        bracket_count = 0
        current_line = start_line
        found_first_bracket = False

        while current_line < len(lines):
            line = lines[current_line]
            if "{" in line:
                found_first_bracket = True
                bracket_count += line.count("{")
            if "}" in line:
                bracket_count -= line.count("}")

            if found_first_bracket and bracket_count == 0:
                return current_line

            current_line += 1

        return start_line  # Fallback if no end found

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def check_api_misuse(self, function_code: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying Java API misuses.",
                    },
                    {
                        "role": "user",
                        "content": f"Check this Java function for API misuses and output only the corrections. If no misuses found, respond with 'Correct.' No explanation needed.\n\nFunction to check:\n\n{function_code}",
                    },
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"API call failed: {str(e)}")
            raise

    def analyze_project(self, project_path: str, output_file: str):
        functions = self.extract_functions(project_path)

        with ThreadPoolExecutor() as executor:
            for i in range(0, len(functions), self.batch_size):
                batch = functions[i : i + self.batch_size]
                futures = [
                    executor.submit(self.check_api_misuse, code) for _, _, code in batch
                ]

                for (file_path, line_number, _), future in zip(batch, futures):
                    try:
                        result = future.result()
                        record = {
                            "file": file_path,
                            "line": line_number,
                            "status": (
                                "correct" if "correct" in result.lower() else "misuse"
                            ),
                            "details": result,
                        }
                        self.results.append(record)
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {str(e)}")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2)

    def get_processed_files(self) -> set:
        return {r["file"] for r in self.results}


if __name__ == "__main__":
    checker = APIMisuseChecker(api_key=os.getenv("OPENAI_API_KEY"), batch_size=10)
    checker.analyze_project(
        project_path="/root/closure-compiler", output_file="api_misuse_results.json"
    )
