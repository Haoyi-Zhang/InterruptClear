"""Explicit POSIX limits or opt-in portable finite-check execution.

Portable mode has cooperative process-CPU checks, not an OS memory limit.
Missing RSS is reported as None; no POSIX measurement is fabricated.
"""
import sys
import time

try:
    import resource as _resource
except ImportError:
    _resource = None

_cpu_deadline = None


def configure_limits(cpu_soft=170, cpu_hard=180, address_space_mib=2500, *, portable=False):
    global _cpu_deadline
    if _resource is None and not portable:
        raise RuntimeError('POSIX resource limits unavailable; use --portable for finite checks without an OS memory cap')
    if _resource is not None:
        _resource.setrlimit(_resource.RLIMIT_AS, (address_space_mib * 1024**2,) * 2)
        _resource.setrlimit(_resource.RLIMIT_CPU, (cpu_soft, cpu_hard))
    _cpu_deadline = cpu_soft
    return {
        'platform': sys.platform,
        'mode': 'posix' if _resource is not None else 'portable',
        'requested_cpu_soft_seconds': cpu_soft,
        'requested_cpu_hard_seconds': cpu_hard,
        'requested_address_space_mib': address_space_mib,
        'os_cpu_limit_enforced': _resource is not None,
        'os_address_space_limit_enforced': _resource is not None,
        'cooperative_cpu_checks': True,
        'peak_rss_available': _resource is not None,
    }


def check_cpu_limit():
    if _cpu_deadline is not None and time.process_time() > _cpu_deadline:
        raise RuntimeError('process CPU ceiling exceeded; no verdict')


def peak_rss_kib():
    if _resource is None:
        return None
    rss = _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
    return rss / 1024 if sys.platform == 'darwin' else rss
