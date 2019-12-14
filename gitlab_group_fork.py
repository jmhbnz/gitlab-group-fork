#!/usr/bin/env python3.7
"""GitLab Group Fork - Fork and entire group of projects in a tree to another namespace"""

import sys
import os
import argparse
import logging
import gitlab
from treelib import Tree

class GitLabInfo():
    def __init__(self, type, id, name="", path="", description="", full_path=""):
            self.type = type #group or project
            self.id = id
            self.name = name
            self.path = path
            self.description = description
            self.full_path = full_path

def main():
    """Main Function"""
    logging.basicConfig(level=logging.DEBUG)
    options = parse_cli()
    glab = gitlab.Gitlab(options.url, options.token)
    src_group_tree = read_src_group(glab, options.srcGroup)
    create_dest_group(glab, options.destGroup, src_group_tree)


def parse_cli():
    """Parse CLI Options and return, fail on no valid token"""
    logging.debug('parse_cli: Parsing CLI Arguments')
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url",
                        dest="url",
                        default="https://gitlab.com",
                        help="base URL of the GitLab instance")

    parser.add_argument("-t", "--token",
                        dest="token",
                        default='',
                        help="API token")

    parser.add_argument("srcGroup", help="Source namespace to copy")

    parser.add_argument("destGroup", help="Destination namespace to create")

    options = parser.parse_args()

    if options.token == "":
        logging.debug('parse_cli: Did not find token in cli options')
        if os.getenv("GITLAB_TOKEN") is not None:
            logging.debug('parse_cli: Found token in system environment variable GITLAB_TOKEN')
            options.token = os.getenv("GITLAB_TOKEN")
        else:
            logging.error('parse_cli: Did not find token in environment variable, quitting')
            print("API Token Required - Not found in options or environment variables")
            sys.exit(1)
    return options

def read_src_group(glab, src):
    """Read source group tree from gitlab server"""
    logging.info("Attemping to read source group '%s/%s'", glab.url, src)
    src_group_tree = Tree()
    top_level_group = glab.groups.get(src, include_subgroups=True)
    src_group_tree.create_node(
        top_level_group.path,
        top_level_group.id,
        data=GitLabInfo(
            type="group", 
            id=top_level_group.id, 
            name=top_level_group.name, 
            full_path=top_level_group.full_path,
            path=top_level_group.path,
            description=top_level_group.description))
    def get_sub_groups(parent):
        logging.debug('Looking for sub-groups in %s', parent.full_path)
        new_top = glab.groups.get(parent.id, include_subgroups=True)
        subgroups = new_top.subgroups.list(all_available=True)
        for sub in subgroups:
            logging.debug('Found sub-group %s', sub.full_path)
            src_group_tree.create_node(
                sub.path,
                sub.id,
                parent=new_top.id,
                data=GitLabInfo(
                    type="group", 
                    id=sub.id, 
                    name=sub.name, 
                    full_path=sub.full_path,
                    path=sub.path,
                    description=sub.description))
            logging.debug('Added node to tree with name %s and id %s', sub.path, sub.id)
            new_parent = glab.groups.get(sub.id, include_subgroups=True)
            new_subgroup = new_parent.subgroups.list(all_available=True)
            for child in new_subgroup:
                logging.debug('Traversing group %s', child.full_path)
                src_group_tree.create_node(
                    child.path,
                    child.id,
                    parent=new_parent.id,
                    data=GitLabInfo(
                        type="group", 
                        id=child.id, 
                        name=child.name, 
                        full_path=child.full_path,
                        path=child.path,
                        description=child.description))
                get_sub_groups(child)
    get_sub_groups(top_level_group)
    logging.info('Found %s sub-groups', len(src_group_tree)-1)
    src_group_tree.show()
    return src_group_tree

def create_dest_group(glab, dest, src_group_tree):
    """Create destination group structure"""
    logging.info('Attempting to create destination group at %s/%s',glab.url, dest)
    try:
        top_level_group = glab.groups.create({'name': dest, 'path': dest})
        logging.info('Group Created at %s/%s', glab.url, top_level_group.full_path)
    except gitlab.exceptions.GitlabCreateError as e:
        logging.error('Group Cannot be created: %s', e)
        sys.exit(1)
    except:
        logging.debug('An error occurred')
        raise
    for g in src_group_tree.expand_tree():
        if src_group_tree.level(g) == 0:
            continue
        l = []
        for b in src_group_tree.rsearch(g):
            l.append(src_group_tree.get_node(b).tag)
        l[-1] = top_level_group.full_path
        new_namespace = '/'.join(reversed(l))
        logging.debug('Creating Group "%s" with Path "%s"', src_group_tree.get_node(g).data.path, new_namespace)
        #print(src_group_tree.get_node(g).data.name, " --> ", new_namespace)
        glab.groups.create({'name': src_group_tree.get_node(g).data.name, 'path': new_namespace})
    #top_level_group.delete() # Remove this after testing
    #logging.info('Deleted Group')
    return


if __name__ == "__main__":
    main()

logging.debug('End of Script')
