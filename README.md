# GitLab Group Fork
Using the GitLab API and the python-gitlab module this will recursively fork projects from one group to another.

Set Environment Variable `GITLAB_TOKEN` to the [personal API token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) from your gitlab servers or optionally use -t on the command-line.

```
pip install -r requirements.txt
gitlab_group_fork.py src_group dest_group [-t token]
```

