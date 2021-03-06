import requests
import json
import yaml
import sys
import argparse
from os import listdir
from os.path import isfile, join
import os.path

CONFIG_NAME = "task.yaml"
ENDPOINT = 'restapi/puttask'


def send_request(host_url, endpoint, api_token, data):
    url = f'{host_url}{endpoint}/'
    response = requests.post(url, json=data, headers={
        'Authorization': f'Token {api_token}'})
    return response


isabelle_file_types = {
    "Definitions file": "Defs.thy",
    "Template file": "Template.thy",
    "Private check file": "Check_Private.thy",
    "Public check file": "Check.thy",
    "Make file": None,
}

coq_file_types = {
    "Definitions file": "Defs.v",
    "Template file": "Template.v",
    "Private check file": "checks.sexp",
    "Public check file": None,
    "Make file": "Makefile",
}

lean_file_types = {
    "Definitions file": "defs.lean",
    "Template file": "template.lean",
    "Private check file": "check.lean",
    "Public check file": "check.lean",
    "Make file": None,
}

file_types = {
    "Isabelle": isabelle_file_types,
    "Coq": coq_file_types,
    "Lean": lean_file_types
}

submission_files = {
    "Isabelle": 'Submission.thy',
    "Coq": "Submission.v",
    "Lean": "submission.lean"
}


def collect_files(path, prover, data):
    files = [f for f in listdir(path) if isfile(join(path, f))]
    for name, file in file_types[prover].items():
        if file in files:
            file_path = join(path, file)
            with open(file_path) as f:
                data[name] = f.read()
        else:
            data[name] = ""


def add_submission(path, prover, data):
    file_path = join(path, submission_files[prover])
    if os.path.exists(file_path):
        with open(file_path) as f:
            data['Submission'] = f.read()


def load_files(data, path):
    prover = data['Prover']
    collect_files(path, prover, data.get('Task Resource', {}))
    add_submission(path, prover, data)


def load_path(path):
    with open(join(path, CONFIG_NAME), 'r') as stream:
        try:
            data = yaml.safe_load(stream)
            load_files(data, path)
            return data
        except yaml.YAMLError as exc:
            print("Error while parsing YAML file!", file=sys.stderr)
            raise exc


def do_path(url, endpoint, token, path):
    data = load_path(path)
    r = send_request(url, endpoint, token, data)

    try:
        reply = r.json()
        if r.status_code == 400:
            print(
                f"A known error was reported by the server: {reply['message']}", file=sys.stderr)
            print(reply['exception'], file=sys.stderr)
            sys.exit(-4)
        elif r.status_code == 500:
            print(
                f"An internal error was reported by the server: {reply['message']}", file=sys.stderr)
            print(reply['exception'], file=sys.stderr)
            sys.exit(-5)
        elif r.status_code == 200:
            if reply['message'] == "success":
                name = None
                if 'Task' in data:
                    name = data['Task'].get('Name')
                if not name and 'Task Definition' in data:
                    name = data['Task Definition'].get('Name')
                return name, reply.get('submission_id')
            else:
                raise ValueError("Unexpected status message!")
        elif r.status_code == 401 and reply['detail'] == "Invalid token.":
            print(f"The access token is invalid.", file=sys.stderr)
            sys.exit(-4)
        else:
            raise ValueError(
                "Unexpected status code: {r.status_code}. Error info: {r.text}")
    except json.decoder.JSONDecodeError as e:
        print(
            f"Unexpected server reply! Status code: {r.status_code}", file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(-1)


def scan_and_push(url, endpoint, token, path):
    requests = []
    for dirpath, _, _ in os.walk(path):
        if os.path.exists(join(dirpath, CONFIG_NAME)):
            task_name, submission_id = do_path(url, endpoint, token, dirpath)
            requests.append((dirpath, task_name, submission_id))
    return requests


parser = argparse.ArgumentParser(
    description='Push tasks to competition system.')
parser.add_argument('paths', metavar='PATH', nargs='+',
                    help='List of paths to inspect for tasks.')
parser.add_argument('-r', '--recursive', action='store_true',
                    help='Recursively inspect subfolders.')
parser.add_argument('--http', action='store_true',
                    help='Allow request via HTTP. Might compromise your access token.')
parser.add_argument('--token', required=True,
                    help="Access token for the competition system.")
parser.add_argument('--url', required=True,
                    help="URL of the competition system.")


def do_it():
    args = parser.parse_args()
    url = args.url
    token = args.token

    if not args.http and not url.startswith('https://'):
        print("URL is not HTTPS but --http was not specified!", file=sys.stderr)
        sys.exit(-1)

    requests = []
    for path in args.paths:
        if args.recursive:
            requests.extend(scan_and_push(url, ENDPOINT, token, path))
        else:
            task_name, submission_id = do_path(url, ENDPOINT, token, path)
            requests.append((path, task_name, submission_id))

    print("Success! List of submitted tasks:")
    for path, task_name, submission_id in requests:
        print(f'{task_name}({path}): {submission_id if submission_id else "none"}')


if __name__ == '__main__':
    do_it()
