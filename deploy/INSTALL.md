# Deployment installation contract

The deployment archive is installed under `/opt/ka9q-beacon-monitor/releases/<version>` and activated by the atomic `/opt/ka9q-beacon-monitor/current` symlink.

A deployment automation layer SHALL:

1. create the service account and `/var/lib/ka9q-beacon-monitor` data directory;
2. create or update `/opt/ka9q-beacon-monitor/venv` from repository-controlled dependency inputs;
3. place validated runtime configuration under `/etc/ka9q-beacon-monitor`;
4. inject secrets outside source control;
5. install `ka9q-beacon-monitor.service`;
6. activate the target release only after package verification succeeds;
7. use the `previous` release pointer for rollback.

M5.3 defines the package and atomic release mechanics. Concrete production adapters and their dependencies remain M5.4 scope.
