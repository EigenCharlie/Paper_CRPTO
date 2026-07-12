# Pipeline Registry Status

`script_role_registry.yaml` is the only live, human-maintained script map. It
includes the active IJDS runner, evidence builder, TeX builder, compiler, and
publication gates.

The other YAML files in this directory and the JSON mirrors under
`models/pipeline_registry/` are historical topology snapshots. Several are
protected by `EXTRACTION_MANIFEST.json`, so they remain at their original paths
and must not be regenerated, moved, or interpreted as the active IJDS capsule.
Their older schema dates are provenance, not drift in the live registry.
