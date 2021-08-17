# GitLab Group Fork

Using the GitLab API and the python-gitlab module this will recursively fork projects from one group to another.

Set Environment Variable `GITLAB_TOKEN` to the [personal API token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) from your gitlab servers or optionally use -t on the command-line.

```bash
# Create new python virtual environment
python3 -m venv .test

# Activate the virtual environment
source .test/bin/activate

# Install python dependencies
pip install -r requirements.txt

# Run the script
python3 gitlab_group_fork.py tps tps3 -t <token> -u <gitlab url>
```
