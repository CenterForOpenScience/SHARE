import subprocess


def test_sharectl_at_least_runs():
    completed_process = subprocess.run(['sharectl', '-v'])
    assert completed_process.returncode == 0
