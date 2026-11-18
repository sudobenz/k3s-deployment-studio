import unittest
from app.core.models import DeploymentConfig, Machine, validate_config
class ModelTests(unittest.TestCase):
 def test_variable_machine_count(self):
  machines=[Machine(f"node-{i}",f"10.10.0.{i}/24","10.10.0.1","10.10.0.10") for i in range(2,7)]
  c=DeploymentConfig(machines=machines); self.assertEqual(len(c.machines),5); self.assertFalse(validate_config(c))
 def test_duplicate_ip_rejected(self):
  c=DeploymentConfig(machines=[Machine("node-a","10.0.0.2/24","10.0.0.1","10.0.0.10"),Machine("node-b","10.0.0.2/24","10.0.0.1","10.0.0.10")])
  self.assertTrue(any("dupliquée" in e for e in validate_config(c)))
if __name__=="__main__": unittest.main()
