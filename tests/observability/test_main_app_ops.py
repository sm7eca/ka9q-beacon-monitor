from dataclasses import dataclass
from fastapi.testclient import TestClient
from ka9q_beacon_monitor.api.server import BeaconDefinition
from ka9q_beacon_monitor.observability import BuildIdentity
from ka9q_beacon_monitor.processing import BeaconClassifier
from ka9q_beacon_monitor.runtime import BeaconPipelineConfig, BeaconRuntime, create_main_app

class Repo:
    schema_version=1
    def counts(self): return (0,0)
    def close(self): pass
    def list_observations(self,*a,**k): return []
    def get_observation(self,*a,**k): return None
    def list_interval_summaries(self,*a,**k): return []
    def get_interval_summary(self,*a,**k): return None
    def save_observation(self,*a): pass
    def save_interval_summary(self,*a): pass
class Verifier:
    async def verify(self, observation, *, expected_callsign=None): return observation

def test_composed_application_exposes_ops_with_shared_lifecycle():
    runtime=BeaconRuntime(repository=Repo(), classifier=BeaconClassifier(), verifier=Verifier(), beacon_pipelines=[BeaconPipelineConfig("B1","sig",("ref",))])
    app=create_main_app(runtime, beacons=[BeaconDefinition("B1")], build_identity=BuildIdentity("5.2-test","rev"))
    with TestClient(app) as c:
        assert c.get('/ops/live').status_code == 200
        assert c.get('/ops/ready').status_code == 200
        assert c.get('/ops/build').json()['version'] == '5.2-test'
        assert 'ka9q_runtime_started 1' in c.get('/ops/metrics').text
