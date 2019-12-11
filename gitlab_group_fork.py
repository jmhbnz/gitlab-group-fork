#!/usr/bin/env python3.7
"""GitLab Group Fork - Fork and entire group of projects in a tree to another namespace"""

import sys
import os
import argparse
import gitlab

def main():
    """Main Function"""
    options = parse_cli()
    glab = gitlab.Gitlab(options.url, options.token)

def parse_cli():
    """Parse CLI Options and return, fail on no valid token"""
    parser = argparse.ArgumentParser("usage: %prog [options] src_group dest_group")

    parser.add_argument("-u", "--url",
                        dest="url",
                        default="https://gitlab.com",
                        help="base URL of the GitLab instance")

    parser.add_argument("-t", "--token",
                        dest="token",
                        default='',
                        help="API token")

    options = parser.parse_args()

    if options.token == "":
        if os.getenv("GITLAB_TOKEN") is not None:
            options.token = os.getenv("GITLAB_TOKEN")
        else:
            print("API Token Required - Not found in options or environment variables")
            sys.exit(1)
    return options



if __name__ == "__main__":
    main()

print("End of Script")
