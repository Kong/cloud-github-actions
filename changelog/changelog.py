#!/usr/bin/env python3

import re
import argparse
import git
from datetime import datetime
from collections import namedtuple

PullRequest = namedtuple("PullRequest", ["number", "message"])
Tag = namedtuple("Tag", ["name", "sha", "date_string"])

PR_MERGE_RE = re.compile(r"^Merge pull request #(\d+) from.*\n\n(.*)")
SQUASH_MERGE_RE = re.compile(r"^(.*) \(#(\d+)\)\n\n(.*)")


def fetch_release_tags(repo, pattern=r"^v\d+\.\d+\.\d+$"):
    def convert(gp_tag):
        date_string = None
        if gp_tag.tag:  # annotated tag
            date_string = (
                datetime.utcfromtimestamp(gp_tag.tag.tagged_date).date().isoformat()
            )
        return Tag(name=gp_tag.name, sha=gp_tag.commit.hexsha, date_string=date_string)

    tag_re = re.compile(pattern)
    return [convert(t) for t in repo.tags if tag_re.match(t.name)]


def get_pr_data(commit):
    if len(commit.parents) > 1:
        m = PR_MERGE_RE.match(commit.message)
        if not m:
            return None
        return PullRequest(message=m.group(2), number=int(m.group(1)))
    else:
        m = SQUASH_MERGE_RE.match(commit.message)
        if not m:
            return None
        return PullRequest(message=m.group(1), number=int(m.group(2)))


def process_commits(repo, branch, tag_map, current_tag):
    result = []
    current_prs = []
    for commit in repo.iter_commits(branch):
        if commit.binsha.hex() in tag_map:
            if current_prs:
                result.append((current_tag, current_prs))
                current_prs = []
                current_tag = tag_map[commit.binsha.hex()]
        pr_data = get_pr_data(commit)
        if pr_data:
            current_prs.append(pr_data)
    if current_prs:
        result.append((current_tag, current_prs))
    return result


def escape_message(message):
    escape_chars = ["(", ")", "_", "[", "]", "*", "<", ">"]
    for c in escape_chars:
        message = message.replace(c, "\\" + c)
    return message


def format_pr(pr, repo_url):
    message = escape_message(pr.message).strip()
    if not message:
        message = "UNKNOWN"
    return "- {message} [\#{pr_number}]({repo_url}/pull/{pr_number})".format(
        message=message, repo_url=repo_url, pr_number=pr.number
    )


def format_tag(tag, repo_url):
    date_string = ""
    if tag.date_string:  # annotated tag
        date_string = " (" + tag.date_string + ")"
    return "## [{tag_name}]({repo_url}/tree/{tag_name}){date_string}".format(
        date_string=date_string, tag_name=tag.name, repo_url=repo_url
    )


def format_full_changelog(tag_name, preceeding_tag_name, repo_url):
    full_changelog_url = "{repo_url}/compare/{preceeding_tag_name}...{tag_name}".format(
        tag_name=tag_name, preceeding_tag_name=preceeding_tag_name, repo_url=repo_url
    )
    return "[Full Changelog]({full_changelog_url})".format(
        full_changelog_url=full_changelog_url
    )


def format_history(history, repo_url, file):
    ordered_tag_names = [t.name for t, _ in history]
    preceeding_tag_name = {
        k: v for k, v in zip(ordered_tag_names, ordered_tag_names[1:])
    }
    print("# Changelog", file=file)
    for tag, prs in history:
        print(file=file)
        print(format_tag(tag, repo_url), file=file)
        print(file=file)
        if tag.name in preceeding_tag_name:
            print(
                format_full_changelog(
                    tag.name, preceeding_tag_name[tag.name], repo_url
                ),
                file=file,
            )
        print(file=file)
        print("**Merged pull requests:**", file=file)
        print(file=file)
        for pr in sorted(prs, reverse=True, key=lambda pr: pr.number):
            print(format_pr(pr, repo_url), file=file)


def changelog(branch, repo_url, next_tag_name, file=None):
    repo = git.Repo(".")
    tags = fetch_release_tags(repo)
    tag_map = {t.sha: t for t in tags}
    next_tag = Tag(
        name=next_tag_name, date_string=datetime.utcnow().date().isoformat(), sha=None
    )
    history = process_commits(repo, branch, tag_map, next_tag)
    format_history(history, repo_url, file)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--next-tag", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--repo-url", required=True)
    parser.add_argument("--file", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.file:
        with open(args.file, "w") as fh:
            changelog(args.branch, args.repo_url, args.next_tag, fh)
    else:
        changelog(args.branch, args.repo_url, args.next_tag)


if __name__ == "__main__":
    main()
