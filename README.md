# Push Tasks to Proof Ground

This project is a utility for the [Proof Ground](https://competition.isabelle.systems/) interactive theorem proving competition system.

The tool can automatically push tasks to the competition system.
A `task.yaml` file specifies the meta information of the task (see the sample file in this folder).
Files that correspond to the task are automatically detected and uploaded.

## Requirements
- Python 3
- The `pyyaml` library (`pip3 install pyyaml`)

## Usage
Running `python3 push_tasks.py -h` displays usage information.