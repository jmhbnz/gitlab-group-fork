"""GitLab Group Fork - Fork and entire group of projects in a tree to another namespace"""

import sys
import os
import argparse
import logging
import gitlab
from treelib import Tree

class GitLabInfo():
    """Custom Data Type to hold data returned about group or project"""
    def __init__(
            self, gitlab_id="", name="",
            path="", description="", full_path="", new_id=""):
        self.gitlab_id = gitlab_id
        self.name = name
        self.path = path
        self.description = description
        self.full_path = full_path
        self.new_id = new_id

def main():
    """Main Function"""
    logging.basicConfig(level=logging.ERROR)
    options = parse_cli()
    glab = gitlab.Gitlab(options.url, options.token)
    src_group_tree = read_src_group(glab, options.srcGroup)
    dest_group_tree = create_dest_group(glab, options.destGroup, src_group_tree)
    count_of_projects = fork_projects(glab, src_group_tree, dest_group_tree)
    print(f"Forked {count_of_projects} Projects into {len(dest_group_tree)} Groups")

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

def add_new_group(gitlab_group_obj: gitlab.Gitlab) -> Tree:
    """Function to add new GitLab Group to Tree Object"""
    group_tree = Tree()
    group_tree.create_node(
        gitlab_group_obj.path,
        gitlab_group_obj.id,
        data=GitLabInfo(
            gitlab_id=gitlab_group_obj.id,
            name=gitlab_group_obj.name,
            full_path=gitlab_group_obj.full_path,
            path=gitlab_group_obj.path,
            description=gitlab_group_obj.description))
    return group_tree

def read_src_group(glab, src):
    """Read source group tree from gitlab server"""
    logging.info("Attemping to read source group '%s/%s'", glab.url, src)
    src_group_tree = Tree()
    top_level_group = glab.groups.get(src, include_subgroups=True)
    src_group_tree = add_new_group(top_level_group) # For root node
    def get_sub_groups(parent):
        logging.debug('Looking for sub-groups in %s', parent.full_path)
        new_top = glab.groups.get(parent.id, include_subgroups=True)
        subgroups = new_top.subgroups.list(all_available=True)
        for sub in subgroups:
            logging.debug('Found sub-group %s', sub.full_path)
            src_group_tree.paste(new_top.id, add_new_group(sub))
            logging.debug('Added node to tree with name %s and id %s', sub.path, sub.id)
            new_parent = glab.groups.get(sub.id, include_subgroups=True)
            new_subgroup = new_parent.subgroups.list(all_available=True)
            for child in new_subgroup:
                logging.debug('Traversing group %s', child.full_path)
                src_group_tree.paste(new_parent.id, add_new_group(child))
                get_sub_groups(child)
    get_sub_groups(top_level_group)
    logging.info('Found %s sub-groups', len(src_group_tree)-1)
    print("Source Groups[group_id]:")
    src_group_tree.show(idhidden=False)
    return src_group_tree

def create_dest_group(glab, dest, src_group_tree):
    """Create destination group structure"""
    if '/' in dest:
        logging.error('SubGroup as destination not supported "%s"', dest)
        sys.exit(1)
    dest_group_tree = Tree()
    logging.info('Attempting to create destination group at %s/%s', glab.url, dest)
    try:
        top_level_group = glab.groups.create({'name': dest, 'path': dest})
        logging.info('Group Created at %s/%s', glab.url, top_level_group.full_path)
        dest_group_tree = add_new_group(top_level_group) # For root node
        src_group_tree.update_node(src_group_tree.root, data=GitLabInfo(new_id=top_level_group.id))
    except gitlab.exceptions.GitlabCreateError as err:
        logging.error('Group Cannot be created: %s', err)
        sys.exit(1)
    except:
        logging.debug('An error occurred')
        raise
    for grp in src_group_tree.expand_tree():
        if src_group_tree.level(grp) == 0:
            continue
        new_parent = src_group_tree.get_node(src_group_tree.parent(grp).identifier).data.new_id
        logging.debug('Creating Group "%s" with Path "%s" and Parent ID "%s"',
                      src_group_tree.get_node(grp).data.name,
                      src_group_tree.get_node(grp).data.path,
                      new_parent)
        new_group = glab.groups.create(
            {'name': src_group_tree.get_node(grp).data.name,
             'path': src_group_tree.get_node(grp).data.path,
             'parent_id': new_parent,
             'description': src_group_tree.get_node(grp).data.description})
        src_group_tree.update_node(grp, data=GitLabInfo(new_id=new_group.id))
        dest_group_tree.paste(new_parent, add_new_group(new_group))
    logging.info('Created %s sub-groups', len(dest_group_tree)-1)
    print("Destination Groups[group_id]:")
    dest_group_tree.show(idhidden=False)
    return dest_group_tree

def fork_projects(glab, src_group_tree, dest_group_tree):
    """Fork the projects in source groups into destination groups"""
    count = 0
    logging.debug('Attempting to fork projects from %s to %s',
                  src_group_tree.get_node(src_group_tree.root).tag,
                  dest_group_tree.get_node(dest_group_tree.root).tag)
    for grp in src_group_tree.expand_tree():
        gitlab_grp = glab.groups.get(grp)
        projects = gitlab_grp.projects.list()
        for project in projects:
            gitlab_prj = glab.projects.get(project.id)
            new_namespace = src_group_tree.get_node(grp).data.new_id
            logging.debug('Forking project "%s" into namepace "%s"', gitlab_prj.name, new_namespace)
            gitlab_prj.forks.create({'namespace': new_namespace})
            print(f"Forked project: {gitlab_prj.name}")
            count = count + 1
    return count

if __name__ == "__main__":
    main()

logging.debug('End of Script')
