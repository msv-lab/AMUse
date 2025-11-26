import requests
import os
import subprocess

# GitHub personal access token (create one on GitHub if you don't have it)
GITHUB_TOKEN = ""

# GitHub API base URL
GITHUB_API_URL = "https://api.github.com"

# Number of stars threshold
STARS_THRESHOLD = 1000

# Headers for authentication
headers = {"Authorization": f"token {GITHUB_TOKEN}"}


def search_repositories(
    organization="apache", language="Java", stars=STARS_THRESHOLD, per_page=100, page=1
):
    query = f"org:{organization} language:{language} stars:>{stars}"
    url = f"{GITHUB_API_URL}/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": per_page,
        "page": page,
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def clone_repository(repo_url, destination_folder="/root/cloned_repos"):
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    if os.path.exists(f"{destination_folder}/{repo_url.split('/')[-1]}/.git"):
        print(f"Repository {repo_url} already cloned.")
        return
    subprocess.run(["git", "clone", repo_url], cwd=destination_folder)


def main():
    print("Searching for Java repositories with more than 500 stars...")
    page = 1
    while True:
        repositories = search_repositories(page=page)
        if not repositories["items"]:
            break
        for repo in repositories["items"]:
            repo_name = repo["full_name"]
            repo_url = repo["clone_url"]
            print(f"Cloning repository {repo_name}...")
            clone_repository(repo_url)
        page += 1


if __name__ == "__main__":
    main()
