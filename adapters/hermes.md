# Hermes adapter

## Install

Install the Python helper package, then link the portable skill directory into the active Hermes profile:

```sh
python -m pip install -e /absolute/path/to/active-recall-learning-system
mkdir -p ~/.hermes/skills
ln -sfn /absolute/path/to/active-recall-learning-system/skills ~/.hermes/skills/active-recall
```

Also place `/absolute/path/to/active-recall-learning-system/protocol/learning-policy.md` in the Hermes project instructions or explicitly direct the agent to read it with the selected skill.

## Invoke

Ask Hermes: `Use the active-recall study-session skill for ~/Learning` or `Use active-recall source-ingest to add INPUT to ~/Learning`. The skill directory exposes the named Markdown procedures; invoke local helpers directly, e.g. `learning recommend ~/Learning`. Hermes must request confirmation before canonical workspace edits or network use and must retain citations and durable turn records.
